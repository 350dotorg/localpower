from django import forms
from django.core.urlresolvers import reverse
from django.template.loader import render_to_string
from django.utils.translation import ugettext_lazy as _

VAMPIRE_OPTIONS = (
    ('y', _('Yes'),),
    ('n', _('No'),),
    ('u', _('Not sure'),),
)

class VampireSlayerWidget(forms.RadioSelect):
    def __init__(self, attrs=None, recommended=None, *args, **kwargs):
        html_class = {"class": "vampire_slayer"}
        if attrs:
            attrs.update(html_class)
        else:
            attrs = html_class
        super(VampireSlayerWidget, self).__init__(attrs=attrs, *args, **kwargs)

class VampireField(forms.ChoiceField):
    def __init__(self, choices=None, widget=None, *args, **kwargs):
        if not choices:
            choices=VAMPIRE_OPTIONS
        if not widget:
            widget = VampireSlayerWidget
        super(VampireField, self).__init__(choices=choices, widget=widget, *args, **kwargs)

class VampirePowerWorksheetForm2(forms.Form):
    computers = VampireField(required=False)
    monitor = VampireField(required=False, label=_("Computer Monitor"))
    computer_speakers = VampireField(required=False)
    televisions = VampireField(required=False)
    dvd_players = VampireField(required=False, label=_("DVD/VCR Players"))
    cable_box = VampireField(required=False, label=_("Cable Box/DVR"))
    game_systems = VampireField(required=False, label=_("Video game Systems"))

    def home_office_fields(self):
        return [self['computers'], self['monitor'], self['computer_speakers']]

    def home_entertainment_fields(self):
        return [self['televisions'], self['dvd_players'], self['cable_box'], self['game_systems']]

    def my_vampires(self):
        return [f for f in self if f.data == 'y']
