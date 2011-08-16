from django import forms
from django.utils.translation import ugettext_lazy as _

from records.models import Record
from tagging.models import Tag

from models import Action, UserActionProgress

class BaseActionForm(forms.Form):
    def __init__(self, user, action, *args, **kwargs):
        super(BaseActionForm, self).__init__(*args, **kwargs)
        self.user = user
        self.action = action

class ActionCommitForm(BaseActionForm):
    date_committed = forms.DateField(
        label=_("Commit date"),
        widget=forms.DateInput(attrs={"class": "date_commit_field"}))

    def save(self):
        return self.action.commit_for_user(
            self.user, self.cleaned_data["date_committed"])

class ActionAdminForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(queryset=Tag.objects.all(),
                                          widget=forms.CheckboxSelectMultiple,
                                          required=False)

    def __init__(self, *args, **kwargs):
        super(ActionAdminForm, self).__init__(*args, **kwargs)
        self.fields["tags"].initial = [t.pk for t in self.instance.tags]

    class Meta:
        model = Action

    def save(self, *args, **kwargs):
        tags = self.cleaned_data["tags"]
        self.instance.tags = " ".join([t.name for t in tags]) if tags and self.instance.pk else ""
        return super(ActionAdminForm, self).save(*args, **kwargs)
