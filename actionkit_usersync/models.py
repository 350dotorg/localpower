from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from actionkit_usersync.utils import get_client
from rah.models import Profile

class null_location(object):
    def __getattr__(self, *args, **kw):
        return ''

def user_post_save(sender, instance, created, **kwargs):
    user = instance
    actionkit = get_client()
    if created:
        # EGJ TODO: would prefer not to have city/country required;
        # we don't have that info yet
        result = actionkit.act(dict(
                page=settings.ACTIONKIT_PAGE_NAME,
                email=user.email,
                city="test",
                country="United states",
                ))
    else:
        profile = user.get_profile()
        location = profile.location or null_location()
        # EGJ TODO: what if profile.location is None?
        # i think the localpower system allows that
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
models.signals.post_save.connect(user_post_save, sender=User)

def profile_post_save(sender, instance, created, **kwargs):
    profile = instance
    user = profile.user
    # EGJ TODO: refactor with user_post_save else block

    location = profile.location or null_location()
    # EGJ TODO: what if profile.location is None?
    # i think the localpower system allows that
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
