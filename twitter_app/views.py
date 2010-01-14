import oauth, json

from django.http import *
from django.shortcuts import render_to_response, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.template import RequestContext
from django.contrib import messages
from twitter_app.utils import *
from twitter_app.forms import StatusForm

@login_required
def unauth(request):
    #TODO: is there an easy way to unauthorize on twitters end as well?
    request.user.get_profile().twitter_access_token = None
    request.user.get_profile().save()
    messages.success(request, "We have unlinked your account with twitter.")
    return redirect('profile_edit', request.user.id)

@login_required
def auth(request):
    "/auth/"
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
            return redirect('profile_edit', request.user.id)
        else:
            messages.error(request, "Your tokens to not match.")
    else:
        messages.error(request, "You are missing a token.")
    return redirect('profile_edit', request.user.id)

@login_required
@require_POST
def post_status(request):
    """
    use this to post a status update to your twitter account
    """
    form = StatusForm(request.POST)
    if form.is_valid():
        profile = request.user.get_profile()
        if form.save(profile):
            messages.success(request, "Your tweet has been posted.")
        else:
            profile.twitter_access_token = None
            profile.save()
            messages.error(request, "There was a problem posting your tweet, please relink your account.")
    return redirect('index')