from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes import generic
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _
from messaging.models import Stream
from utils import hash_val

class DiscussionManager(models.Manager):
    def get_query_set(self):
        return super(DiscussionManager, self).get_query_set().filter(
            is_removed=False)

class Discussion(models.Model):
    subject = models.CharField(_('subject'), max_length=255)
    body = models.TextField(_('body'))
    user = models.ForeignKey(User, verbose_name=_('user'),
                             related_name='discussions')

    content_type = models.ForeignKey(ContentType, 
                                     verbose_name=_('content type'))
    object_id = models.PositiveIntegerField(_('object id'))
    content_object = generic.GenericForeignKey('content_type', 'object_id')

    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)
    parent = models.ForeignKey("Discussion", null=True, verbose_name=_('parent'))
    is_public = models.BooleanField(_('is public'), default=False)
    is_removed = models.BooleanField(_('is removed'), default=False)
    reply_count = models.IntegerField(_('reply count'), null=True)
    objects = DiscussionManager()

    disallow_replies = models.BooleanField(_('disallow replies'), default=False)
    contact_admin = models.BooleanField(_('contact admin'), default=False)

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
        return self.content_object.get_absolute_url()

    def container(self):
        return self.content_object

    def email_recipients(self):
        if self.content_type == ContentType.objects.get(
            app_label="events", model="event"):
            event = self.content_object

            if self.contact_admin:
                # TODO: also email related-group-managers
                return event.hosts()

            guests = event.attendees()
            # @@TODO: this is too many queries, select related
            # @@TODO: check blacklist?
            return [u.contributor for u in guests if u.contributor.email != self.user.email]

        if self.content_type == ContentType.objects.get(
            app_label="challenges", model="challenge"):
            petition = self.content_object
            
            if self.contact_admin:
                # TODO: also email related-group-managers
                return [petition.creator]

            # @@TODO: check blacklist
            return [u for u in petition.supporters.all() if u.email != self.user.email]
        
        if self.content_type == ContentType.objects.get(
            app_label="groups", model="group"):
            group = self.content_object

            if self.contact_admin:
                return group.managers() or [settings.DEFAULT_FROM_EMAIL]
            
            # @@TODO: implement

        if self.content_type == ContentType.objects.get(
            app_label="auth", model="user"):
            user = self.content_object
            if self.contact_admin:
                return [user]

            # @@TODO: implement
        
        return []
        
    def email_extra_headers(self, user_object):
        if self.disallow_replies:
            # If we're not allowing replies, then the sender
            # should receive email replies out of the system.
            return {'Reply-To': self.user.email}
        return None


def alert_users_of_discussion(sender, instance, **kwargs):
    if instance.is_removed:
        return True
    if instance.reply_count:
        return True
    Stream.objects.get(slug="community-discussion").enqueue(
        content_object=instance, start=instance.created)
    return True
models.signals.post_save.connect(alert_users_of_discussion, sender=Discussion)

def update_discussion_reply_count(sender, instance, **kwargs):
    if instance.parent_id:
        parent = Discussion.objects.get(pk=instance.parent_id)
        reply_count = Discussion.objects.filter(parent=instance.parent_id, is_public=True).count()
        parent.reply_count = reply_count
        parent.save()
models.signals.post_save.connect(update_discussion_reply_count, sender=Discussion)
