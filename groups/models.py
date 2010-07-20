from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.models import Site
from django.core.mail import send_mail, EmailMessage
from django.db import models
from django.template import loader
from django.template.defaultfilters import slugify

from geo.models import Location
from records.models import Record
from rah.models import Profile
from actions.models import Action
from invite.models import Invitation, Rsvp
from notification import models as notification
   
class GroupManager(models.Manager):
    def groups_with_memberships(self, user, limit=None):
        groups = self.filter(is_geo_group=False).order_by("name")
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
        
    def user_geo_group_tuple(self, user, location_type):
        location = user.get_profile().location
        geo_groups = []
        slug = Group.LOCATION_SLUG[location_type](location)
        query = self.filter(slug=slug)
        geo_groups.append((location_type, query[0] if query else None))
        parent_key = Group.LOCATION_PARENT[location_type]
        while parent_key:
            size = Group.LOCATION_SIZE[location_type](location)
            parent_size = Group.LOCATION_SIZE[parent_key](location)
            if parent_size > size:
                geo_groups = geo_groups + self.user_geo_group_tuple(user, parent_key)
                break
            else:
                parent_key = Group.LOCATION_PARENT[parent_key]
        return geo_groups

    def create_geo_group(self, location_type, location, parent):
        name = Group.LOCATION_NAME[location_type](location)
        slug = Group.LOCATION_SLUG[location_type](location)
        return Group.objects.create(name=name, slug=slug, is_geo_group=True, location_type=location_type, sample_location=location, parent=parent)
        
    def groups_not_blacklisted_by_user(self, user):
        return self.filter(users=user).exclude(pk__in=user.email_blacklisted_group_set.all())
        
class Group(models.Model):
    DISC_MODERATION = (
        (1, 'Yes, a manager must approve all discussions',),
        (0, 'No, members can post discussions directly',),
    )
    DISC_POST_PERM = (
        (0, 'Members and managers',),
        (1, 'Only managers',),
    )
    MEMBERSHIP_CHOICES = (
        ('O', 'Open membership'),
        ('C', 'Closed membership'),
    )
    LOCATION_TYPE = (
        ('S', 'State'),
        ('C', 'County'),
        ('P', 'Place'),
    )
    LOCATION_PARENT = {
        'S': None,
        'C': 'S',
        'P': 'C',
    }
    LOCATION_NAME = {
        'S': lambda l: l.state,
        'C': lambda l: l.county,
        'P': lambda l: "%s, %s" % (l.name, l.state),
    }
    LOCATION_SLUG = {
        'S': lambda l: slugify(l.st),
        'C': lambda l: "%s-%s" % (slugify(l.st), slugify(l.county)),
        'P': lambda l: "%s-%s-%s" % (slugify(l.st), slugify(l.county), slugify(l.name)),
    }
    LOCATION_URL = {
        'S': lambda l: ("geo_group_state", [l.st]),
        'C': lambda l: ("geo_group_county", [l.st, slugify(l.county)]),
        'P': lambda l: ("geo_group_place", [l.st, slugify(l.county), slugify(l.name)]),
    }
    LOCATION_SIZE = {
        'S': lambda l: Location.objects.filter(state=l.state).aggregate(size=models.Count('state')),
        'C': lambda l: Location.objects.filter(state=l.state,county=l.county).aggregate(size=models.Count('county')),
        'P': lambda l: Location.objects.filter(state=l.state,county=l.county,name=l.name).aggregate(size=models.Count('name'))
    }

    name = models.CharField(max_length=255, blank=True)
    slug = models.CharField(max_length=255, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="group_images", null=True)
    is_featured = models.BooleanField(default=False)
    membership_type = models.CharField(max_length=1, choices=MEMBERSHIP_CHOICES, default="O", null=True)
    is_geo_group = models.BooleanField(default=False)
    location_type = models.CharField(max_length=1, choices=LOCATION_TYPE, blank=True)
    sample_location = models.ForeignKey(Location, null=True, blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, related_name="children")
    users = models.ManyToManyField(User, through="GroupUsers")
    requesters = models.ManyToManyField(User, through="MembershipRequests", related_name="requested_group_set")
    email_blacklisted = models.ManyToManyField(User, through="DiscussionBlacklist", related_name="email_blacklisted_group_set")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    objects = GroupManager()
    disc_moderation = models.IntegerField(choices=DISC_MODERATION, default=0, null=True, verbose_name="Moderate discussions?")
    disc_post_perm = models.IntegerField(choices=DISC_POST_PERM, default=0, null=True,  verbose_name="Who can post discussions?")
    member_count = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "team"
        verbose_name_plural = "teams"
    
    def is_joinable(self):
        return not self.is_geo_group
    
    def is_public(self):
        return self.is_geo_group or self.membership_type == "O"
        
    def is_member(self, user):
        return user.is_authenticated() and \
            GroupUsers.objects.filter(group=self, user=user).exists()
        
    def safe_image(self):
        if self.is_geo_group:
            return self.image if self.image else "images/theme/geo_group.jpg"
        return self.image if self.image else "images/theme/default_group.png"
        
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
        
    def is_user_manager(self, user):
        return user.is_authenticated() and \
            self.is_joinable() and \
            GroupUsers.objects.filter(user=user, group=self, is_manager=True).exists()
        
    def parents(self):
        parents = []
        if self.parent:
            parents.extend(self.parent.parents())
            parents.append(self.parent)
        return parents
        
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
    
    def moderate_disc(self, user):
        """True if disc needs to be moderated"""
        if self.disc_moderation == 0 and self.is_member(user) or self.is_user_manager(user):
            return False
        return True
    
    @models.permalink
    def get_absolute_url(self):
        if self.is_geo_group:
            return Group.LOCATION_URL[self.location_type](self.sample_location)
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
        
    def __unicode__(self):
        return u'%s' % self.name
        
