import base64

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from django.contrib.gis.db.models import GeoManager
from django.contrib.sites.models import Site
from django.core.mail import send_mail, EmailMessage
from django.db import models, transaction, IntegrityError
from django.template import loader
from django.template.defaultfilters import slugify
from django.utils import simplejson as json
from django.utils.translation import ugettext_lazy as _

from geo.filterspec import (CountryFilterSpec, StateFilterSpec,
                            CityFilterSpec, RegionFilterSpec)
from geo.models import Location
from records.models import Record
from rah.models import Profile
from actions.models import Action
from invite.models import Invitation, Rsvp
from thumbnails.fields import ImageAndThumbsField
from messaging.models import Stream
from utils import hash_val

class GroupManager(GeoManager):
    def groups_with_memberships(self, user, limit=None):
        groups = self.all().select_related("geom").order_by("name")
        groups = groups.extra(
                    select_params = (user.id,),
                    select = { 'is_member': 'SELECT groups_groupusers.created \
                                                FROM groups_groupusers \
                                                WHERE groups_groupusers.user_id = %s AND \
                                                groups_groupusers.group_id = groups_group.id'})
        groups = groups.extra(
                    select_params = (user.id,),
                    select = { 'membership_pending': 'SELECT groups_membershiprequests.created \
                                                        FROM groups_membershiprequests \
                                                        WHERE groups_membershiprequests.user_id = %s AND \
                                                        groups_membershiprequests.group_id = groups_group.id'})
        return groups[:limit] if limit else groups

    def groups_not_blacklisted_by_user(self, user):
        return self.filter(users=user).exclude(pk__in=user.email_blacklisted_group_set.all())

