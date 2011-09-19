import os
from datetime import datetime, timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction, IntegrityError
from django.utils.translation import ugettext_lazy as _

import tagging

from commitments.models import Commitment
from records.models import Record
from dated_static.templatetags.dated_static import timestamp_file
from messaging.models import Stream, Queue
from rah.signals import logged_in

class ActionManager(models.Manager):

    def get_popular(self, count=6):
        # Returns the most popular actions where popularity is defined as the sum of completed and commited users
        # TODO: Write a unit test for get_popular
        actions = Action.objects.all()
        count = actions.count() if actions.count() < count else count
        return sorted(actions, reverse=True, key=lambda action: action.users_completed+action.users_committed)[:count]

    def actions_by_status(self, user):
        actions = Action.objects.select_related().all().extra(select_params = (user.id,),
                    select = { 'completed': 'SELECT uap.is_completed FROM actions_useractionprogress uap \
                                             WHERE uap.user_id = %s AND uap.action_id = actions_action.id'
                    }).extra(select_params = (user.id,),
                    select = { 'committed': 'SELECT uap.date_committed FROM actions_useractionprogress uap \
                                             WHERE uap.user_id = %s AND uap.action_id = actions_action.id'
                    })
        def action_sorter(action):
            if action.completed:
                return 2
            elif action.committed:
                return 0
            else:
                return 1
        return sorted(actions, key=action_sorter)

    def process_commitment_card(self, user, new_user=False):
        # Are there any event_commitments for this user that were updated after the user's last_login timestamp?
        if new_user:
            commitments = Commitment.objects.filter(contributor__email=user.email, action__isnull=False)
        else:
            commitments = Commitment.objects.filter(updated__gt=user.last_login, contributor__email=user.email, action__isnull=False)
        changes = []
        # If yes, apply those commitments to the user's account
        for commitment in commitments:
            try:
                # If there is a conflict, go with the later of: user's action date | event date
                uap = UserActionProgress.objects.get(action=commitment.action, user=user)
                if commitment.answer == "D":
                    commitment.action.complete_for_user(user)
                    changes.append(commitment)
            except UserActionProgress.DoesNotExist:
                if commitment.answer == "D":
                    commitment.action.complete_for_user(user)
                elif commitment.answer == "C":
                    uap, record = commitment.action.commit_for_user(user, commitment.date_committed, add_to_stream=False)
                    # transition the guest commitment messages to user commitment messages
                    messages = Queue.objects.filter(content_type=ContentType.objects.get_for_model(commitment),
                        object_pk=commitment.pk)
                    messages.update(content_type=ContentType.objects.get_for_model(uap),
                        object_pk=uap.pk, batch_content_type=ContentType.objects.get_for_model(uap.user),
                        batch_object_pk=uap.user.pk)
                changes.append(commitment)
        return changes

