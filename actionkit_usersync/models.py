from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from actionkit_usersync.utils import get_client
from rah.models import Profile
from geo.fields import GoogleGeoField

class null_location(object):
    def __getattr__(self, *args, **kw):
        return ''

class google_location(object):
    def __init__(self, geom):
        self.g = GoogleGeoField().clean(geom.formatted_address)
        addr = dict()
        for row in self.g['google_top_result']['address_components']:
            addr[tuple(row['types'])] = row
            for i in row['types']:
                addr[i] = row
        self.addr = addr

    @property
    def postal(self):
        try:
            postal = self.addr['postal']
        except:
            return ''
        return postal['long_name']

    @property
    def zipcode(self):
        if self.country != "United States":
            return ''
        return self.postal

    @property
    def county(self):
        try:
            addr = self.addr['administrative_area_level_2']
        except:
            pass
        else:
            return addr['long_name']
        try:
            addr = self.addr['administrative_area_level_1']
        except:
            return ''
        return addr['long_name']

    @property
    def st(self):
        if self.country != "United States":
            return ''
        try:
            addr = self.addr['administrative_area_level_1']
        except:
            return ''
        return addr['short_name']

    @property
    def state(self):
        try:
            addr = self.addr['administrative_area_level_1']
        except:
            return ''
        return addr['long_name']

    @property
    def name(self):
        try:
            addr = self.addr['sublocality']
        except:
            pass
        else:
            return addr['long_name']
        try:
            addr = self.addr['locality']
        except:
            return ''
        else:
            return addr['long_name']

    @property
    def country(self):
        try:
            addr = self.addr['country']
        except:
            return ''
        else:
            return addr['long_name']
        
def actionkit_push(user, profile):
    geom = profile.geom
    if geom:
        location = google_location(geom)
    else:
        location = null_location()

    # EGJ TODO: what if profile.geom is None?
    # i think the localpower system allows that
    # currently just setting empty strings (per line above)
   
    actionkit = get_client()
    ak_user = actionkit.User.save_or_create(dict(
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            zip=location.zipcode,
            postal=location.postal,
            region=location.county,
            state=location.st,
            state_name=location.state,
            city=location.name,
            country=location.country
            ))

    try:
        page_name = settings.ACTIONKIT_PAGE_NAME
    except AttributeError:
        return ak_user

    history = actionkit.User.subscription_history({'id': ak_user['id']})
    ever_been_subscribed = False
    for entry in history:
        if entry.get("page_name") == page_name:
            ever_been_subscribed = True
            break
    if not ever_been_subscribed:
        result = actionkit.act(dict(
                page=page_name,
                email=user.email))

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
#actionkit = get_client()
#import xmlrpclib
#try:
#    actionkit.version()
#except xmlrpclib.ProtocolError:
#    print ("Your ActionKit API settings are incorrect; please double-check them "
#           "and try again.")
#    raise