class Group(models.Model):
    DISC_MODERATION = (
        (1, _('Yes, a manager must approve all discussions'),),
        (0, _('No, members can post discussions directly'),),
    )
    DISC_POST_PERM = (
        (0, _('Members and managers'),),
        (1, _('Only managers'),),
    )
    MEMBERSHIP_CHOICES = (
        ('O', _('Open membership')),
        ('C', _('Closed membership')),
    )

    name = models.CharField(_('name'), max_length=255, blank=True)
    slug = models.CharField(_('slug'), max_length=255, unique=True, db_index=True)
    description = models.TextField(_('description'), blank=True)
    image = ImageAndThumbsField(_('image'), upload_to="group_images", null=True, 
                                default="images/theme/default_group.png")
    is_featured = models.BooleanField(_('is featured'), default=False)

    geom = models.ForeignKey('geo.Point', blank=True, null=True,
                             verbose_name=_('location'))

    membership_type = models.CharField(_('membership type'), max_length=1, 
                                       choices=MEMBERSHIP_CHOICES, default="O", null=True)

    is_external_link_only = models.BooleanField(_('is external link only'), default=False)

    sample_location = models.ForeignKey(Location, null=True, blank=True, 
                                        related_name="sample_group_set",
                                        verbose_name=_('sample location'))
    sample_location.country_filter = True

    users = models.ManyToManyField(User, through="GroupUsers", verbose_name=_('users'))
    requesters = models.ManyToManyField(User, through="MembershipRequests", 
                                        related_name="requested_group_set",
                                        verbose_name=_('requesters'))
    email_blacklisted = models.ManyToManyField(User, through="DiscussionBlacklist", 
                                               related_name="email_blacklisted_group_set",
                                               verbose_name=_('email blacklisted'))
    created = models.DateTimeField(_('created'), auto_now_add=True)
    created.state_filter = True

    updated = models.DateTimeField(_('updated'), auto_now=True)
    updated.city_filter = True

    objects = GroupManager()
    disc_moderation = models.IntegerField(choices=DISC_MODERATION, default=0, null=True, 
                                          verbose_name=_("Moderate discussions?"))
    disc_moderation.region_filter = True

    disc_post_perm = models.IntegerField(choices=DISC_POST_PERM, default=0, null=True,
                                         verbose_name=_("Who can post discussions?"))
    member_count = models.IntegerField(default=0)

    class Meta:
        verbose_name = _("community")
        verbose_name_plural = _("communities")

    def is_joinable(self):
        if self.is_external_link_only:
            return False
        return True

    def is_public(self):
        return self.membership_type == "O"

    def is_member(self, user):
        return user.is_authenticated() and \
            GroupUsers.objects.filter(group=self, user=user).exists()

    def completed_actions_by_user(self, limit=None):
        """
        what actions have been completed by users in this group and how many users have completed each action
        """
        fields = ", ".join(["%s.%s" % (Action._meta.db_table, f.column) for f in Action._meta.fields])
        query = """
            SELECT DISTINCT %(fields)s, COUNT(DISTINCT actions_useractionprogress.user_id) AS completes_in_group
            FROM actions_action
            INNER JOIN actions_useractionprogress ON (actions_action.id = actions_useractionprogress.action_id)
            INNER JOIN groups_groupusers ON (actions_useractionprogress.user_id = groups_groupusers.user_id)
            WHERE groups_groupusers.group_id = %(group_id)s
            AND actions_useractionprogress.is_completed = 1
            GROUP BY %(fields)s
            ORDER BY completes_in_group DESC
        """
        if limit:
            query += "LIMIT %(limit)s"
        return Action.objects.raw(query % {"fields": fields, "group_id": self.id, "limit": limit})

    def members_ordered_by_points(self, limit=None):
        fields = ", ".join(["%s.%s" % (User._meta.db_table, f.column) for f in User._meta.fields])
        query = """
            SELECT %(fields)s, rah_profile.total_points,
                SUM(actions_useractionprogress.is_completed) AS actions_completed,
                COUNT(actions_useractionprogress.date_committed) AS actions_committed,
                (SELECT MAX(created) FROM records_record WHERE user_id = auth_user.id) AS last_active
            FROM auth_user
            INNER JOIN groups_groupusers ON (auth_user.id = groups_groupusers.user_id)
            LEFT OUTER JOIN actions_useractionprogress ON (auth_user.id = actions_useractionprogress.user_id)
            LEFT OUTER JOIN rah_profile ON (auth_user.id = rah_profile.user_id)
            WHERE groups_groupusers.group_id = %(group_id)s
            GROUP BY %(fields)s, rah_profile.total_points
            ORDER BY rah_profile.total_points DESC
        """
        if limit:
            query += "LIMIT %(limit)s"
        return User.objects.raw(query % {"fields": fields, "group_id": self.id, "limit": limit})

    def group_records(self, limit=None):
        records = Record.objects.filter(user__group=self)
        records = records.exclude(user__profile__is_profile_private=True)
        records = records.exclude(user__is_staff=True)
        records = records.select_related().order_by("-created")
        return records[:limit] if limit else records

    def has_pending_membership(self, user):
        return user.is_authenticated() and \
            self.is_joinable() and \
            MembershipRequests.objects.filter(group=self, user=user).exists()

    def requesters_to_grant_or_deny(self, user):
        if self.is_joinable() and user.is_authenticated() and self.is_user_manager(user):
            return User.objects.filter(membershiprequests__group=self)
        return []

    def events_waiting_approval(self, user):
        return self.association_requests_waiting_approval(
            user, content_type=ContentType.objects.get(app_label="events", model="event"))

    def challenges_waiting_approval(self, user):
        return self.association_requests_waiting_approval(
            user, content_type=ContentType.objects.get(app_label="challenges", model="challenge"))

    def actions_waiting_approval(self, user):
        return self.association_requests_waiting_approval(
            user, content_type=ContentType.objects.get(app_label="actions", model="action"))

    def association_requests_waiting_approval(self, user, content_type=None):
        if user.is_authenticated() and self.is_user_manager(user):
            requests = GroupAssociationRequest.objects.filter(group=self, approved=False)
            if content_type is not None:
                requests = requests.filter(content_type=content_type)
            return requests
        return []

    def is_user_manager(self, user):
        return user.is_authenticated() and \
            GroupUsers.objects.filter(user=user, group=self, is_manager=True).exists()

    def managers(self):
        return User.objects.filter(group=self, groupusers__is_manager=True)

    def has_other_managers(self, user):
        managers = GroupUsers.objects.filter(group=self, is_manager=True)
        if user.is_authenticated():
            managers = managers.exclude(user=user)
        return managers.exists()

    def number_of_managers(self):
        return GroupUsers.objects.filter(group=self, is_manager=True).count()

    def is_poster(self, user):
        """True if a user is allowed to post discussions to this group"""
        if user.is_authenticated() and (self.is_user_manager(user) or (self.is_member(user) and self.disc_post_perm == 0)):
            return True
        return False

    def is_subscribed(self, user):
        if not user.is_authenticated():
            return False
        return not DiscussionBlacklist.objects.filter(group=self, user=user).exists()

    def moderate_disc(self, user):
        """True if disc needs to be moderated"""
        if self.disc_moderation == 0 and self.is_member(user) or self.is_user_manager(user):
            return False
        return True

    def get_public_url(self):
        if self.is_external_link_only:
            return self.external_link()
        return self.get_absolute_url()

    @models.permalink
    def get_absolute_url(self):
        return ("group_detail", [str(self.slug)])

    def users_not_blacklisted(self):
        return User.objects.filter(group=self).exclude(pk__in=self.email_blacklisted.all())

    def total_points(self):
        return Profile.objects.filter(user__group=self).aggregate(t_p=models.Sum("total_points"))["t_p"]

    def total_members(self):
        return GroupUsers.objects.filter(group=self).count()

    def invites_sent(self):
        content_type = ContentType.objects.get_for_model(self)
        return Invitation.objects.filter(content_type=content_type, object_pk=self.pk).count()

    def external_link(self):
        if not self.is_external_link_only:
            return None
        from group_links.models import ExternalLink
        try:
            return self.external_link_set.all()[0]
        except:
            return None

    def facebook_link(self):
        if self.is_external_link_only:
            return None
        from group_links.models import ExternalLink
        link = self.external_link_set.filter(url__contains="facebook.com")
        if not len(link):
            return None
        return link[0]

    def twitter_link(self):
        if self.is_external_link_only:
            return None
        from group_links.models import ExternalLink
        link = self.external_link_set.filter(url__contains="twitter.com")
        if not len(link):
            return None
        return link[0]

    def __unicode__(self):
        return u'%s' % self.name