class Action(models.Model):
    class Meta:
        verbose_name = _('action')
        verbose_name_plural = _('actions')

    name = models.CharField(_('name'), max_length=255, unique=True)
    slug = models.SlugField(_('slug'), unique=True)
    teaser = models.TextField(_('teaser'))
    content = models.TextField(_('content'))
    points = models.IntegerField(_('points'), default=0)
    users_completed = models.IntegerField(_('users completed'), default=0)
    users_committed = models.IntegerField(_('users committed'), default=0)
    users = models.ManyToManyField(User, through="UserActionProgress",
                                   verbose_name=_('users'))
    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)
    objects = ActionManager()

    groups = models.ManyToManyField(
        "groups.Group", blank=True,
        verbose_name=_("Communities"))

    def creator(self):
        return ""

    def image_paths(self):
        images = {}
        images['small'] = timestamp_file("images/badges/%s-action-badge-0-small.png" % self.slug)
        images['large'] = timestamp_file("images/badges/%s-action-badge-0-large.png" % self.slug)
        images['white'] = timestamp_file("images/badges/%s-action-badge-0-white.png" % self.slug)
        return images


    @transaction.commit_on_success
    def complete_for_user(self, user):
        try:
            uap = UserActionProgress.objects.create(user=user, action=self)
        except IntegrityError:
            transaction.commit()
            uap = UserActionProgress.objects.get(user=user, action=self)
        was_completed = uap.is_completed
        uap.is_completed = True
        uap.save()
        record = None
        if not was_completed:
            Stream.objects.get(slug="commitment").dequeue(content_object=uap)
            record = Record.objects.create_record(user, "action_complete", self)
        return (uap, record)

    def undo_for_user(self, user):
        try:
            uap = UserActionProgress.objects.get(user=user, action=self)
            was_completed = uap.is_completed
            uap.is_completed = False
            uap.save()
            if was_completed:
                if uap.date_committed:
                    Stream.objects.get(slug="commitment").upqueue(content_object=uap,
                        start=uap.created, end=uap.date_committed, batch_content_object=user)
                Record.objects.void_record(user, "action_complete", self)
        except UserActionProgress.DoesNotExist:
            return False
        return True

    @transaction.commit_on_success
    def commit_for_user(self, user, date, add_to_stream=True):
        try:
            uap = UserActionProgress.objects.create(user=user, action=self)
        except IntegrityError:
            transaction.commit()
            uap = UserActionProgress.objects.get(user=user, action=self)
        was_committed = uap.date_committed <> None
        uap.date_committed = date
        uap.save()
        record = None
        if add_to_stream:
            if was_committed:
                Stream.objects.get(slug="commitment").upqueue(content_object=uap, start=uap.created,
                    end=uap.date_committed, batch_content_object=user)
            else:
                Stream.objects.get(slug="commitment").enqueue(content_object=uap, start=uap.updated,
                    end=uap.date_committed, batch_content_object=user)
                record = Record.objects.create_record(user, "action_commitment", self, data={"date_committed": date})
        return (uap, record)

    def cancel_for_user(self, user):
        try:
            uap = UserActionProgress.objects.get(user=user, action=self)
            was_committed = uap.date_committed <> None
            uap.date_committed = None
            uap.save()
            if was_committed:
                Stream.objects.get(slug="commitment").dequeue(content_object=uap)
                Record.objects.void_record(user, "action_commitment", self)
        except UserActionProgress.DoesNotExist:
            return False
        return True

    def tag_list(self):
        tag_names = [t.name for t in self.tags]
        return ", ".join(tag_names) if tag_names else ""
    tag_list.short_description = "Tags"

    def action_forms_with_data(self, user):
        return ActionForm.objects.filter(action=self).extra(
                select_params = (user.id,),
                select = { "data": """SELECT afd.data
                                        FROM actions_actionformdata afd
                                        WHERE afd.user_id = %s
                                        AND actions_actionform.id = afd.action_form_id"""})

    def get_detail_illustration(self):
        return timestamp_file("images/badges/%s-small." % self.slug)

    def get_nugget_illustration(self):
        return timestamp_file("images/actions/%s/action_nugget.jpg" % self.slug)

    def has_illustration(self):
        path = "images/actions/%s/action_detail.jpg" % self.slug
        return os.path.exists(os.path.join(settings.MEDIA_ROOT, path))

    def __unicode__(self):
        return u"%s" % self.name

    @models.permalink
    def get_absolute_url(self):
        return ("action_detail", [str(self.slug)])
tagging.register(Action)

class UserActionProgressManager(models.Manager):
    def commitments_for_user(self, user):
         return self.select_related().filter(user=user, is_completed=False,
            date_committed__isnull=False).order_by("date_committed")

    def completed_for_user(self, user):
         return self.select_related().filter(user=user, is_completed=True
                                             ).order_by("date_committed")

    def pending_commitments(self, user=None):
        queryset = self.filter(is_completed=False, date_committed__isnull=False)
        return queryset if not user else queryset.filter(user=user)

