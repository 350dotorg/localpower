from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from commitments.models import Contributor
from commitments.forms import ContributorForm
from groups.forms import GroupAssociationRequestRelatedForm

from models import Challenge, Support

class ChallengeForm(forms.ModelForm, GroupAssociationRequestRelatedForm):
    goal = forms.IntegerField(min_value=1, 
                              label=_("How many signatures do you want to collect?"))
    target = forms.CharField(min_length=3, widget=forms.TextInput(), label=_(
            "Who do you want to petition?"))
    demand = forms.CharField(min_length=10, widget=forms.TextInput(), label=_(
            "What do you want them to do?"))
    description = forms.CharField(min_length=15, widget=forms.Textarea(attrs={'rows': 5}),
                                  label=_(
            "Why is this important?"))

    class Meta:
        model = Challenge
        fields = ('target', 'demand', 'description', 'goal', 'groups')
        widgets = {
            "groups": forms.CheckboxSelectMultiple(),
            "title": forms.HiddenInput(),
            }

    def __init__(self, user, *args, **kwargs):
        super(ChallengeForm, self).__init__(*args, **kwargs)
        self.user = user
        self.init_groups(user)
        
    def save(self, *args, **kwargs):
        challenge = super(ChallengeForm, self).save(*args, **kwargs)
        challenge.title = challenge.title or u"%s: %s" % (self.cleaned_data['target'],
                                                          self.cleaned_data['demand'])
        challenge.save()
        self.save_groups(challenge)
        return challenge

class PetitionForm(ContributorForm):
    first_name = forms.CharField(min_length=2, widget=forms.TextInput(attrs={'class':'form_row_half'}))
    last_name = forms.CharField(min_length=1, widget=forms.TextInput(attrs={'class':'form_row_half form_row_half_last'}))

    class Meta:
        model = Contributor
        fields = ('first_name', 'last_name', 'email',)

    def __init__(self, challenge, *args, **kwargs):
        self.challenge = challenge
        super(PetitionForm, self).__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        contributor = super(PetitionForm, self).save(*args, **kwargs)
        support, created = Support.objects.get_or_create(challenge=self.challenge,
            contributor=contributor)
        return support
