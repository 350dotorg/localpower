from json import dumps

from django.contrib.gis.db.models import GeoManager
from django.contrib.gis.db.models import PointField
from django.db import models

from geo.yahoo import Geocoder
from geo.regions import REGION_MAP

class Point(models.Model):
    latlng = PointField()
    raw_address = models.TextField()
    formatted_address = models.TextField()

    city = models.CharField(max_length=200, db_index=True, 
                            null=True, blank=True)
    state = models.CharField(max_length=200, db_index=True, 
                             null=True, blank=True)
    country = models.CharField(max_length=200, db_index=True, 
                               null=True, blank=True)
    postal = models.CharField(max_length=200, db_index=True, 
                              null=True, blank=True)
    raw_data = models.TextField(null=True, blank=True)
    region = models.CharField(max_length=200, db_index=True,
                              null=True, blank=True)

    objects = GeoManager()

    def __unicode__(self):
        return self.formatted_address or self.raw_address

    def geocode(self):
        return Geocoder.geocode(self.formatted_address)

    def normalize(self):
        data = self.geocode()
        self.raw_data = dumps(data)
        r = data[2]['top_result']

        def get_component(type):
            components = r.get("address_components", [])
            for component in components:
                if type not in component['types']:
                    continue
                return component['long_name']

        self.city = get_component('locality')
        self.state = get_component('administrative_area_level_1')
        self.country = get_component('country')
        self.postal = get_component('postal_code')
        self.region = REGION_MAP.get(self.country) or None
        self.save()

    def save(self, *args, **kw):
        models.Model.save(self, *args, **kw)
        if self.raw_data:
            return
        self.normalize()
    
class Location(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    zipcode = models.CharField(max_length=5, db_index=True)
    county = models.CharField(max_length=100, db_index=True)
    st = models.CharField(max_length=2, db_index=True)
    state = models.CharField(max_length=50)
    lon = models.CharField(max_length=50)
    lat = models.CharField(max_length=50)
    recruit = models.BooleanField(default=False)

    def __unicode__(self):
        return u'%s, %s' % (self.name, self.st)

    def long(self):
        return u'%s, %s, USA' % (self.name, self.state)