class GroupUsers(models.Model):
    user = models.ForeignKey(User, verbose_name=_('user'))
    group = models.ForeignKey(Group, verbose_name=_('group'))
    is_manager = models.BooleanField(_('is manager'), default=False)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)

    class Meta:
        unique_together = ("user", "group",)
        verbose_name = _("member")
        verbose_name_plural = _("members")

    def __unicode__(self):
        return _('%(user)s belongs to community %(group)s') % {
            'user': self.user.get_full_name(), 'group': self.group}

class MembershipRequests(models.Model):
    user = models.ForeignKey(User, verbose_name=_('user'))
    group = models.ForeignKey(Group, verbose_name=_('group'))
    created = models.DateTimeField(_('created'), auto_now_add=True)

    class Meta:
        unique_together = ("user", "group",)
        verbose_name = _('group membership request')
        verbose_name_plural = _('group membership requests')

    def __unicode__(self):
        return _('%(user)s request to join %(group)s on %(date)s') % {
                'user': self.user, 'group': self.group, 'date': self.created}

class DiscussionBlacklist(models.Model):
    """
    Any user listed in this table will not recieve discussion emails for the group
    they are linked to.
    """
    user = models.ForeignKey(User, verbose_name=_('user'))
    group = models.ForeignKey(Group, verbose_name=_('group'))
    created = models.DateTimeField(_('created'), auto_now_add=True)

    class Meta:
        unique_together = ("user", "group",)
        verbose_name = _('group discussion blacklist entry')
        verbose_name_plural = _('group discussion blacklist entries')

    def __unicode__(self):
        return _("%(user)s will not recieve emails for %(group)s discussions") % {
            'user': self.user, 'group': self.group}

class DiscussionManager(models.Manager):
    def get_query_set(self):
        return super(DiscussionManager, self).get_query_set().filter(is_removed=False)

