from geo.fields import GoogleLocationField as Google
from geo.models import Point
from django.contrib.gis import geos

from rah.models import Profile
from events.models import Event
from groups.models import Group
from commitments.models import Contributor
from django.db import transaction

def migrate_profiles():
    for p in Profile.objects.filter(location__isnull=False,
                                    geom__isnull=True):
        l = p.location
        latlng = geos.Point(float(l.lon),
                            float(l.lat))
        g = Point.objects.create(
            latlng=latlng, 
            raw_address=str(l),
            formatted_address=l.long())
        p.geom = g
        p.save()

def migrate_events():
    for p in Event.objects.filter(location__isnull=False,
                                  geom__isnull=True):
        l = p.location
        latlng = geos.Point(float(l.lon),
                            float(l.lat))
        g = Point.objects.create(
            latlng=latlng, 
            raw_address=p.where,
            formatted_address=l.long())
        p.geom = g
        p.save()

def migrate_groups():
    for p in Group.objects.filter(headquarters__isnull=False,
                                  geom__isnull=True):
        l = p.headquarters
        latlng = geos.Point(float(l.lon),
                            float(l.lat))
        g = Point.objects.create(
            latlng=latlng, 
            raw_address=str(l),
            formatted_address=l.long())
        p.geom = g
        p.save()

def migrate_contributors():
    for p in Contributor.objects.filter(location__isnull=False,
                                        geom__isnull=True):
        l = p.location
        latlng = geos.Point(float(l.lon),
                            float(l.lat))
        g = Point.objects.create(
            latlng=latlng, 
            raw_address=str(l),
            formatted_address=l.long())
        p.geom = g
        p.save()

def wipe_unused_geoms():
    for p in Point.objects.all():
        if (not p.contributor_set.count()
            and not p.group_set.count()
            and not p.event_set.count()
            and not p.profile_set.count()):
            p.delete()

def wipe():
    wipe_unused_geoms()

def run():
    migrate_profiles()
    migrate_events()
    migrate_groups()
    migrate_contributors()