class GroupUsers(models.Model):
    user = models.ForeignKey(User)
    group = models.ForeignKey(Group)
    is_manager = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ("user", "group",)
        verbose_name_plural = "group users"
    
    def __unicode__(self):
        return u'%s belongs to team %s' % (self.user, self.group)
        
class MembershipRequests(models.Model):
    user = models.ForeignKey(User)
    group = models.ForeignKey(Group)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ("user", "group",)
    
    def __unicode__(self):
        return u'%s request to join %s on %s' % (self.user, self.group, self.created)
        
class DiscussionBlacklist(models.Model):
    """
    Any user listed in this table will not recieve discussion emails for the group
    they are linked to.
    """
    user = models.ForeignKey(User)
    group = models.ForeignKey(Group)
    created = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ("user", "group",)
        
    def __unicode__(self):
        return u"%s will not recieve emails for %s discussions" % (self.user, self.group)

class DiscussionManager(models.Manager):
    def get_query_set(self):
        return super(DiscussionManager, self).get_query_set().filter(is_removed=False)

class Discussion(models.Model):
    subject = models.CharField(max_length=255)
    body = models.TextField()
    user = models.ForeignKey(User)
    group = models.ForeignKey(Group)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    parent = models.ForeignKey("Discussion", null=True)
    is_public = models.BooleanField(default=False)
    is_removed = models.BooleanField(default=False)
    reply_count = models.IntegerField(null=True)
    objects = DiscussionManager()
    
    @models.permalink
    def get_absolute_url(self):
        return ("group_disc_detail", [self.group.slug, self.parent_id if self.parent_id else self.id])

"""
Signals!
"""
def associate_with_geo_groups(sender, instance, **kwargs):
    user = instance.user
    GroupUsers.objects.filter(user=user, group__is_geo_group=True).delete()
    if instance.location:
        geo_groups = Group.objects.user_geo_group_tuple(user, 'P')
        parent = None
        for location_type, geo_group in reversed(geo_groups):
            if not geo_group:
                geo_group = Group.objects.create_geo_group(location_type, instance.location, parent)
            GroupUsers(user=user, group=geo_group).save()
            parent = geo_group

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
    group = Group.objects.get(pk=instance.group.id)
    group.member_count = GroupUsers.objects.filter(group=group).count()
    group.save()
    
def alert_users_of_discussion(sender, instance, **kwargs):
    if instance.is_public and not instance.is_removed and not instance.reply_count:
        template = "groups/group_disc_email.html"
        context = {"discussion": instance, "domain": Site.objects.get_current().domain,}
        users = instance.group.users_not_blacklisted()
        for user in users:
            if user.pk == instance.user.pk: #don't send an email to the user that started the discussion
                continue
            context["user"] = user
            msg = EmailMessage("Repower at Home %s Discussion - %s" % (instance.group, instance.subject),
                loader.render_to_string(template, context), None, [user.email])
            msg.content_subtype = "html"
            try:
                msg.send()
            except SMTPException, e:
                return False
    return True

models.signals.post_save.connect(associate_with_geo_groups, sender=Profile)
models.signals.post_save.connect(add_invited_user_to_group, sender=Rsvp)
models.signals.post_save.connect(update_discussion_reply_count, sender=Discussion)
models.signals.post_save.connect(update_group_member_count, sender=GroupUsers)
models.signals.post_delete.connect(update_group_member_count, sender=GroupUsers)
models.signals.post_save.connect(alert_users_of_discussion, sender=Discussion)