class Discussion(models.Model):
    subject = models.CharField(_('subject'), max_length=255)
    body = models.TextField(_('body'))
    user = models.ForeignKey(User, verbose_name=_('user'))
    group = models.ForeignKey(Group, verbose_name=_('group'))
    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)
    parent = models.ForeignKey("Discussion", null=True, verbose_name=_('parent'))
    is_public = models.BooleanField(_('is public'), default=False)
    is_removed = models.BooleanField(_('is removed'), default=False)
    reply_count = models.IntegerField(_('reply count'), null=True)
    objects = DiscussionManager()

    disallow_replies = models.BooleanField(_('disallow replies'), default=False)

    ## This will be used to denote discussions that are attached to an event/campaign
    ## linked to the group.  Right now an informal text field with storage like
    ## "events.Event:3"
    attached_to = models.TextField(null=True)

    class Meta:
        verbose_name = _('Discussion')
        verbose_name = _('Discussions')

    @property
    def thread_id(self):
        if self.parent:
            return self.parent.id
        return self.id

    @models.permalink
    def get_absolute_url(self):
        return ("group_disc_detail", [self.group.slug, self.thread_id])

    def container(self):
        if self.attached_to is None:
            return self.group
        target = self.attached_to.split(":")
        if target[0] == "events.Event":
            from events.models import Event
            try:
                event = Event.objects.get(pk=target[1], groups=self.group)
            except Event.DoesNotExist:
                self.attached_to = None
                self.save()
                return self.group
            return event
        elif target[0] == "challenges.Challenge":
            from challenges.models import Challenge
            try:
                petition = Challenge.objects.get(pk=target[1], groups=self.group)
            except Challenge.DoesNotExist:
                self.attached_to = None
                self.save()
                return self.group
            return petition

        self.attached_to = None
        self.save()
        
    def email_staff_for_moderation(self):
        return None

    def email_recipients(self):
        if self.attached_to is None:
            return [u for u in self.group.users_not_blacklisted() if u.pk != self.user.pk]

        target = self.attached_to.split(":")
        if target[0] == "events.Event":
            from events.models import Event
            try:
                event = Event.objects.get(pk=target[1], groups=self.group)
            except Event.DoesNotExist:
                self.attached_to = None
                self.save()
                return [u for u in self.group.users_not_blacklisted() if u.pk != self.user.pk]
            guests = event.attendees()
            # @@TODO: this is too many queries, select related
            # @@TODO: check blacklist
            return [u.contributor for u in guests if u.contributor.email != self.user.email]

        elif target[0] == "challenges.Challenge":
            from challenges.models import Challenge
            try:
                petition = Challenge.objects.get(pk=target[1], groups=self.group)
            except Challenge.DoesNotExist:
                self.attached_to = None
                self.save()
                return [u for u in self.group.users_not_blacklisted() if u.pk != self.user.pk]
            # @@TODO: check blacklist
            return [u for u in petition.supporters.all() if u.email != self.user.email]

        self.attached_to = None
        self.save()
        return [u for u in self.group.users_not_blacklisted() if u.pk != self.user.pk]
        
    def email_extra_headers(self, user_object):
        """
        The Messaging system will look for this method to call
        while constructing emails to send; we build a custom
        Reply-To header that encodes the discussion's group
        and thread ID, and the email address of the recipient 
        we're sending to, so that email replies can use the
        address to find what discussion to try to append to.
        We encode the recipient's email address so that we can
        allow users to send email replies from an address other
        than the one that received it -- e.g. if I have multiple
        addresses going to the same email account and prefer to
        send with a specific one.

        A secret-key-hash of the JSONified data is joined to the
        data itself, and the resulting string (base64-encoded)
        is used as the Reply-To value.  This way, when receiving
        email responses, we can use the hashed value to confirm
        that the user did not tamper with or manually construct
        the address to send to.  This is important because we
        will need to trust the inbound email as coming from the
        user it claims to be coming from.
        """
        headers = {
            "To": settings.PLUS_ADDRESSED_TO_EMAIL % self.group.slug
            }
        if self.disallow_replies:
            # If we're not allowing replies, just use the system defaults
            # and don't build a magic reply-to header.
            return headers

        value = json.dumps(dict(parent_id=self.thread_id,
                                user=user_object.email,
                                group=self.group.slug))
        value = "%s\0%s" % (value, hash_val(value))
        value = base64.b64encode(value)
        headers["Reply-To"] = "%s@%s" % (value, settings.SMTP_HTTP_RELAY_DOMAIN)
        return headers

