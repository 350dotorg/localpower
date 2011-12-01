from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.views.decorators.http import require_POST
from utils import forbidden

from models import Challenge, Support
from forms import ChallengeForm, PetitionForm

def _edit(request, challenge):
    nav_selected = "challenges"
    title = challenge.title or ''
    title = title.split(":")
    if len(title) == 1:
        target = ''
        demand = title[0].strip()
    else:
        target = title[0].strip()
        demand = title[1].strip()

    form = ChallengeForm(request.user, instance=challenge, 
                         data=(request.POST or None),
                         initial={'groups': request.GET.getlist("groups"),
                                  "target": target,
                                  "demand": demand})
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
        profile = request.user.get_profile()
        if profile.geom:
            initial['geom'] = profile.geom.formatted_address
    else:
        initial = {}
    form = PetitionForm(challenge=challenge, data=(request.POST or None), initial=initial)
    if form.is_valid():
        form.save()
        messages.success(request, _('Thanks for your support'))

        from groups.views import group_join
        for group_id in request.POST.getlist("join_group"):
            group_join(request, group_id)

        return redirect('challenges_detail', challenge_id=challenge_id)
    supporters = Support.objects.filter(challenge=challenge).order_by("-pledged_at")

    has_manager_privileges = challenge.has_manager_privileges(request.user)
    
    groups_to_join = challenge.groups.all()
    groups_to_join = groups_to_join.filter(is_external_link_only=False)
    if request.user.is_authenticated():
        groups_to_join = groups_to_join.exclude(groupusers__user=request.user)

    return render_to_response('challenges/detail.html', locals(), context_instance=RequestContext(request))

@login_required
def edit(request, challenge_id=None):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    if request.user != challenge.creator:
        return forbidden(request, _('You do not have permissions to edit %(challenge)s'
                                    ) % {'challenge': challenge})
    return _edit(request, challenge)

@login_required
def pdf_download(request, challenge_id=None):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    if request.user != challenge.creator:
        return forbidden(request, _('You do not have permissions to download %(challenge)s'
                                    ) % {'challenge': challenge})
    supporters = Support.objects.filter(challenge=challenge).order_by("-pledged_at")
    if not len(supporters):
        messages.error(request, _("No one has signed this petition yet."))
        return redirect("challenges_detail", challenge_id=challenge_id)

    from challenges.pdf import _download
    return _download(request, challenge, supporters)

@login_required
@csrf_protect
def challenges_disc_create(request, challenge_id):
    nav_selected = "challenges"
    challenge = get_object_or_404(Challenge, id=challenge_id)

    if not challenge.has_manager_privileges(request.user):
        return forbidden(request, _('You do not have permissions'))
        
    from groups.forms import DiscussionCreateForm
    from discussions.models import Discussion

    if request.method == "POST":
        disc_form = DiscussionCreateForm(request.POST)
        if disc_form.is_valid():
            disc = Discussion.objects.create(
                subject=disc_form.cleaned_data['subject'],
                body=disc_form.cleaned_data['body'],
                parent_id=None,
                user=request.user,
                content_object=challenge,
                reply_count=0,
                is_public=False,
                disallow_replies=True)
            messages.success(request, "Your message has been sent to the campaign's supporters.")
            return redirect(challenge)
    else:
        disc_form = DiscussionCreateForm()

    return render_to_response("challenges/challenge_disc_create.html", 
                              locals(), 
                              context_instance=RequestContext(request)) 

@login_required
@csrf_protect
def challenge_contact_admins(request, challenge_id):
    challenge = get_object_or_404(Challenge, id=challenge_id)
    from discussions.models import Discussion as GenericDiscussion
    from groups.forms import DiscussionCreateForm

    if request.method == "POST":
        disc_form = DiscussionCreateForm(request.POST)
        if disc_form.is_valid():
            disc = GenericDiscussion.objects.create(
                subject="Message to campaign organizers: %s" % disc_form.cleaned_data['subject'],
                body=disc_form.cleaned_data['body'],
                parent_id=None,
                user=request.user, 
                content_object=challenge,
                is_public=False,
                disallow_replies=True,
                reply_count=0,
                contact_admin=True,
            )
            messages.success(request, "Your message has been sent to the campaign organizers")
            return redirect(challenge)
    else:
        disc_form = DiscussionCreateForm()
    return render_to_response("challenges/challenge_disc_contact_admins.html",
                              locals(), 
                              context_instance=RequestContext(request)) 