class UserActionProgress(models.Model):
    user = models.ForeignKey(User, verbose_name=_('user'))
    action = models.ForeignKey(Action, verbose_name=_('action'))
    is_completed = models.BooleanField(_('is completed'), default=False)
    date_committed = models.DateField(_('date completed'), null=True)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)
    objects = UserActionProgressManager()

    class Meta:
        unique_together = ("user", "action",)
        verbose_name = _("user action progress")
        verbose_name_plural = _("user action progress")

    def other_commitments(self):
        return UserActionProgress.objects.filter(user=self.user, date_committed__isnull=False,
            is_completed=0).exclude(pk=self.pk).order_by("date_committed")

    def email(self):
        return self.user.email

    def __unicode__(self):
        return _("%(user)s is working on %(action)s") % {'user': self.user,
                                                         'action': self.action}


class GroupActionProgress(models.Model):
    group = models.ForeignKey(Group, verbose_name=_('group'))
    action = models.ForeignKey(Action, verbose_name=_('action'))
    is_completed = models.BooleanField(_('is completed'), default=False)
    date_committed = models.DateField(_('date completed'), null=True)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)
    objects = UserActionProgressManager()

    class Meta:
        unique_together = ("group", "action",)
        verbose_name = _("group action progress")
        verbose_name_plural = _("group action progress")

    def other_commitments(self):
        return GroupActionProgress.objects.filter(group=self.group, date_committed__isnull=False,
            is_completed=0).exclude(pk=self.pk).order_by("date_committed")

    ## TODO: send messaging.message emails to all group admins
    #def email(self):
    #    return self.user.email

    def __unicode__(self):
        return _("%(group)s is working on %(action)s") % {'user': self.group,
                                                          'action': self.action}

class ActionForm(models.Model):
    """
    ActionForm is used to link a worksheet form to an action.  Since we will use
    introspection to create an instance of the form, it is imparitive that the form_name
    field match the action class name of the django form.
    """
    action = models.ForeignKey(Action, verbose_name=_('action'))
    form_name = models.CharField(_('form name'), max_length=100)
    var_name = models.CharField(_('var name'), max_length=100)
    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)

    class Meta:
        unique_together = ("action", "form_name",)
        verbose_name = _("action form")
        verbose_name_plural = _("action forms")

    def __unicode__(self):
        return _("%(action)s is using form %(form_name)s") % {
            'action': self.action, 'form_name': self.form_name}

class ActionFormData(models.Model):
    """
    ActionFormData is used to store a users state for a particular action form, the
    data field will contain serialized data that can be reformed into a request.POST
    dict and initialized with the corresponding ActionForm.
    """
    action_form = models.ForeignKey(ActionForm, verbose_name=_('action form'))
    user = models.ForeignKey(User, verbose_name=_('user'))
    data = models.TextField(_('data'))
    # TODO: make ActionFormData.data a serialized field
    created = models.DateTimeField(_('created'), auto_now_add=True)
    updated = models.DateTimeField(_('updated'), auto_now=True)

    class Meta:
        unique_together = ("action_form", "user",)
        verbose_name = ("action form data")
        verbose_name_plural = ("action form data")

    def __unicode__(self):
        return _("%(user)s is working on %(action_form)s") % {
            'user': self.user, 'action_form': self.action_form}

"""
SIGNALS!
"""
def update_action_aggregates(sender, instance, **kwargs):
    instance.action.users_completed = UserActionProgress.objects.filter(action=instance.action, is_completed=True).count()
    instance.action.users_committed = UserActionProgress.objects.filter(action=instance.action, date_committed__isnull=False).count()
    instance.action.save()
models.signals.post_save.connect(update_action_aggregates, sender=UserActionProgress)

def apply_changes_from_commitment_cards(sender, request, user, is_new_user, **kwargs):
    changes = Action.objects.process_commitment_card(user, new_user=is_new_user)
    if not changes:
        return
    messages.success(request,
                     _("%(num_actions)s actions were applied to "
                       "your account from a commitment card") % {'num_actions': len(changes)},
                     extra_tags="sticky")
logged_in.connect(apply_changes_from_commitment_cards)
