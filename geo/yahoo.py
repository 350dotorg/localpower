from django.conf import settings
from json import load
from urllib2 import quote, urlopen

GEOCODE_URL = 'http://where.yahooapis.com/geocode?flags=J&q='

class Geocoder(object):
    @classmethod
    def _geocode(cls, url, data=None):
        if not data:
            data = {}
        try:
            res = load(urlopen(url))
            ## TODO: we are just always taking the top result
            results = res['ResultSet']['Results'][0]
            data['latitude'] = results['latitude']
            data['longitude'] = results['longitude']
            
            data['top_result'] = results
            return data
        except:
            raise ValueError('Could not locate this address')

    @classmethod
    def geocode(cls, value):
        value = value.encode("utf8")
        url = '%s%s' % (GEOCODE_URL, quote(value))
        data = cls._geocode(url)
        
        return data['latitude'], data['longitude'], data
