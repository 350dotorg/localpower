from django.conf.urls.defaults import *

urlpatterns = patterns("events.views",
    url(r"^create/$", "create", name="event-create"),
    url(r"^(?P<event_id>\d+)/$", "show", name="event-show"),
    url(r"^(?P<event_id>\d+)/invite/(?P<token>[a-f0-9]{15})/$", "show", name="event-invite"),
    url(r"^(?P<event_id>\d+)/edit/$", "edit", name="event-edit"),
    url(r"^(?P<event_id>\d+)/guests/$", "guests", name="event-guests"),
    url(r"^(?P<event_id>\d+)/guests/add/", "guests_add", {"type":"add"}, name="event-guests-add"),
    url(r"^(?P<event_id>\d+)/guests/invite/", "guests_add", {"type":"invite"}, name="event-guests-invite"),
    url(r"^(?P<event_id>\d+)/guests/(?P<guest_id>\d+)/edit/name/", "guests_edit", {"type":"name"}, name="event-guests-edit-name"),
    url(r"^(?P<event_id>\d+)/guests/(?P<guest_id>\d+)/edit/email/", "guests_edit", {"type":"email"}, name="event-guests-edit-email"),
    url(r"^(?P<event_id>\d+)/guests/(?P<guest_id>\d+)/edit/phone/", "guests_edit", {"type":"phone"}, name="event-guests-edit-phone"),
    url(r"^(?P<event_id>\d+)/guests/(?P<guest_id>\d+)/edit/status/", "guests_edit", {"type":"rsvp_status"}, name="event-guests-edit-status"),
    url(r"^(?P<event_id>\d+)/rsvp/$", "rsvp", name="event-rsvp"),
    url(r"^(?P<event_id>\d+)/rsvp/confirm/$", "rsvp_confirm", name="event-rsvp-confirm"),
    url(r"^(?P<event_id>\d+)/rsvp/account/$", "rsvp_account", name="event-rsvp-account"),
    url(r"^rsvp_statuses/", "rsvp_statuses", name="event-rsvp_statuses"),
    url(r"^(?P<event_id>\d+)/commitments/$", "commitments", name="event-commitments"),
    url(r"^(?P<event_id>\d+)/commitments/(?P<guest_id>\d+)/$", "commitments", name="event-commitments-guest"),
    url(r"^(?P<event_id>\d+)/print/$", "print_sheet", name="event-print"),
)