class GroupAssociationRequest(models.Model):
    content_type = models.ForeignKey(ContentType, verbose_name=_('content type'))
    object_id = models.PositiveIntegerField(_('object id'))
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    group = models.ForeignKey('groups.Group', verbose_name=_('group'))
    approved = models.BooleanField(_('approved'), default=False)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)

    class Meta:
        unique_together = ('content_type', 'object_id', 'group',)
        verbose_name = _('group association request')
        verbose_name = _('group association requests')

    def __unicode__(self):
        return _('%(user)s would like to link %(object)s to %(group)s') % {
            'user': self.content_object.creator, 
            'object': self.content_object, 
            'group': self.group}

def remove_association_requests(sender, instance, **kwargs):
    content_object = instance
    content_type = ContentType.objects.get_for_model(content_object)
    object_id = content_object.id
    requests = GroupAssociationRequest.objects.filter(
        content_type=content_type, object_id=object_id)
    requests.delete()
from events.models import Event
from challenges.models import Challenge
from actions.models import Action
models.signals.post_delete.connect(remove_association_requests, sender=Event)
models.signals.post_delete.connect(remove_association_requests, sender=Challenge)
models.signals.post_delete.connect(remove_association_requests, sender=Action)

"""
Signals!
"""

def add_invited_user_to_group(sender, instance, **kwargs):
    invitation = instance.invitation
    if invitation.content_type == ContentType.objects.get(app_label="groups", model="group"):
        GroupUsers.objects.get_or_create(user=instance.invitee, group=invitation.content_object)

def update_discussion_reply_count(sender, instance, **kwargs):
    if instance.parent_id:
        parent = Discussion.objects.get(pk=instance.parent_id)
        reply_count = Discussion.objects.filter(parent=instance.parent_id, is_public=True).count()
        parent.reply_count = reply_count
        parent.save()

def update_group_member_count(sender, instance, **kwargs):
    try:
        group = instance.group
        group.member_count = GroupUsers.objects.filter(group=group).count()
        group.save()
    except Group.DoesNotExist:
        pass #in case the group was just deleted

def alert_users_of_discussion(sender, instance, **kwargs):
    if (instance.is_public or instance.attached_to) and not instance.is_removed and not instance.reply_count:
        Stream.objects.get(slug="community-discussion").enqueue(content_object=instance, start=instance.created)
    return True

def infer_user_location_from_group(sender, instance, created, **kwargs):
    usergroup = instance
    group = usergroup.group
    profile = usergroup.user.get_profile()
    if profile.geom:
        return
    profile.geom = group.geom
    profile.save()

models.signals.post_save.connect(add_invited_user_to_group, sender=Rsvp)
models.signals.post_save.connect(update_discussion_reply_count, sender=Discussion)
models.signals.post_save.connect(update_group_member_count, sender=GroupUsers)
models.signals.post_delete.connect(update_group_member_count, sender=GroupUsers)
models.signals.post_save.connect(alert_users_of_discussion, sender=Discussion)
models.signals.post_save.connect(infer_user_location_from_group, sender=GroupUsers)

def remove_community_create_stream(sender, instance, **kwargs):
    Stream.objects.get(slug="community-create").dequeue(content_object=instance)
models.signals.post_delete.connect(remove_community_create_stream, sender=Group)

def notification_on_group_association_request(sender, instance, created, **kwargs):
    if created:
        Stream.objects.get(slug="event-group-association-request").enqueue(
            content_object=instance, start=instance.created)
models.signals.post_save.connect(notification_on_group_association_request,
                                 sender=GroupAssociationRequest)

