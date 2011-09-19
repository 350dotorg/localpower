import json

from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext, loader
from django.http import HttpResponse
from django.views.decorators.http import require_POST

from utils import forbidden
from models import Commitment, Contributor, ContributorSurvey, Survey
from forms import ContributorForm
from commitments import survey_forms

def show(request):
    if request.user.is_authenticated():
        commitments = Commitment.objects.distinct().select_related('action__id', 'action__name',
            'contributor__first_name', 'contributor__last_name', 'contributor__email',
            'contributor__user__first_name', 'contributor__user__last_name','contirbutor__user__email').filter(
            contributor__contributorsurvey__entered_by=request.user, action__isnull=False).order_by(
            'contributor__first_name', 'contributor__last_name')
        actions = {}
        for c in commitments:
            if c.action in actions:
                actions[c.action].append(c)
            else:
                actions[c.action] = [c]
        total_commitments = 0
        total_completes = 0
        for a, c in actions.items():
            commitments = len([x for x in c if x.answer == 'C'])
            total_commitments += commitments
            completes = len([x for x in c if x.answer == 'D'])
            total_completes += completes
            actions[a] = (c, commitments, completes)

        pledge_card_count = ContributorSurvey.objects.filter(entered_by=request.user).count()
    return render_to_response('commitments/show.html', locals(), context_instance=RequestContext(request))

def card(request, contrib_id=None, form_name=None):
    # Get the contributor object if specified
    if not contrib_id:
        contributor = Contributor()
    else:
        contributor = get_object_or_404(Contributor, pk=contrib_id)

        # Make sure the logged in user has access to view the card. User must have entered a survey for this 
        # contributor, or else have the edit_any_contributor permission
        if ContributorSurvey.objects.filter(entered_by=request.user, contributor=contributor).exists() == False \
            and request.user.has_perm("contributor.edit_any_contributor") == False:
            return forbidden(request, "You don't have permission to edit this contributor.")

    contrib_form = ContributorForm((request.POST or None), instance=contributor)

    # If a survey_form was specified, use that, otherwise use a default
    form_name = request.GET.get("form_name", str(form_name))
    try:
        survey_form = getattr(survey_forms, form_name)(contributor, request.user, (request.POST or None))
    except AttributeError:
        survey_form = survey_forms.PledgeCard(contributor, request.user, (request.POST or None))

    if request.method == 'POST' and contrib_form.is_valid() and survey_form.is_valid():

        # If the contrib form finds that the email already exists, it'll return the matched contributor
        contributor = contrib_form.save()

        # Make sure the survey form has the right contributor in case one was matched on email
        survey_form.contributor = contributor
        survey_form.save()

        messages.success(request, "Commitment card for %s %s saved" % (contributor.first_name, contributor.last_name,))

    if request.is_ajax():
        if request.method == 'POST':
            message_html = loader.render_to_string('_messages.html', {}, RequestContext(request))
            return HttpResponse(message_html)

        template = 'commitments/_card.html'
    else:
        if request.method == 'POST':
            if request.POST.get("submit") == "save_and_add_another":
                return redirect("commitments_card_create")
            else:
                return redirect("commitments_show")
        template = 'commitments/card.html'

    # Get the Surveys for the survey select widget
    survey_types = Survey.objects.filter(is_active=True)

    return render_to_response(template, {
        "survey_form": survey_form,
        "contrib_form": contrib_form,
        "survey_types": survey_types,
        "current_form_name": survey_form.__class__.__name__
    }, context_instance=RequestContext(request))

@require_POST
# when available add an ajax required decorator
def take_pledge(request):
    form = ContributorForm(data=request.POST)
    valid = form.is_valid()
    if valid:
        contributor = form.save()
        survey_forms.PledgeCard(contributor, None, data=request.POST).save()
        messages.success(request, "Thanks for taking the pledge!")
    pledge_card = loader.render_to_string("commitments/_pledge_card_form.html", {"pledge_card_form": form}, RequestContext(request))
    message = loader.render_to_string("_messages.html", {}, RequestContext(request))
    return HttpResponse(json.dumps({"errors": not valid, "msg": message, "payload": pledge_card}), mimetype="text/json")
