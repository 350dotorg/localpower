from smtplib import SMTPException

from django import forms
from django.contrib.sites.models import Site
from django.core.exceptions import ObjectDoesNotExist
from django.core.mail import EmailMessage
from django.template import loader
from django.utils.translation import ugettext_lazy as _

from utils import hash_val
from messaging.models import Stream

from models import Invitation, make_token
from fields import MultiEmailField

class InviteForm(forms.ModelForm):
    emails = MultiEmailField(
        label=_("Email addresses"), required=True,
        widget=forms.Textarea,
        help_text=_("Separate multiple email addresses with a comma."))
    note = forms.CharField(widget=forms.Textarea, 
                           label=_("Personal note (optional)"),
                           required=False)
    signature = forms.CharField(widget=forms.HiddenInput, required=True)

    class Meta:
        model = Invitation
        fields = ("emails", "note", "content_type", "object_pk")
        widgets = {
            "token": forms.HiddenInput,
            "content_type": forms.HiddenInput,
            "object_pk": forms.HiddenInput,
        }

    def __init__(self, *args, **kwargs):
        form = super(InviteForm, self).__init__(*args, **kwargs)
        self.fields["signature"].initial = hash_val((self.instance.content_type, self.instance.object_pk,))

    def clean(self):
        if "content_type" in self.cleaned_data and "object_pk" in self.cleaned_data and "signature" in self.cleaned_data:
            content_type = self.cleaned_data["content_type"]
            object_pk = self.cleaned_data["object_pk"]
            if content_type or object_pk:
                try:
                    target = content_type.get_object_for_this_type(pk=object_pk)
                except ObjectDoesNotExist:
                    raise forms.ValidationError(
                        _("No object found matching %(object_pk)s)") % {'object_pk': object_pk})
                except ValueError:
                    raise forms.ValidationError(_("Invalid parameters %(content_type)s, %(object_pk)s") % {'content_type': content_type, 'object_pk': object_pk})
                if hash_val((content_type, object_pk,)) != self.cleaned_data["signature"]:
                    raise forms.ValidationError(_("Signature has been corrupted"))
        return self.cleaned_data

    def save(self, *args, **kwargs):
        invites = []
        for email in self.cleaned_data["emails"]:
            self.instance.pk = None
            self.instance.email = email
            self.instance.token = make_token()
            invite = super(InviteForm, self).save(*args, **kwargs)
            ct = self.instance.content_type
            stream = None
            if ct:
                try:
                    stream = Stream.objects.get(slug="invite-%s" % ct.model_class()._meta.app_label)
                except Stream.DoesNotExist:
                    pass
            stream = stream or Stream.objects.get(slug="invite")
            stream.enqueue(content_object=invite, start=invite.created,
                extra_params={"note": self.cleaned_data["note"]})
            invites.append(Invitation.objects.get(pk=invite.pk))
        return invites
