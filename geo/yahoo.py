from django.conf import settings
from json import load
from urllib2 import quote, urlopen

#GEOCODE_URL = 'http://where.yahooapis.com/geocode?flags=J&appid=%s&q=' % settings.YAHOO_APP_ID
GEOCODE_URL = 'http://maps.googleapis.com/maps/api/geocode/json?sensor=false&address='

class Geocoder(object):
    @classmethod
    def _geocode(cls, url, data=None):
        if not data:
            data = {}
        try:
            res = load(urlopen(url))
            ## TODO: we are just always taking the top result
#            results = res['ResultSet']['Results'][0]
            results = res['results'][0]
#            data['latitude'] = results['latitude']
#            data['longitude'] = results['longitude']
            data['latitude'] = results['geometry']['location']['lat']
            data['longitude'] = results['geometry']['location']['lng']
            data['top_result'] = results
            return data
        except Exception, e:
            raise ValueError('Could not locate this address, %s -- %s' % (
                    url, str(e)))

    @classmethod
    def geocode(cls, value):
        value = value.encode("utf8")
        url = '%s%s' % (GEOCODE_URL, quote(value))
        tries = 0
        while True:
            try:
                data = cls._geocode(url)
            except ValueError:
                tries += 1
                if tries > 4:
                    raise
            else:
                break
        
        return data['latitude'], data['longitude'], data
