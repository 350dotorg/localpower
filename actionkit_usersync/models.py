from django.contrib.auth.models import User
from django.db import models
from rah.models import Profile
from actionkit_usersync.tasks import actionkit_push

def user_post_save(sender, instance, created, **kwargs):
    user = instance
    profile = user.get_profile()
    ak_user = actionkit_push.delay(user, profile)
models.signals.post_save.connect(user_post_save, sender=User)

def profile_post_save(sender, instance, created, **kwargs):
    profile = instance
    user = profile.user
    ak_user = actionkit_push.delay(user, profile)
models.signals.post_save.connect(profile_post_save, sender=Profile)

# EGJ TODO: test profile post-save signal

# Verify that the ActionKit API settings are correct 
# and successfully connect to the server
#actionkit = get_client()
#import xmlrpclib
#try:
#    actionkit.version()
#except xmlrpclib.ProtocolError:
#    print ("Your ActionKit API settings are incorrect; please double-check them "
#           "and try again.")
#    raise
