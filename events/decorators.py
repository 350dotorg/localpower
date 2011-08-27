from functools import wraps

from django.shortcuts import get_object_or_404
from django.utils.decorators import available_attrs
from django.utils.translation import ugettext as _

from utils import forbidden

from models import Event

def user_is_event_manager(view_func):
    def _wrapped_view(request, event_id, *args, **kwargs):
        event = get_object_or_404(Event, id=event_id)
        if event.has_manager_privileges(request.user):
            return view_func(request, event_id, *args, **kwargs)
        return forbidden(request, _("You must be an event manager"))
    return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)

def user_is_guest(view_func):
    def _wrapped_view(request, event_id, *args, **kwargs):
        event = get_object_or_404(Event, id=event_id)
        if request.user.has_perm("events.view_any_event") or event.is_guest(request):
            return view_func(request, event_id, *args, **kwargs)
        return forbidden(request, _("You are not a registered guest"))
    return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)

def user_is_guest_or_has_token(view_func):
    def _wrapped_view(request, event_id, *args, **kwargs):
        event = get_object_or_404(Event, id=event_id)
        if not request.user.has_perm("events.view_any_event") and not event.is_guest(request) and event.is_private:
            # if the user does not have view_any privledges, is not already a guest or is
            # and the event is private, ensure they have a valid token
            token = kwargs.get("token", request.POST.get("token", None))
            if not token:
                return forbidden(request, _("You need an invitation for this event"))
            if not event.is_token_valid(token):
                return forbidden(request, _("Invitation code is not valid for this event"))
        return view_func(request, event_id, *args, **kwargs)
    return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)
