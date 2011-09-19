import datetime
import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext, loader
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect

from tagging.models import Tag
from records.models import Record
from records.signals import record_created
from rah.decorators import login_required_save_POST, login_required_except_GET_save_POST

from groups.models import Group
from settings import GA_TRACK_PAGEVIEW
from models import (Action, UserActionProgress, GroupActionProgress,
                    ActionForm, ActionFormData)
from forms import ActionCommitForm, GroupActionCommitForm, ActionGroupLinkForm

def action_show(request, tag_slug=None, is_group_project=False):
    """Show all actions by Category"""
    nav_selected = "group_actions" if is_group_project else "solo_actions"

    if request.user.is_authenticated():
        if is_group_project:
            actions = Action.objects.filter(is_group_project=is_group_project)            
        else:
            actions = Action.objects.actions_by_status(request.user)
    else:
        actions = Action.objects.filter(is_group_project=is_group_project)

    return render_to_response("actions/action_show.html", {
        'actions': actions,
        'nav_selected': nav_selected
    }, context_instance=RequestContext(request))

@login_required_except_GET_save_POST
@csrf_protect
def action_detail(request, action_slug):
    """Detail page for an action"""
    action = get_object_or_404(Action, slug=action_slug)
    nav_selected = "group_actions" if action.is_group_project else "solo_actions"
    default_vars = _default_action_vars(action, request.user)
    default_vars.update(_build_action_form_vars(action, request.user))

    group_link_forms = []
    action_commit_form = None
    if action.is_group_project and not request.user.is_anonymous():
        for group in Group.objects.groups_with_memberships(request.user):
            form = GroupActionCommitForm(user=request.user, action=action,
                                         group=group)
            try:
                progress = GroupActionProgress.objects.get(
                    action=action, 
                    group=group)
                days_till_commitment = 0
                if progress.date_committed:
                    days_till_commitment = (progress.date_committed -
                                            datetime.date.today())
                    days_till_commitment = (days_till_commitment.days
                                            if days_till_commitment.days > 0
                                            else 0)
                form.progress = progress
                form.days_till_commitment = days_till_commitment

            except GroupActionProgress.DoesNotExist:
                form.progress = None
            group_link_forms.append(form)
    else:
        action_commit_form = ActionCommitForm(user=request.user, action=action)

    if request.method == "POST":
        group_link_form = ActionGroupLinkForm(request.user, instance=action, data=request.POST)
        if group_link_form.is_valid():
            action = group_link_form.save()
            messages.success(request, _("Thanks for taking on this project with your group."))
            return redirect("action_detail", action_slug=action.slug)

    default_vars.update(locals())
    return render_to_response("actions/action_detail.html", default_vars, RequestContext(request))

@login_required_save_POST
@csrf_protect
def action_complete(request, action_slug):
    """invoked when a user marks an action as completed"""
    action = get_object_or_404(Action, slug=action_slug)
    if request.method == "GET":
        return redirect("action_detail", action_slug=action.slug)
    if action.is_group_project:
        action_commit_form = GroupActionCommitForm(user=request.user, 
                                                   action=action,
                                                   mark_completed=True,
                                                   data=request.POST)
        if action_commit_form.is_valid():
            uap, record = action_commit_form.save()
        else:
            return redirect("action_detail", action_slug=action.slug)
    else:
        uap, record = action.complete_for_user(request.user)

    if record:
        record_created.send(sender=None, request=request, record=record)
    messages.success(request, _("Nice work! We've updated your profile, "
                                "so all your friends can see your progress "
                                "(<a href='#' class='undo_trigger'>Undo</a>)"))
    messages.add_message(request, GA_TRACK_PAGEVIEW, '/actions/complete')
    messages.add_message(request, GA_TRACK_PAGEVIEW, '/actions/complete/%s' % action_slug)
    return redirect("action_detail", action_slug=action.slug)

@login_required
@csrf_protect
def action_undo(request, action_slug):
    action = get_object_or_404(Action, slug=action_slug)
    if request.method == "GET":
        return redirect("action_detail", action_slug=action.slug)
    if action.undo_for_user(request.user):
        messages.success(request, _("No worries. We've updated the record. "
                                    "Let us know when you're finished with "
                                    "this action."))
        messages.add_message(request, GA_TRACK_PAGEVIEW, '/actions/undo')
        messages.add_message(request, GA_TRACK_PAGEVIEW, '/actions/undo/%s' % action_slug)
    return redirect("action_detail", action_slug=action.slug)

