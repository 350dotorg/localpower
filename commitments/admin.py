import string

from adminfilters.admin import GenericFilterAdmin
from django import forms
from django.contrib import admin
from django.db.models import F
from django.utils.dateformat import DateFormat

from geo.models import Location

from models import Contributor, ContributorSurvey
from forms import ContributorForm

class ContributorAdmin(GenericFilterAdmin):
    list_display = (
        "first_name", "last_name",
        "email", "phone", 
        "geom",
        "registered_user",
        "created", "updated",)
    list_display_links = ('first_name', 'last_name')
    search_fields = ['first_name', 'last_name', 'email',
                     'geom__formatted_address',]
    date_hierarchy = "created"
    generic_filters = ('has_user_filter', 'collector_filter',)
    form = ContributorForm

    def lookup_allowed(self, lookup, *args, **kw):
        return lookup in ("user__isnull", 
                          "contributorsurvey__entered_by")

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
            collectors = ContributorSurvey.objects.distinct().filter(
                entered_by__isnull=False,
                contributor__in=cl.query_set).values_list("entered_by_id",
                "entered_by__first_name", "entered_by__last_name")
            for id, first_name, last_name in collectors:
                choices.append((selected == str(id),
                       cl.get_query_string({'contributorsurvey__entered_by': id}),
                       "%s %s" % (first_name, last_name)))
            return cl.build_filter_spec(choices, 'collector')
        return False

    def registered_user(self, obj):
        return "yes" if obj.user else "no"
admin.site.register(Contributor, ContributorAdmin)
