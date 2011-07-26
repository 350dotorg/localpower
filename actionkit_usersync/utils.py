from django.conf import settings
import xmlrpclib

def get_client():
    actionkit = xmlrpclib.Server('http://%s:%s@%s/api/' % (
            settings.ACTIONKIT_API_USER,
            settings.ACTIONKIT_API_PASSWORD,
            settings.ACTIONKIT_API_HOST))
    return actionkit
