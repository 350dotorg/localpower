from django.conf.urls.defaults import *

from twitter_app.views import *

urlpatterns = patterns('twitter_app.views',
    url(r'^auth/$',
        view=auth,
        name='twitter_oauth_auth'),

    url(r'^return/$',
        view=return_,
        name='twitter_oauth_return'),

    url(r'^clear/$',
        view=unauth,
        name='twitter_oauth_unauth'),

    url(r'^status/$',
        view=post_status,
        name='twitter_oauth_post_status'),

    url(r"^sharing/enable/$", "sharing", {"is_enabled": True}, name="twitter_enable_sharing"),
    url(r"^sharing/disable/$", "sharing", {"is_enabled": False}, name="twitter_disable_sharing"),
)
