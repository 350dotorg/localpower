import csv
import datetime
import json
from pdf import render_to_pdf

from django.contrib import messages
from django.contrib import auth
from django.contrib.auth.decorators import login_required
from django.db.models.fields import FieldDoesNotExist
from django.forms import ValidationError
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST

from utils import forbidden
from rah.signals import logged_in
from invite.models import Invitation, make_token
from records.models import Record

from models import Event, Guest
from forms import EventForm, GuestInviteForm, GuestAddForm, GuestListForm, GuestEditForm, \
    RsvpForm, RsvpConfirmForm, RsvpAccountForm, MessageForm, HostForm
from decorators import user_is_event_manager, user_is_guest, user_is_guest_or_has_token

def show(request):
    nav_selected = "events"
    map_events = Event.objects.filter(is_private=False, geom__isnull=False)
    events = Event.objects.filter(is_private=False).order_by("-when", "-start")[:4]
    return render_to_response("events/show.html", locals(), context_instance=RequestContext(request))

def archive(request):
    nav_selected = "events"
    events = Event.objects.filter(is_private=False).order_by("-when", "-start")
    return render_to_response("events/archive.html", locals(), context_instance=RequestContext(request))

@login_required
def create(request):
    nav_selected = "events"
    form = EventForm(user=request.user, data=(request.POST or None),
                     initial={"groups": request.GET.getlist("groups")})
    if form.is_valid():
        event = form.save()
        Record.objects.create_record(request.user, "event_create", event)
        messages.success(request, "%s has been created." % event)
        return redirect(event)
    return render_to_response("events/create.html", locals(), context_instance=RequestContext(request))

@user_is_guest_or_has_token
def detail(request, event_id, token=None):
    nav_selected = "events"
    event = get_object_or_404(Event, id=event_id)
    guest = event.current_guest(request, token)
    has_manager_privileges = event.has_manager_privileges(request.user)

    rsvp_form = RsvpForm(instance=guest, initial={
            "token": token, "rsvp_status": "A"})

    from groups.models import GroupUsers
    manager = None
    if has_manager_privileges:
        manager = GroupUsers.objects.filter(
            user=request.user,
            group__in=event.groups.all(),
            is_manager=True)
        try:
            manager = manager[0]
        except IndexError:
            manager = None

    groups_to_join = event.groups.all()
    groups_to_join = groups_to_join.filter(is_external_link_only=False)
    if request.user.is_authenticated():
        groups_to_join = groups_to_join.exclude(groupusers__user=request.user)

    return render_to_response("events/detail.html", locals(), context_instance=RequestContext(request))

@login_required
@user_is_event_manager
@csrf_protect
def event_disc_create(request, event_id):
    nav_selected = "events"
    event = get_object_or_404(Event, id=event_id)

    from groups.forms import DiscussionCreateForm
    from discussions.models import Discussion

    if not event.has_manager_privileges(request.user):
        return redirect(event)

    if request.method == "POST":
        disc_form = DiscussionCreateForm(request.POST)
        if disc_form.is_valid():
            disc = Discussion.objects.create(
                subject=disc_form.cleaned_data['subject'],
                body=disc_form.cleaned_data['body'],
                parent_id=None,
                user=request.user,
                content_object=event,
                reply_count=0,
                is_public=False,
                disallow_replies=True)
            messages.success(request, "Your message has been sent to the event's participants.")
            return redirect(event)
    else:
        disc_form = DiscussionCreateForm()

    return render_to_response("events/event_disc_create.html", locals(), 
                              context_instance=RequestContext(request)) 


@login_required
@user_is_event_manager
def edit(request, event_id):
    nav_selected = "events"
    event = get_object_or_404(Event, id=event_id)
    form = EventForm(user=request.user, instance=event, data=(request.POST or None))
    if form.is_valid():
        event = form.save()
        messages.success(request, "%s has been changed." % event)
        return redirect(event)
    return render_to_response("events/edit.html", locals(), context_instance=RequestContext(request))

