from django.contrib.gis.db.models import GeoManager
from django.contrib.gis.db.models import PointField
from django.db import models

class Point(models.Model):
    latlng = PointField()
    raw_address = models.TextField()
    formatted_address = models.TextField()

    objects = GeoManager()

    def __unicode__(self):
        return self.formatted_address or self.raw_address

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
