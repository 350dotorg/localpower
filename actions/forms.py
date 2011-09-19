import datetime

from django import forms
from django.utils.translation import ugettext_lazy as _

from records.models import Record
from tagging.models import Tag
from tinymce.widgets import TinyMCE
from groups.forms import GroupAssociationRequestRelatedForm
from groups.models import Group

from models import Action, UserActionProgress, GroupActionProgress

class BaseActionForm(forms.Form):
    def __init__(self, user, action, *args, **kwargs):
        super(BaseActionForm, self).__init__(*args, **kwargs)
        self.user = user
        self.action = action

class ActionCommitForm(BaseActionForm):
    date_committed = forms.DateField(
        label=_("Commit date"),
        widget=forms.DateInput(format="%Y-%m-%d", 
                               attrs={"class": "date_commit_field"}))

    def __init__(self, *args, **kwargs):
        super(ActionCommitForm, self).__init__(*args, **kwargs)
        if not self.user or self.user.is_anonymous() or not self.action:
            self.fields["date_committed"].initial = (datetime.date.today() + 
                                                     datetime.timedelta(days=1))
            return
        try:
            uap = UserActionProgress.objects.get(user=self.user, action=self.action)
        except UserActionProgress.DoesNotExist:
            uap = None
        if uap and uap.date_committed:
            self.fields["date_committed"].initial = uap.date_committed
        else:
            self.fields["date_committed"].initial = (datetime.date.today() + 
                                                     datetime.timedelta(days=1))

    def save(self):
        return self.action.commit_for_user(
            self.user, self.cleaned_data["date_committed"])

class GroupActionCommitForm(BaseActionForm):
    date_committed = forms.DateField(
        label=_("Commit date"),
        widget=forms.DateInput(format="%Y-%m-%d", 
                               attrs={"class": "date_commit_field"}))
    group = forms.CharField(widget=forms.HiddenInput, required=True)

    def __init__(self, *args, **kwargs):
        group = kwargs.pop("group", None)
        super(GroupActionCommitForm, self).__init__(*args, **kwargs)
        self.group_obj = group
        self.fields["group"].initial = group.slug if group else ''
        if (not self.user or self.user.is_anonymous() 
            or not self.action
            or not self.group_obj):
            self.fields["date_committed"].initial = (datetime.date.today() + 
                                                     datetime.timedelta(days=1))
            return
        try:
            gap = GroupActionProgress.objects.get(group=self.group_obj, action=self.action)
        except GroupActionProgress.DoesNotExist:
            gap = None
        if gap and gap.date_committed:
            self.fields["date_committed"].initial = gap.date_committed
        else:
            self.fields["date_committed"].initial = (datetime.date.today() + 
                                                     datetime.timedelta(days=1))

    def clean_group(self):
        group = self.cleaned_data.get("group")
        if not group:
            return
        try:
            group = Group.objects.get(slug=group)
        except Group.DoesNotExist:
            raise forms.ValidationError(_("The specific group does not exist."))
        if self.user and self.user not in group:
            raise forms.ValidationError(_("You must be a member of the group."))

    def save(self):
        link_form = ActionGroupLinkForm(self.user, instance=self.action,
                                        data={'groups': [self.group_obj.pk]})
        if not link_form.is_valid():
            return
        action = link_form.save()
        if self.group_obj in link_form.cleaned_data["groups"]:
            return self.action.commit_for_group(
                self.group_obj, self.cleaned_data["date_committed"])

class ActionAdminForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(),
                                          widget=forms.CheckboxSelectMultiple,
                                          required=False)
    content = forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))

    def __init__(self, *args, **kwargs):
        super(ActionAdminForm, self).__init__(*args, **kwargs)
        self.fields["tags"].initial = [t.pk for t in self.instance.tags]

    class Meta:
        model = Action

    def save(self, *args, **kwargs):
        tags = self.cleaned_data["tags"]
        self.instance.tags = " ".join([t.name for t in tags]) if tags and self.instance.pk else ""
        return super(ActionAdminForm, self).save(*args, **kwargs)

class ActionGroupLinkForm(forms.ModelForm, GroupAssociationRequestRelatedForm):
    class Meta:
        model = Action
        fields = ("groups",)
        widgets = {
            "groups": forms.CheckboxSelectMultiple(),
            }

    def __init__(self, user, *args, **kwargs):
        super(ActionGroupLinkForm, self).__init__(*args, **kwargs)
        self.user = user
        self.init_groups(user)

    def save(self, *args, **kwargs):
        action = super(ActionGroupLinkForm, self).save(*args, **kwargs)
        self.save_groups(action)
        return action
