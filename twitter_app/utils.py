import oauth, httplib, json
from django.conf import settings

signature_method = oauth.OAuthSignatureMethod_HMAC_SHA1()

SERVER = getattr(settings, 'OAUTH_SERVER', 'twitter.com')
REQUEST_TOKEN_URL = getattr(settings, 'OAUTH_REQUEST_TOKEN_URL', 'https://%s/oauth/request_token' % SERVER)
ACCESS_TOKEN_URL = getattr(settings, 'OAUTH_ACCESS_TOKEN_URL', 'https://%s/oauth/access_token' % SERVER)
AUTHORIZATION_URL = getattr(settings, 'OAUTH_AUTHORIZATION_URL', 'http://%s/oauth/authorize' % SERVER)

CONSUMER_KEY = getattr(settings, 'TWITTER_CONSUMER_KEY', '')
CONSUMER_SECRET = getattr(settings, 'TWITTER_CONSUMER_SECRET', '')

CONSUMER = oauth.OAuthConsumer(CONSUMER_KEY, CONSUMER_SECRET)
def CONNECTION():
    return httplib.HTTPSConnection(SERVER)

# We use this URL to check if Twitters oAuth worked
TWITTER_CHECK_AUTH = 'https://twitter.com/account/verify_credentials.json'
TWITTER_FRIENDS = 'https://twitter.com/statuses/friends.json'
TWITTER_UPDATE_STATUS = 'https://twitter.com/statuses/update.json'

def request_oauth_resource(url, access_token, parameters=None, signature_method=signature_method, http_method="GET"):
    """
    usage: request_oauth_resource('/url/', your_access_token, parameters=dict() )
    Returns a OAuthRequest object
    """
    print CONSUMER_KEY
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        CONSUMER, token=access_token, http_method=http_method, http_url=url, parameters=parameters,
    )
    oauth_request.sign_request(signature_method, CONSUMER, access_token)
    return oauth_request


def fetch_response(oauth_request):
    url = oauth_request.to_url()
    c = CONNECTION()
    try:
        c.request(oauth_request.http_method, url)
        response = CONNECTION.getresponse()
        s = response.read()
    finally:
        c.close()
    return s

def get_unauthorised_request_token(signature_method=signature_method):
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        CONSUMER, http_url=REQUEST_TOKEN_URL
    )
    oauth_request.sign_request(signature_method, CONSUMER, None)
    resp = fetch_response(oauth_request)
    token = oauth.OAuthToken.from_string(resp)
    return token


def get_authorisation_url(token, signature_method=signature_method):
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        CONSUMER, token=token, http_url=AUTHORIZATION_URL
    )
    oauth_request.sign_request(signature_method, CONSUMER, token)
    return oauth_request.to_url()

def exchange_request_token_for_access_token(request_token, signature_method=signature_method):
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        CONSUMER, token=request_token, http_url=ACCESS_TOKEN_URL
    )
    oauth_request.sign_request(signature_method, CONSUMER, request_token)
    resp = fetch_response(oauth_request)
    return oauth.OAuthToken.from_string(resp)

def update_status(token, status):
    """Update twitter status, i.e., post a tweet"""
    oauth_request = request_oauth_resource(TWITTER_UPDATE_STATUS, token, {'status': status}, http_method='POST')
    json = fetch_response(oauth_request)
    return json
