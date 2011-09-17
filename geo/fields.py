from json import load
from urllib2 import quote, urlopen

from django import forms
from django.forms import ValidationError
from django.contrib.localflavor.us.forms import USZipCodeField

from models import Location

GOOGLE_GEOCODE_URL = 'http://maps.googleapis.com/maps/api/geocode/json?sensor=false'

class ZipCodeField(USZipCodeField):
    def clean(self, value):
        if value:
            if not Location.objects.filter(zipcode=value).exists():
                raise ValidationError("Invalid zipcode %s" % value)
        return value

class GoogleGeoField(forms.CharField):
    @classmethod
    def _google_geocode(cls, url, data=None):
        if not data:
            data = {}
        try:
            res = load(urlopen(url))
            if res['status'] != 'OK':
                raise Exception
            results = res['results'][0]
            location = results['geometry']['location']
            if 'address' not in data:
                data['address'] = results['formatted_address']
            if 'latitude' not in data:
                data['latitude'] = location['lat']
            if 'longitude' not in data:
                data['longitude'] = location['lng']

            # search for the postal_code
            zipcode = None
            for comp in results['address_components']:
                if 'postal_code' in comp['types']:
                    zipcode = comp['short_name']
                    data['zipcode'] = zipcode
                    data['location'] = Location.objects.get(zipcode=zipcode)
                    break
            return data
        except:
            raise ValidationError('Could not locate this address')

    def clean(self, value):
        value = super(GoogleGeoField, self).clean(value)
        if value:
            url = '%s&address=%s' % (GOOGLE_GEOCODE_URL, quote(value))
            data = GoogleGeoField._google_geocode(url)
            if 'location' in data:
                return data
            url = '%s&latlng=%s,%s' % (GOOGLE_GEOCODE_URL, data['latitude'], data['longitude'])
            return GoogleGeoField._google_geocode(url, data)
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
            self.raw_data = value
            return value['location']
        return value
