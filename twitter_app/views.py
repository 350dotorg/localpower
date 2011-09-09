import oauth, json

from django.http import *
from django.core.urlresolvers import reverse
from django.shortcuts import render_to_response, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.template import RequestContext
from django.contrib import messages
from twitter_app.utils import *
from twitter_app.forms import StatusForm

from records.models import Record

@login_required
def unauth(request):
    request.user.get_profile().twitter_access_token = None
    request.user.get_profile().save()
    messages.success(request, "We have unlinked your account with twitter.")
    next = reverse('profile_edit', kwargs={'user_id': request.user.id}) + "#social_networks_tab"
    return redirect(next)

@login_required
def auth(request):
    "/auth/"
    request.session["twitter_next"] = request.GET.get("next", reverse("profile_edit", args=[request.user.id]))
    token = get_unauthorised_request_token()
    auth_url = get_authorisation_url(token)
    request.session['unauthed_token'] = token.to_string()
    return HttpResponseRedirect(auth_url)

@login_required
def return_(request):
    "/return/"
    unauthed_token = request.session.get('unauthed_token', None)
    if unauthed_token:
        token = oauth.OAuthToken.from_string(unauthed_token)
        if token.key == request.GET.get('oauth_token', 'no-token'):
            access_token = exchange_request_token_for_access_token(token)
            profile = request.user.get_profile()
            profile.twitter_access_token = access_token.to_string()
            profile.save()
            messages.success(request, "Your account is now linked with twitter.")
            return redirect(request.session.pop("twitter_next") + "#social_networks_tab")
        else:
            messages.error(request, "Your tokens to not match.")
    else:
        messages.error(request, "You are missing a token.")
    return redirect(request.session.pop("twitter_next") + "#social_networks_tab")

@login_required
@require_POST
def post_status(request):
    """
    use this to post a status update to your twitter account
    """
    form = StatusForm(request.POST)
    if form.is_valid():
        profile = request.user.get_profile()
        resp = form.save(profile)
        if resp == "success":
            Record.objects.create_record(request.user, 'mag_tweet')
            messages.success(request, "Your tweet has been posted.")
        else:
            messages.error(request, "There was a problem posting your tweet. Twitter says, '%s'" % resp)
    return redirect("index")


@login_required
def sharing(request, is_enabled):
    profile = request.user.get_profile()
    if profile.twitter_access_token:
        profile.twitter_share = is_enabled
        profile.save()
        if is_enabled:
            messages.success(request, "Your activity stream will now be shared on Twitter")
        else:
            messages.success(request, "Your activity stream will no longer be shared on Twitter")
    else:
        messages.error(request, "You must link your Twitter account first")
    next = request.GET.get("next", "")
    if not next:
        next = reverse('profile_edit', kwargs={'user_id': request.user.id}) + "#social_networks_tab"

    return redirect(next) if next else redirect("profile_edit", user_id=request.user.id)
