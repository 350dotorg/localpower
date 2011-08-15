from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.http import require_POST

from utils import forbidden

from models import Challenge, Support
from forms import ChallengeForm, PetitionForm

def _edit(request, challenge):
    nav_selected = "challenges"
    form = ChallengeForm(request.user, instance=challenge, data=(request.POST or None))
    if form.is_valid():
        form.save()
        return redirect(challenge)
    type_label = challenge.id and 'Edit' or 'Create'
    return render_to_response('challenges/edit.html', locals(), context_instance=RequestContext(request))

def list(request):
    nav_selected = "challenges"
    challenges = Challenge.objects.all_challenges(request.user)
    return render_to_response('challenges/list.html', locals(), context_instance=RequestContext(request))

@login_required
def create(request):
    challenge = Challenge(creator=request.user)
    return _edit(request, challenge)

def detail(request, challenge_id):
    nav_selected = "challenges"
    challenge = get_object_or_404(Challenge.objects.select_related(), id=challenge_id)
    if request.user.is_authenticated():
        initial = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        if request.user.get_profile().location:
            initial['zipcode'] = request.user.get_profile().location.zipcode
    else:
        initial = {}
    form = PetitionForm(challenge=challenge, data=(request.POST or None), initial=initial)
    if form.is_valid():
        form.save()
        messages.success(request, _('Thanks for your support'))
        return redirect('challenges_detail', challenge_id=challenge_id)
    supporters = Support.objects.filter(challenge=challenge).order_by("-pledged_at")[:12]
    return render_to_response('challenges/detail.html', locals(), context_instance=RequestContext(request))

@login_required
def edit(request, challenge_id=None):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    if request.user != challenge.creator:
        return forbidden(request, _('You do not have permissions to edit %(challenge)s'
                                    ) % {'challenge': challenge})
    return _edit(request, challenge)
