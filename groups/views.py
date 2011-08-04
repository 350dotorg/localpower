import base64
from datetime import datetime
import email
from smtplib import SMTPException

from brabeion import badges as badge_cache

from django.core.paginator import Paginator, InvalidPage, EmptyPage
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import send_mail, EmailMessage
from django.http import Http404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import Context, loader, RequestContext
from django.utils import simplejson as json
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST

from records.models import Record
from invite.models import Invitation
from invite.forms import InviteForm
from utils import hash_val, forbidden
from messaging.models import Stream
from events.models import Event, GroupAssociationRequest

from models import Group, GroupUsers, MembershipRequests, Discussion
from forms import GroupForm, MembershipForm, DiscussionSettingsForm, DiscussionCreateForm, DiscussionApproveForm, DiscussionRemoveForm

@login_required
@csrf_protect
def group_create(request):
    """
    create a form a user can use to create a custom group, on POST save this group to the database
    and automatically add the creator to the said group as a manager.
    """
    nav_selected = "communities"
    if request.method == "POST":
        form = GroupForm(request.POST, request.FILES)
        if form.is_valid():
            group = form.save()
            GroupUsers.objects.create(group=group, user=request.user, is_manager=True)
            Stream.objects.get(slug="community-create").enqueue(content_object=group, start=group.created)
            Record.objects.create_record(request.user, 'group_create', group)
            badge_cache.possibly_award_badge('created_a_community', user=request.user)
            messages.success(request, "%s has been created." % group)
            return redirect("group_detail", group_slug=group.slug)
    else:
        form = GroupForm()
    return render_to_response("groups/group_create.html", {
        "form": form,
        "site": Site.objects.get_current(),
        "nav_selected": nav_selected
    }, context_instance=RequestContext(request))

@login_required
def group_leave(request, group_id):
    group = get_object_or_404(Group, id=group_id, is_geo_group=False)
    if request.user.id in group.users.all().values_list("id", flat=True):
        if group.has_other_managers(request.user):
            GroupUsers.objects.filter(group=group, user=request.user).delete()
            messages.success(request, "You have been removed from community %s" % group)
        else:
            messages.error(request, "You cannot leave the community, until you've assigned someone else to be manager.", extra_tags="sticky")
    else:
        messages.error(request, "You cannot leave a community your not a member of")
    return redirect("group_detail", group_slug=group.slug)

@login_required
def group_join(request, group_id):
    group = get_object_or_404(Group, id=group_id, is_geo_group=False)
    if GroupUsers.objects.filter(group=group, user=request.user).exists():
        messages.error(request, "You are already a member")
        return redirect("group_detail", group_slug=group.slug)
    if MembershipRequests.objects.filter(group=group, user=request.user).exists():
        messages.error(request, "Your membership is currently pending")
        return redirect("group_detail", group_slug=group.slug)
    if group.is_public():
        GroupUsers.objects.create(group=group, user=request.user, is_manager=False)
        messages.success(request, "You have successfully joined community %s" % group, extra_tags="sticky")
    else:
        membership_request = MembershipRequests.objects.create(group=group, user=request.user)
        Stream.objects.get(slug="community-join-request").enqueue(content_object=membership_request, start=datetime.now())
        messages.success(request, "You have made a request to join %s, a manager should grant or deny your membership shortly." % group, extra_tags="sticky")
    return redirect("group_detail", group_slug=group.slug)

