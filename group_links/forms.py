from django import forms

from models import ExternalLink

class ExternalLinkForm(forms.ModelForm):
    class Meta:
        model = ExternalLink
        exclude = ["group"]

    def save(self, group=None):
        if group is not None:
            self.instance.group = group
        link = super(ExternalLinkForm, self).save()
        return link