@login_required
@user_is_event_manager
def guests_add(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    guest = Guest(event=event)
    form = GuestAddForm(instance=guest, data=(request.POST or None))
    if form.is_valid():
        form.save()
        return redirect(event)
    template = "events/_guests_add.html" if request.is_ajax() else "events/guests_add.html"
    return render_to_response(template, locals(), context_instance=RequestContext(request))

@login_required
@user_is_event_manager
def guests_invite(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    invite = Invitation(user=request.user, content_object=event)
    form = GuestInviteForm(instance=invite, initial={"emails": request.GET.get("emails", "")},
        data=(request.POST or None))
    if form.is_valid():
        form.save()
        return redirect(event)
    template = "events/_guests_invite.html" if request.is_ajax() else "events/guests_invite.html"
    return render_to_response(template, locals(), context_instance=RequestContext(request))

@login_required
@user_is_event_manager
def event_commitments(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return HttpResponse("ok")

@login_required
@require_POST
@user_is_event_manager
def guests_edit(request, event_id, guest_id, type):
    event = get_object_or_404(Event, id=event_id)
    guest = get_object_or_404(Guest, id=guest_id)
    if guest.event != event:
        return forbidden(request, "Guest is not a member of this event")
    if not hasattr(guest, type) and not hasattr(guest.contributor, type):
        return forbidden(request, "Guest has no attribute %s" % type)
    data = request.POST.copy()
    for field in guest._meta.fields:
        data[field.name] = field.value_from_object(guest)
    data[type] = data.get("value")
    form = GuestEditForm(instance=guest, data=data)
    if form.is_valid():
        form.save()
        messages.success(request, "%s has been updated" % guest)
    else:
        for field,errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    guest = Guest.objects.get(id=guest_id)
    message_html = render_to_string("_messages.html", {}, context_instance=RequestContext(request))
    guest_status = render_to_string("events/_guest_status.html", {"event": event, "guest": guest}, context_instance=RequestContext(request))
    return HttpResponse(json.dumps({"message_html": message_html, "guest_status": guest_status}), mimetype="text/json")

@login_required
@user_is_event_manager
def hosts(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    form = HostForm(event=event, data=(request.POST or None))
    if form.is_valid():
        form.save()
        return redirect(event)
    template = "events/_hosts.html" if request.is_ajax() else "events/hosts.html"
    return render_to_response(template, locals(), context_instance=RequestContext(request))

@require_POST
@user_is_guest_or_has_token
def rsvp(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    guest = event.current_guest(request=request, token=request.POST.get("token", None))
    rsvp_form = RsvpForm(instance=guest, data=request.POST)
    if rsvp_form.is_valid():
        guest = rsvp_form.store(request)
        if guest.contributor.needs_more_info():
            return redirect("event-rsvp-confirm", event_id=event.id)
        else:
            rsvp_form.save()

            from groups.views import group_join
            for group_id in request.POST.getlist("join_group"):
                group_join(request, group_id)

            return redirect(event)
    return render_to_response("events/show.html", locals(), context_instance=RequestContext(request))

@user_is_guest
def rsvp_confirm(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    guest = event.current_guest(request)
    form = RsvpConfirmForm(instance=guest, data=(request.POST or None))
    if form.is_valid():
        guest = form.save(request)
        if guest.contributor.user:
            return redirect(event)
        return redirect("event-rsvp-account", event_id=event.id)
    return render_to_response("events/rsvp_confirm.html", locals(), context_instance=RequestContext(request))

@user_is_guest
def rsvp_account(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    guest = event.current_guest(request)
    form = RsvpAccountForm(instance=guest, data=(request.POST or None))
    if form.is_valid():
        guest = form.save(request)
        user = auth.authenticate(username=guest.contributor.email, password=form.cleaned_data["password1"])
        logged_in.send(sender=None, request=request, user=user, is_new_user=True)
        auth.login(request, user)
        return redirect(event)
    return render_to_response("events/rsvp_account.html", locals(), context_instance=RequestContext(request))

def rsvp_cancel(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.delete_guest_in_session(request)
    return redirect(event)

def rsvp_statuses(request):
    return HttpResponse(json.dumps(dict(Guest.RSVP_STATUSES)), mimetype="text/json")

@login_required
@user_is_event_manager
def print_sheet(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    attendees = event.attendees()
    attendee_count = len(attendees)

    # Fill every page with blank rows adding rows beyond the initial value of blank_rows if necessary
    blank_rows      = 10
    first_page_rows = 20
    page_rows       = 23
    if attendee_count + blank_rows <= first_page_rows:
        blank_rows = first_page_rows - attendee_count
    else:
        rows_after_first_page = attendee_count + blank_rows - first_page_rows
        if rows_after_first_page <= page_rows:
            blank_rows += page_rows - rows_after_first_page
        else:
            blank_rows += page_rows - (rows_after_first_page % page_rows)

    blank_rows = range(blank_rows)
    return render_to_pdf("events/sign_in_sheet.html", "%s_Sign_In.pdf" % event, {
        "event": event,
        "attendees": attendees,
        "blank_rows": blank_rows
    })

@login_required
@user_is_event_manager
def spreadsheet(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    response = HttpResponse(mimetype="text/csv")
    response["Content-Disposition"] = \
        "attachment; filename=%s_Guest_List.csv" % event

    writer = csv.writer(response)
    writer.writerow(["Name", "Email", "Phone", "Location", "Status"])

    for g in Guest.objects.filter(event=event):        
        writer.writerow([g.contributor.name,
                         g.contributor.email,
                         g.contributor.phone, 
                         g.contributor.geom.formatted_address if g.contributor.geom else '',
                         g.status()])

    return response

@login_required
@user_is_event_manager
def message(request, event_id, type):
    event = get_object_or_404(Event, id=event_id)
    form = MessageForm(user=request.user, event=event, type=type, data=(request.POST or None),
        initial={"guests": request.GET.get("guests", "").split(",")})
    if form.is_valid():
        form.save()
        messages.success(request, "Your message has been sent.")
        return redirect(event)
    template = "events/message.html"
    return render_to_response(template, locals(), context_instance=RequestContext(request))

@login_required
@csrf_protect
def event_contact_admins(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    from discussions.models import Discussion as GenericDiscussion
    from groups.forms import DiscussionCreateForm

    if request.method == "POST":
        disc_form = DiscussionCreateForm(request.POST)
        if disc_form.is_valid():
            disc = GenericDiscussion.objects.create(
                subject="Message to event organizers: %s" % disc_form.cleaned_data['subject'],
                body=disc_form.cleaned_data['body'],
                parent_id=None,
                user=request.user, 
                content_object=event,
                is_public=False,
                disallow_replies=True,
                reply_count=0,
                contact_admin=True,
            )
            messages.success(request, "Your message has been sent to the event organizers")
            return redirect(event)
    else:
        disc_form = DiscussionCreateForm()
    return render_to_response("events/event_disc_contact_admins.html",
                              locals(), 
                              context_instance=RequestContext(request)) 
