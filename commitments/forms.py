from django import forms
from django.forms import ModelForm
from django.utils.translation import ugettext_lazy as _

from geo.fields import GoogleLocationField
from geo.models import Location

from models import Contributor

class ContributorForm(forms.ModelForm):

    geom = GoogleLocationField(
        label=_("Location"),
        help_text=_("(Optional) Be as specific as you're comfortable sharing"))
    email = forms.EmailField(label='Email', widget=forms.TextInput, required=False)
    first_name = forms.CharField(min_length=2)

    class Meta:
        model = Contributor
        fields = ('first_name', 'last_name', 'email', 'phone')

    def __init__(self, *args, **kwargs):
        super(ContributorForm, self).__init__(*args, **kwargs)
        ## geom/location should be at bottom
        self.fields["geom"].initial = ""
        if self.instance and self.instance.geom:
            self.fields["geom"].initial = self.instance.geom.raw_address

    def clean(self):
        email = self.cleaned_data.get('email', None)

        # If there's an email we'll try to match it to contributors in the data. If there's already a contributor id
        # then we can skip the lookup because we're editing a known contributor
        if email and not self.instance.id:
            try:
                self.instance = Contributor.objects.get(email=email)
            except Contributor.DoesNotExist:
                # We didn't match this email to an existing contributor, so we're going to make a new one
                pass
            else:
                # We don't want to delete any fields that may exist in the database
                for key in self.cleaned_data.keys():
                    if self.cleaned_data.get(key) == '':
                        del(self.cleaned_data[key])

        return self.cleaned_data

    def clean_email(self):
        # If there is no email entered, make sure it's set to NULL in the DB because there can't be more than one ''
        email = self.cleaned_data.get('email')
        if email == '':
            self.cleaned_data['email'] = None

        return self.cleaned_data['email']

    def save(self, *args, **kwargs):
        if self.cleaned_data["geom"]:
            point = self.cleaned_data["geom"]
            self.instance.geom = point
        return super(ContributorForm, self).save(*args, **kwargs)
