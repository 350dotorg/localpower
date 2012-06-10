import datetime
from django import forms
from django.utils.translation import ugettext_lazy as _

from discussions.models import Discussion, SpamFlag

from utils import hash_val

class DiscussionCreateForm(forms.Form):
    subject = forms.CharField()
    body = forms.CharField(widget=forms.Textarea, label=_("Comment"))
    parent_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    parent_id_sig = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, sender, *args, **kwargs):
        forms.Form.__init__(self, *args, **kwargs)
        # If a parent_id was passed in, sign it
        if 'parent_id' in self.initial:
            self.fields['parent_id_sig'].initial = hash_val(self.initial.get('parent_id'))
            self.fields['subject'].widget = forms.HiddenInput()
        self.sender = sender

    def clean_parent_id(self):
        """Verify the parent_id_sig"""
        parent_id = self.cleaned_data['parent_id']
        if parent_id:
            sig_check = hash_val(parent_id)
            if parent_id and sig_check <> self.data['parent_id_sig']:
                raise forms.ValidationError(_('Parent ID is currupted'))
        return parent_id

    def clean(self):
        recently = datetime.datetime.now() - datetime.timedelta(1)
        try:
            user_spamflag = SpamFlag.objects.get(user=self.sender)
        except SpamFlag.DoesNotExist:
            spam_status = "unreviewed"
        else:
            spam_status = user_spamflag.moderation_status
        if spam_status == "not_spam":
            return forms.Form.clean(self)
        if spam_status == "spam":
            raise forms.ValidationError(_("Your message was rejected because your account has been flagged as a spammer. If this was an error, contact the site staff for help."))
        discussions = Discussion.objects.filter(user=self.sender, created__gt=recently)
        if discussions.count() > 1:
            raise forms.ValidationError(_("Your message was rejected because you have already exceeded the daily message quota for your account. To increase your rate limit, contact the site staff for a review."))
        return forms.Form.clean(self)
