from django import forms
from django.contrib.contenttypes.models import ContentType

from commitments.models import Contributor
from commitments.forms import ContributorForm
from groups.models import GroupAssociationRequest

from models import Challenge, Support

class ChallengeForm(forms.ModelForm):
    goal = forms.IntegerField(min_value=1, help_text="How many petitions do you want to collect?")

    class Meta:
        model = Challenge
        fields = ('title', 'description', 'goal', 'groups')
        widgets = {
            "groups": forms.CheckboxSelectMultiple(),
            }

    def __init__(self, user, *args, **kwargs):
        super(ChallengeForm, self).__init__(*args, **kwargs)
        self.user = user
        groups = self.fields["groups"]
        groups.queryset = groups.queryset.filter(groupusers__user=user)
        if not groups.queryset:
            groups.help_text = "You need to be a member of a community first"
        else:
            groups.help_text = None

    def clean_groups(self):
        data = self.cleaned_data["groups"]
        approved_groups, self.requested_groups = [], []
        content_type = ContentType.objects.get_for_model(self.instance)
        for g in data:
            if g.is_user_manager(self.user) or GroupAssociationRequest.objects.filter(
                content_type=content_type, object_id=self.instance.pk,
                group=g, approved=True).exists():
                approved_groups.append(g)
            else:
                self.requested_groups.append(g)
        return approved_groups

    def save(self, *args, **kwargs):
        challenge = super(ChallengeForm, self).save(*args, **kwargs)
        content_type = ContentType.objects.get_for_model(challenge)
        for g in self.requested_groups:
            request, created = GroupAssociationRequest.objects.get_or_create(
                content_type=content_type, object_id=challenge.pk,
                group=g)
            # TODO: notify user of groups requested
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
