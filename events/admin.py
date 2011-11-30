from django.contrib import admin
from django.db.models import F
from django.utils.dateformat import DateFormat
from django.utils.translation import ugettext_lazy as _

from models import Event, Guest
from forms import EventForm

class EventAdminForm(EventForm):
    def __init__(self, *args, **kwargs):
        super(EventAdminForm, self).__init__(None, *args, **kwargs)

class EventAdmin(admin.ModelAdmin):
    valid_lookups = ("geom",)
    list_display = ("title", "_when", "geom", "hosts", "guests", "guests_with_commitment_card", "is_private",)
    list_filter = ("when", "is_private", "limit", "start", "duration", "details",)
    date_hierarchy = "when"
    readonly_fields = ("limit",)
    form = EventAdminForm

    def lookup_allowed(self, lookup, *args, **kwargs):
        for valid_lookup in self.valid_lookups:
            if lookup.startswith(valid_lookup):
                return True
        return admin.ModelAdmin.lookup_allowed(self, lookup, *args, **kwargs)

    def save_form(self, request, form, change):
        form.user = request.user
        return super(EventAdmin, self).save_form(request, form, change)

    def name(self, obj):
        return obj.place_name or obj.__unicode__()

    def _when(self, obj):
        return DateFormat(obj.start_datetime()).format("M j Y @ g:ia")
    _when.short_description = _("When")

    def city(self, obj):
        return '' # obj.location.name

    def state(self, obj):
        return '' #obj.location.st

    def guests(self, obj):
        return obj.guest_set.count()

    def guests_with_commitment_card(self, obj):
        return Guest.objects.distinct().filter(event=obj, contributor__survey=F('event__default_survey')).count()

    def hosts(self, obj):
        return ", ".join([g.contributor.name for g in obj.hosts()])
    hosts.short_description = _("Hosts")

admin.site.register(Event, EventAdmin)