@login_required
def group_membership_request(request, group_id, user_id, action):
    group = get_object_or_404(Group, id=group_id, is_geo_group=False)
    user = get_object_or_404(User, id=user_id)
    if not group.is_user_manager(request.user):
        return forbidden(request)
    try:
        membership_request = MembershipRequests.objects.get(group=group, user=user)
    except MembershipRequests.DoesNotExist:
        membership_request = None
    if membership_request:
        if action == "approve":
            GroupUsers.objects.create(group=group, user=user, is_manager=False)
            Stream.objects.get(slug="community-membership-approved").enqueue(content_object=membership_request,
                start=datetime.now())
            membership_request.delete()
            messages.success(request, "%s has been added to the community" % user.get_full_name())
        elif action == "deny":
            Stream.objects.get(slug="community-membership-denied").enqueue(content_object=membership_request,
                start=datetime.now())
            membership_request.delete()
            messages.success(request, "%s has been denied access to the community" % user.get_full_name())
    elif GroupUsers.objects.filter(group=group, user=user).exists():
        messages.info(request, "%s has already been added to this community" % user.get_full_name())
    else:
        messages.info(request, "%s has already been denied access to this community" % user.get_full_name())
    return redirect("group_detail", group_slug=group.slug)

@login_required
def group_event_request(request, group_id, event_id, action):
    group = get_object_or_404(Group, id=group_id, is_geo_group=False)
    event = get_object_or_404(Event, id=event_id)
    if not group.is_user_manager(request.user):
        return forbidden(request)
    try:
        event_request = GroupAssociationRequest.objects.get(event=event, group=group)
    except GroupAssociationRequest.DoesNotExist:
        event_request = None
    if event_request:
        if action == "approve":
            event.groups.add(group)
            event_request.approved = True
            event_request.save()
            messages.success(request, "Your community has been linked with %s" % event)
        elif action == "deny":
            event_request.delete()
            messages.success(request, "Your community will not be linked with %s" % event)
    elif group.event_set.filter(event=event).exists():
        messages.info(request, "%s has already been linked with your community" % event)
    else:
        messages.info(request, "%s has not been linked with your community" % event)
    return redirect("group_detail", group_slug=group.slug)

def group_detail(request, group_slug):
    """
    display all of the information about a particular group
    """
    group = get_object_or_404(Group, slug=group_slug, is_geo_group=False)
    return _group_detail(request, group)

def geo_group(request, state, county_slug=None, place_slug=None):
    slug = state.lower()
    if county_slug:
        slug += "-%s" % county_slug
    if place_slug:
        slug += "-%s" % place_slug
    group = get_object_or_404(Group, slug=slug)
    return _group_detail(request, group)

def group_list(request):
    """
    display a listing of the groups
    """
    nav_selected = "communities"
    groups = Group.objects.groups_with_memberships(request.user)
    if request.user.is_authenticated():
        my_groups = Group.objects.filter(users=request.user, is_geo_group=False)
    return render_to_response("groups/group_list.html", locals(), context_instance=RequestContext(request))

@login_required
@csrf_protect
def group_edit(request, group_slug):
    nav_selected = "communities"
    group = get_object_or_404(Group, slug=group_slug, is_geo_group=False)
    if not group.is_user_manager(request.user):
        return forbidden(request)
    if request.method == "POST":
        if "change_group" in request.POST:
            group_form = GroupForm(request.POST, request.FILES, instance=group)
            if group_form.is_valid():
                group = group_form.save()
                messages.success(request, "%s has been updated." % group)
                return redirect("group_edit", group_slug=group.slug)
            else:
                membership_form = MembershipForm(group=group)
                discussions_form = DiscussionSettingsForm(instance=group)
        if "discussion_settings" in request.POST:
            discussions_form = DiscussionSettingsForm(request.POST, instance=group)
            if discussions_form.is_valid():
                group = discussions_form.save()
                messages.success(request, "%s has been updated." % group)
                return redirect("group_edit", group_slug=group.slug)
            else:
                membership_form = MembershipForm(group=group)
                group_form = GroupForm(instance=group)
        elif "delete_group" in request.POST:
            group.delete()
            messages.success(request, "%s has been deleted." % group)
            return redirect("group_list")
        elif "change_membership" in request.POST:
            membership_form = MembershipForm(group=group, data=request.POST)
            if membership_form.is_valid():
                membership_form.save()
                if group.is_user_manager(request.user):
                    messages.success(request, "%s's memberships have been updated." % group)
                    return render_to_response("groups/group_edit.html", locals(), context_instance=RequestContext(request))
                else:
                    messages.success(request, "You no longer have permissions to edit %s" % group)
                    return redirect("group_detail", group_slug=group.slug)
            else:
                group_form = GroupForm(instance=group)
                discussions_form = DiscussionSettingsForm(instance=group)
        else:
            messages.error(request, "No action specified.")
    else:
        group_form = GroupForm(instance=group)
        membership_form = MembershipForm(group=group)
        discussions_form = DiscussionSettingsForm(instance=group)
    site = Site.objects.get_current()
    requesters = group.requesters_to_grant_or_deny(request.user)
    return render_to_response("groups/group_edit.html", locals(), context_instance=RequestContext(request))

