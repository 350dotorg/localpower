from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template import RequestContext
from django.shortcuts import render_to_response, redirect, get_object_or_404

from utils import forbidden

from models import Commitment, Contributor, ContributorSurvey
from forms import ContributorForm
from commitments import survey_forms

import pdb


@login_required
def show(request):
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
    return render_to_response('commitments/show.html', locals(), context_instance=RequestContext(request))
    
def card(request, contrib_id=None, form_name=None):
    # Get the contributor object is specified
    if not contrib_id:
        contributor = Contributor()
    else:
        contributor = get_object_or_404(Contributor, pk=contrib_id)
        
        # Make sure the logged in user has access to view the card. User must have entered a survey for this 
        # contributor, or else have the edit_any_contributor permission
        if ContributorSurvey.objects.filter(entered_by=request.user, contributor=contributor).exists() == False \
            and request.user.has_perm("contributor.edit_any_contributor") == False:
            return forbidden(request, "You don't have permission to edit this contributor.")
        
    # If the contributor has a location, get the zipcode
    contrib_loc = contributor.location.zipcode if contributor.location else ""
    
    # Setup a contrib form
    contrib_form = ContributorForm((request.POST or None), instance=contributor, initial={"zipcode": contrib_loc})
    
    # If a survey_form was specified, use that, otherwise use a default
    form_name = request.GET.get("form_name", str(form_name))
    try:
        survey_form = getattr(survey_forms, form_name)(contributor, request.user, (request.POST or None))
    except AttributeError:
        survey_form = survey_forms.EnergyMeetingCommitmentCardVersion2(contributor, request.user, (request.POST or None))
    
    # pdb.set_trace()
    if request.method == 'POST' and contrib_form.is_valid() and survey_form.is_valid():
        contributor = contrib_form.save()
        # pdb.set_trace()
        survey_form.save()
        messages.success(request, "Commitment card for %s saved" % contributor.get_full_name())
        if request.POST.get("submit") == "save_and_add_another":
            return redirect("commitments_card_create")
        else:
            return redirect("commitments_show")
    
    return render_to_response('commitments/card.html', {
        "survey_form": survey_form,
        "contrib_form": contrib_form
    }, context_instance=RequestContext(request))