@login_required_save_POST
@csrf_protect
def action_commit(request, action_slug):
    action = get_object_or_404(Action, slug=action_slug)
    if request.method == "GET":
        return redirect("action_detail", action_slug=action.slug)
    if action.is_group_project:
        action_commit_form = GroupActionCommitForm(user=request.user, action=action, data=request.POST)
    else:
        action_commit_form = ActionCommitForm(user=request.user, action=action, data=request.POST)
    # TODO: There is weirdness here if you have already completed the action and try to commit again. 
    # This can happen when you are logged out, commit to an action you've already completes, are asked to log in, and are directed back to the action detail page.
    if action_commit_form.is_valid():
        uap, record = action_commit_form.save()
        if record:
            record_created.send(sender=None, request=request, record=record)
        messages.success(request, _("Thanks for making a commitment."))
        messages.add_message(request, GA_TRACK_PAGEVIEW, '/actions/commit')
        messages.add_message(request, GA_TRACK_PAGEVIEW, '/actions/commit/%s' % action_slug)
        return redirect("action_detail", action_slug=action.slug)
    default_vars = _default_action_vars(action, request.user)
    default_vars.update(locals())
    return render_to_response("actions/action_detail.html", default_vars, RequestContext(request))

@login_required
@csrf_protect
def action_cancel(request, action_slug):
    action = get_object_or_404(Action, slug=action_slug)
    if request.method == "POST":
        if action.cancel_for_user(request.user):
            messages.success(request, _("We cancelled your commitment. If "
                                        "you're having trouble completing an "
                                        "action, try asking a question. "
                                        "Other members will be happy to help!"))
            messages.add_message(request, GA_TRACK_PAGEVIEW, '/actions/cancel')
            messages.add_message(request, GA_TRACK_PAGEVIEW, '/actions/cancel/%s' % action_slug)
        return redirect("action_detail", action_slug=action.slug)
    return render_to_response("actions/action_cancel.html", locals(), RequestContext(request))

@login_required_save_POST
@csrf_protect
def save_action_form(request, action_slug, form_name):
    import action_forms

    action = get_object_or_404(Action, slug=action_slug)
    action_form = get_object_or_404(ActionForm, action=action, form_name=form_name)
    if request.method == "GET":
        return redirect("action_detail", action_slug=action.slug)
    afd, c = ActionFormData.objects.get_or_create(action_form=action_form, user=request.user)
    data = request.POST.copy()
    if "csrfmiddlewaretoken" in data:
        del data["csrfmiddlewaretoken"]
    if afd.data:
        existing = json.loads(afd.data)
        existing.update(data.items())
        data = existing
        afd.data = json.dumps(data)
    else:
        afd.data = json.dumps(data)
    afd.save()
    if request.is_ajax():
        form = getattr(action_forms, form_name)(data=data)
        ajax_data_func = getattr(form, "ajax_data", None)
        return HttpResponse(json.dumps(ajax_data_func() if ajax_data_func else None))
    return redirect("action_detail", action_slug=action.slug)

def _default_action_vars(action, user):
    users_completed = User.objects.filter(useractionprogress__action=action,
        useractionprogress__is_completed=1).order_by("-useractionprogress__updated")[:5]
    noshow_users_completed = action.users_completed - users_completed.count()
    users_committed = User.objects.filter(useractionprogress__action=action,
        useractionprogress__date_committed__isnull=False,
        useractionprogress__is_completed=0).order_by("-useractionprogress__updated")
    total_users_committed = users_committed.count()
    users_committed = users_committed[:5]
    noshow_users_committed = total_users_committed - users_committed.count()
    progress = None
    if user.is_authenticated():
        try:
            progress = UserActionProgress.objects.get(action=action, user=user)
            if progress.date_committed:
                days_till_commitment = progress.date_committed - datetime.date.today()
                days_till_commitment = days_till_commitment.days if days_till_commitment.days > 0 else 0
        except UserActionProgress.DoesNotExist: pass
    default_vars = dict(locals())
    del default_vars["action"]
    del default_vars["user"]
    return default_vars

def _build_action_form_vars(action, user):
    import action_forms

    forms = {}
    for form in action.action_forms_with_data(user):
        if hasattr(action_forms, form.form_name):
            data = json.loads(form.data) if form.data else None
            forms[form.var_name] = getattr(action_forms, form.form_name)(data=data)
    return forms