@csrf_exempt
def receive_mail(request):
    msg = email.message_from_string(request.raw_post_body)
    addr = msg.get("To")
    if not addr:
        return forbidden(request)

    try:
        values, tamper_check = base64.b64decode(addr).split("\0")
    except TypeError:
        return forbidden(request)

    if hash_val(values) != tamper_check:
        return forbidden(request)
    try:
        values = json.loads(values)
    except ValueError:
        return forbidden(request)

    # The Discussion Form wants this hashed value as a tamper-proof check
    values['parent_id_sig'] = hash_val(values['parent_id'])

    try:
        user = User.objects.get(email=values.pop("user"))
        group = Group.objects.get(slug=values.pop("group"))
        parent_disc = Discussion.objects.get(group=group, id=parent_id)
    except (User.DoesNotExist, Group.DoesNotExist, Discussion.DoesNotExist), e:
        return forbidden(request)

    values['subject'] = "Re: %s" % parent_disc.subject

    best_choice = None
    for part in msg.walk():
        if part.get_content_maintype() == 'multipart':
            continue
        if part.get_content_type() == 'text/plain':
            best_choice = part
            break
        if best_choice is None and part.get_content_type() == 'text/html':
            best_choice = part
    if best_choice is None:
        # No text/plain or text/html message was found in the email
        # so we'll just reject it for now.
        # TODO: figure out a sane approach to email content-type handling
        return forbidden(request)
    # TODO: process text/html message differently
    values['body'] = best_choice.get_payload(decode=True)

    disc_form = DiscussionCreateForm(values)
    if not disc_form.is_valid():
        return forbidden(request)

    new_disc = Discussion.objects.create(
        subject=disc_form.cleaned_data['subject'],
        body=disc_form.cleaned_data['body'],
        parent_id=disc_form.cleaned_data['parent_id'],
        user=request.user,
        group=group,
        is_public=not group.moderate_disc(request.user),
        reply_count=None if disc_form.cleaned_data['parent_id'] else 0
        )
    new_disc.save()
    return_to = (disc_form.cleaned_data['parent_id'] 
                 if disc_form.cleaned_data['parent_id']
                 else disc.id)

    # TODO: would be better to return a unique URL for the newly created object
    # for debugging/logging purposes
    return redirect("group_disc_detail", group_slug=group.slug, disc_id=return_to)

@login_required
@csrf_protect
def group_disc_create(request, group_slug):
    group = Group.objects.get(slug=group_slug)
    if not group.is_poster(request.user):
        return forbidden(request)
    if request.method == "POST":
        disc_form = DiscussionCreateForm(request.POST)
        if disc_form.is_valid():
            group = Group.objects.get(slug=group_slug)
            disc = Discussion.objects.create(
                subject=disc_form.cleaned_data['subject'],
                body=disc_form.cleaned_data['body'], 
                parent_id=disc_form.cleaned_data['parent_id'], 
                user=request.user, 
                group=group,
                is_public=not group.moderate_disc(request.user),
                reply_count=None if disc_form.cleaned_data['parent_id'] else 0
            )
            messages.success(request, "Discussion posted")
            return_to = disc_form.cleaned_data['parent_id'] if disc_form.cleaned_data['parent_id'] else disc.id
            return redirect("group_disc_detail", group_slug=group.slug, disc_id=return_to)
    else:
        disc_form = DiscussionCreateForm()
    return render_to_response("groups/group_disc_create.html", locals(), context_instance=RequestContext(request)) 

