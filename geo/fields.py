from json import load
from urllib2 import quote, urlopen

from django import forms
from django.forms import ValidationError
from django.contrib.gis import geos

from models import Location, Point

GOOGLE_GEOCODE_URL = 'http://maps.googleapis.com/maps/api/geocode/json?sensor=false'

class GoogleGeoField(forms.CharField):
    @classmethod
    def _google_geocode(cls, url, data=None):
        if not data:
            data = {}
        try:
            res = load(urlopen(url))
            if res['status'] != 'OK':
                raise Exception
            ## TODO: we are just always taking the top result
            results = res['results'][0]
            location = results['geometry']['location']
            if 'address' not in data:
                data['address'] = results['formatted_address']
            if 'latitude' not in data:
                data['latitude'] = location['lat']
            if 'longitude' not in data:
                data['longitude'] = location['lng']
            data['google_top_result'] = results
            return data
        except:
            raise ValidationError('Could not locate this address')

    def clean(self, value):
        value = super(GoogleGeoField, self).clean(value)
        if value:
            value = value.encode("utf8")
            url = '%s&address=%s' % (GOOGLE_GEOCODE_URL, quote(value))
            data = GoogleGeoField._google_geocode(url)

            url = '%s&latlng=%s,%s' % (GOOGLE_GEOCODE_URL, 
                                       data['latitude'], data['longitude'])
            result = GoogleGeoField._google_geocode(url, data)
            result['user_input'] = value
            return result
        return value

class GoogleLocationField(GoogleGeoField):
    def __init__(self, *args, **kwargs):
        super(GoogleLocationField, self).__init__(*args, **kwargs)
        self.raw_data = {}

    def prepare_value(self, value):
        if isinstance(value, int) or isinstance(value, long):
            return Location.objects.get(pk=value)
        return value

    def clean(self, value):
        value = super(GoogleLocationField, self).clean(value)
        if value:
            try:
                lat = value['latitude']
                lng = value['longitude']
                user_input = value['user_input']
                google_address = value['address']
            except:
                return value
            latlng = geos.Point(float(lng), float(lat))
            point = Point.objects.create(
                latlng=latlng,
                raw_address=user_input,
                formatted_address=google_address)
            self.raw_data = value
            return point
        return value
