from django import forms
from django.utils.translation import ugettext_lazy as _

class Honeypot(forms.CharField):
    def __init__(self,
                 required=False, 
                 label=_("Don't use or else your submission will be flagged as spam"),
                 widget=forms.HiddenInput, 
                 *args, **kwargs):
        self.required, self.label, self.widget = required, label, widget
        super(Honeypot, self).__init__(*args, **kwargs)

    def clean(self, value):
        """Check that nothing's been entered into the honeypot."""
        if value:
            raise forms.ValidationError(self.label)
        return value