def group_disc_detail(request, group_slug, disc_id):
    disc = get_object_or_404(Discussion, id=disc_id, parent=None)
    group = Group.objects.get(slug=group_slug)
    is_poster = group.is_poster(request.user)
    is_manager = group.is_user_manager(request.user)
    approve_form = DiscussionApproveForm()
    remove_form = DiscussionRemoveForm()
    discs = Discussion.objects.filter(parent=disc).order_by("created")
    disc_form = DiscussionCreateForm(initial={'parent_id':disc.id, 'subject':"Re: %s" % disc.subject})
    return render_to_response("groups/group_disc_detail.html", locals(), context_instance=RequestContext(request))

@login_required
@csrf_protect
def group_disc_approve(request, group_slug, disc_id):
    disc = get_object_or_404(Discussion, id=disc_id)
    group = Group.objects.get(slug=group_slug)
    form = DiscussionApproveForm(request.POST, instance=disc)
    if request.method == "POST" and form.is_valid() and group.is_user_manager(request.user):
        form.save()
        messages.success(request, "Discussion approved")

    return_to = disc.parent_id if disc.parent_id else disc.id
    return redirect("group_disc_detail", group_slug=group_slug, disc_id=return_to)

@login_required
@csrf_protect
def group_disc_remove(request, group_slug, disc_id):
    disc = get_object_or_404(Discussion, id=disc_id)
    group = Group.objects.get(slug=group_slug)
    form = DiscussionRemoveForm(request.POST, instance=disc)

    if request.method == "POST" and form.is_valid() and group.is_user_manager(request.user):
        form.save()
        messages.success(request, "Discussion removed")
        if disc.parent_id:
            return redirect("group_disc_detail", group_slug=group_slug, disc_id=disc.parent_id)
        else:
            return redirect("group_disc_list", group_slug=group_slug)

    return redirect("group_disc_detail", group_slug=group_slug, disc_id=disc.id)

def group_disc_list(request, group_slug):
    group = Group.objects.get(slug=group_slug)
    paginator = Paginator(Discussion.objects.filter(parent=None, group=group), 20)
    is_poster = group.is_poster(request.user)
    is_manager = group.is_user_manager(request.user)
    # Make sure page request is an int. If not, deliver first page.
    try:
        page = int(request.GET.get('page', '1'))
    except ValueError:
        page = 1

    # If page request is out of range, deliver last page of results.
    try:
        discs = paginator.page(page)
    except (EmptyPage, InvalidPage):
        discs = paginator.page(paginator.num_pages)

    return render_to_response("groups/group_disc_list.html", locals(), context_instance=RequestContext(request))

def _group_detail(request, group):
    nav_selected = "communities"
    popular_actions = list(group.completed_actions_by_user(5))
    top_members = group.members_ordered_by_points()
    group_records = group.group_records(10)
    is_member = group.is_member(request.user)
    is_manager = group.is_user_manager(request.user)
    is_poster = group.is_poster(request.user)
    membership_pending = group.has_pending_membership(request.user)
    requesters = group.requesters_to_grant_or_deny(request.user)
    event_requests = group.events_waiting_approval(request.user)
    has_other_managers = group.has_other_managers(request.user)
    discs = Discussion.objects.filter(parent=None, group=group).order_by("-created")[:5]
    return render_to_response("groups/group_detail.html", locals(), context_instance=RequestContext(request))
