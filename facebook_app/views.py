import facebook
import hashlib

from django.core.urlresolvers import reverse, NoReverseMatch
from django.conf import settings
from django.contrib import auth, messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect
from django.template import loader, Context

from settings import SITE_NAME
from rah.models import Profile
from rah.signals import logged_in

def login(request):
    facebook_user = facebook.get_user_from_cookie(request.COOKIES,
        settings.FACEBOOK_APPID, settings.FACEBOOK_SECRET)
    next = request.GET.get("next", None)
    if facebook_user:
        access_token = facebook_user["access_token"]
        graph = facebook.GraphAPI(access_token)
        facebook_user = graph.get_object("me")
        email = facebook_user["email"]
        if graph:
            is_new_user = False
            username = hashlib.md5(email).hexdigest()[:30]
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                is_new_user = True
                user = User.objects.create_user(username, email, "")
                user.first_name = facebook_user["first_name"]
                user.last_name = facebook_user["last_name"]
                user.save()
            profile = user.get_profile()
            profile.facebook_access_token = access_token
            if is_new_user:
                profile.facebook_connect_only = True
            profile.save()
            user = auth.authenticate(username=profile.user.email, is_facebook_connect=True)
            logged_in.send(sender=None, request=request, user=user, is_new_user=is_new_user)
            auth.login(request, user)
            next = next or settings.LOGIN_REDIRECT_URL
            try:
                return redirect(next)
            except NoReverseMatch:
                return redirect(settings.LOGIN_REDIRECT_URL)
    messages.error(request, "Facebook login credentials could not be verified, please try again.")
    try:
        return redirect(next or "login")
    except NoReverseMatch:
        return redirect("login")

@login_required
def authorize(request):
    facebook_user = facebook.get_user_from_cookie(request.COOKIES,
        settings.FACEBOOK_APPID, settings.FACEBOOK_SECRET)
    next = request.GET.get("next", "")
    profile_edit_link = reverse('profile_edit', kwargs={'user_id': request.user.id})
    if profile_edit_link in next:
        next = profile_edit_link + "#social_networks_tab"
    if facebook_user:
        profile = request.user.get_profile()
        profile.facebook_access_token = facebook_user["access_token"]
        profile.save()
        messages.success(request, "Your Facebook account is now linked with %s" % SITE_NAME)
        return redirect(next) if next else redirect("profile_edit", user_id=request.user.id)
    messages.error(request, "Facebook authorization credentials could not be verified, please try again.")
    return redirect(next) if next else redirect("profile_edit", user_id=request.user.id)

@login_required
def unauthorize(request):
    profile = request.user.get_profile()
    profile.facebook_access_token = None
    profile.facebook_share = False
    profile.save()
    messages.success(request, "Your Facebook account has been unlinked with %s" % SITE_NAME)
    next = request.GET.get("next", None)
    return redirect(next) if next else redirect(reverse('profile_edit', kwargs={'user_id': request.user.id}) + "#social_networks_tab")

@login_required
def sharing(request, is_enabled):
    profile = request.user.get_profile()
    if profile.facebook_access_token:
        profile.facebook_share = is_enabled
        profile.save()
        if is_enabled:
            messages.success(request, "Your activity stream will now be shared on Facebook")
        else:
            messages.success(request, "Your activity stream will no longer be shared on Facebook")
    else:
        messages.error(request, "You must link your Facebook account first")
    next = request.GET.get("next", "")
    if not next:
        next = reverse('profile_edit', kwargs={'user_id': request.user.id}) + "#social_networks_tab"

    return redirect(next) if next else redirect("profile_edit", user_id=request.user.id)
