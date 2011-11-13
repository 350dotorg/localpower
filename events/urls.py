from django.conf.urls.defaults import *

from search_widget.views import search_list

from models import Event

event_search_info = {
    'queryset': Event.objects.all(),
    'paginate_by': 5,
    'search_fields': ['title', 'details', 'where', 'geom__formatted_address'],
    'template_name': 'events/_search_listing',
}

urlpatterns = patterns("events.views",
    # TODO: Make these underscores instead of hyphens
    url(r"^$", "show", name="event-show"),
    url(r"^create/$", "create", name="event-create"),
    url(r"^(?P<event_id>\d+)/$", "detail", name="event-detail"),
    url(r"^(?P<event_id>\d+)/invite/(?P<token>[a-f0-9]{15})/$", "detail", name="event-invite"),
    url(r"^(?P<event_id>\d+)/edit/$", "edit", name="event-edit"),
    url(r"^(?P<event_id>\d+)/guests/add/", "guests_add", name="event-guests-add"),
    url(r"^(?P<event_id>\d+)/guests/invite/", "guests_invite", name="event-guests-invite"),
    url(r"^(?P<event_id>\d+)/guests/(?P<guest_id>\d+)/edit/status/", "guests_edit", {"type":"rsvp_status"}, name="event-guests-edit-status"),
    url(r"^(?P<event_id>\d+)/hosts/", "hosts", name="event-hosts"),
    url(r"^(?P<event_id>\d+)/rsvp/$", "rsvp", name="event-rsvp"),
    url(r"^(?P<event_id>\d+)/rsvp/confirm/$", "rsvp_confirm", name="event-rsvp-confirm"),
    url(r"^(?P<event_id>\d+)/rsvp/account/$", "rsvp_account", name="event-rsvp-account"),
    url(r"^(?P<event_id>\d+)/rsvp/cancel/$", "rsvp_cancel", name="event-rsvp-cancel"),
    url(r"^rsvp_statuses/", "rsvp_statuses", name="event-rsvp_statuses"),

    url(r"^(?P<event_id>\d+)/commitments/$", "event_commitments", name="event-commitments"),

    url(r'^(?P<event_id>\d+)/discussions/create/$', 'event_disc_create', name='event_disc_create'),

    url(r"^(?P<event_id>\d+)/print/$", "print_sheet", name="event-print"),
    url(r"^(?P<event_id>\d+)/spreadsheet/$", "spreadsheet", name="event-spreadsheet"),
    url(r"^(?P<event_id>\d+)/guests/reminder/$", "message", {"type": "reminder"}, name="event-reminder"),
    url(r"^(?P<event_id>\d+)/guests/announcement/$", "message", {"type": "announcement"}, name="event-announcement"),
    url(r"^search/$", search_list, event_search_info, name='event_search'),
    url(r"^archive/$", "archive", name="event-archive"),
)
