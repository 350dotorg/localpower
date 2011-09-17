import string

from adminfilters.admin import GenericFilterAdmin
from django import forms
from django.contrib import admin
from django.db.models import F
from django.utils.dateformat import DateFormat

from geo.models import Location
from geo.fields import ZipCodeField

from models import Contributor, ContributorSurvey

class ContributorForm(forms.ModelForm):
    zipcode = ZipCodeField(required=False)

    class Meta:
        model = Contributor
        exclude = ("location", "user",)

    def __init__(self, *args, **kwargs):
        super(ContributorForm, self).__init__(*args, **kwargs)
        if self.instance.location:
            self.fields["zipcode"].initial = self.instance.location.zipcode

    def save(self, *args, **kwargs):
        if self.cleaned_data["zipcode"]:
            self.instance.location = Location.objects.get(zipcode=self.cleaned_data["zipcode"])
        return super(ContributorForm, self).save(*args, **kwargs)

class ContributorAdmin(GenericFilterAdmin):
    list_display = (
        "first_name", "last_name",
        "email", "phone", 
        "location",
        "registered_user",
        "created", "updated",)
    list_display_links = ('first_name', 'last_name')
    search_fields = ['first_name', 'last_name', 'email',
                     'location__zipcode',]
    date_hierarchy = "created"
    generic_filters = ('has_user_filter', 'collector_filter',)
    form = ContributorForm

    def has_user_filter(self, request, cl):
        if self.model.objects.all().count():
            selected = request.GET.get('user__isnull', None)
            choices = [
                (selected is None, cl.get_query_string({}, ['user__isnull']), 'All'),
                (selected == 'False', cl.get_query_string({'user__isnull': False}), 'Yes'),
                (selected == 'True', cl.get_query_string({'user__isnull': True}), 'No'),
            ]
            return cl.build_filter_spec(choices, 'has user account')
        return False

    def collector_filter(self, request, cl):
        if self.model.objects.all().count():
            selected = request.GET.get('contributorsurvey__entered_by', None)
            choices = [(selected is None,
                   cl.get_query_string({}, ['contributorsurvey__entered_by']),
                   'All')]
            collectors = ContributorSurvey.objects.distinct().filter(entered_by__isnull=False,
                contributor__in=cl.query_set).values_list("entered_by_id",
                "entered_by__first_name", "entered_by__last_name")
            for id, first_name, last_name in collectors:
                choices.append((selected == str(id),
                       cl.get_query_string({'contributorsurvey__entered_by': id}),
                       "%s %s" % (first_name, last_name)))
            return cl.build_filter_spec(choices, 'collector')
        return False

    def location(self, obj):
        if obj.location:
            return "%s, %s" % (obj.location.name, obj.location.st)
        return None

    def registered_user(self, obj):
        return "yes" if obj.user else "no"
admin.site.register(Contributor, ContributorAdmin)
