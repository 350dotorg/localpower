from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from actionkit_usersync.utils import get_client
from rah.models import Profile

class null_location(object):
    def __getattr__(self, *args, **kw):
        return ''

def actionkit_push(user, profile):
    location = profile.location or null_location()
    # EGJ TODO: what if profile.location is None?
    # i think the localpower system allows that
    # currently just setting empty strings (per line above)

    actionkit = get_client()
    ak_user = actionkit.User.save_or_create(dict(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            zip=location.zipcode,
            region=location.county,
            state=location.st,
            state_name=location.state,
            city=location.name
            ))

    history = actionkit.User.subscription_history({'id': ak_user['id']})
    ever_been_subscribed = False
    for entry in history:
        if entry.get("page_name") == settings.ACTIONKIT_PAGE_NAME:
            ever_been_subscribed = True
            break
    if not ever_been_subscribed:
        # EGJ TODO: would prefer not to have city/country required;
        # we don't necessarily have that info yet
        result = actionkit.act(dict(
                page=settings.ACTIONKIT_PAGE_NAME,
                email=user.email,
                city=location.name,
                country="United states",
                ))

    return ak_user

def user_post_save(sender, instance, created, **kwargs):
    user = instance
    profile = user.get_profile()
    ak_user = actionkit_push(user, profile)
models.signals.post_save.connect(user_post_save, sender=User)

def profile_post_save(sender, instance, created, **kwargs):
    profile = instance
    user = profile.user
    ak_user = actionkit_push(user, profile)
models.signals.post_save.connect(profile_post_save, sender=Profile)

# EGJ TODO: test profile post-save signal

# Verify that the ActionKit API settings are correct 
# and successfully connect to the server
actionkit = get_client()
import xmlrpclib
try:
    actionkit.version()
except xmlrpclib.ProtocolError:
    print ("Your ActionKit API settings are incorrect; please double-check them "
           "and try again.")
    raise
