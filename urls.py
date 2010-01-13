import settings
from django.conf.urls.defaults import *
from django.core.urlresolvers import reverse
from rah.forms import AuthenticationForm
from basic.blog.feeds import BlogPostsFeed

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

feeds = {
    'blog': BlogPostsFeed,
}

# OPTIMIZE: we can wrap the regex patterns in the url function to insure there are no reverse conflicts
urlpatterns = patterns('rah.views',
    url(r'^$', 'index', name='index'),
    url(r'^register/$', 'register', name='register'),
    url(r'^logout/$', 'logout', name='logout'),
    url(r'^password_changed/$', 'password_changed', name='password_changed'),
    (r'^actions/$', 'action_show'),
    (r'^actions/(?P<action_slug>[a-z0-9-]+)/$', 'action_detail'),
    (r'^actiontasks/(?P<action_task_id>\d+)/$', 'action_task'),
    url(r'^user/(?P<user_id>\d+)/$', 'profile', name='profile'),
    url(r'^user/edit/(?P<user_id>\d+)/$', 'profile_edit', name='profile_edit'),
    (r'^validate/$', 'validate_field'),
    (r'^houseparty/$', 'house_party'),
    (r'^invitefriend/$', 'invite_friend'),
    (r'^feedback/$', 'feedback'),
    (r'^search/$', 'search'),
    url(r'^comments/post/$', 'post_comment', name='post_comment'),
)

urlpatterns += patterns('',
    url(r'^(?P<url>.*)/feed/$', 'django.contrib.syndication.views.feed', {'feed_dict': feeds}, name='feed'),
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^login/$', 'django.contrib.auth.views.login', { 'authentication_form': AuthenticationForm }, name='login'),
    url(r'^password_change/$', 'django.contrib.auth.views.password_change', { 'post_change_redirect': '/password_changed/' }, name='password_change'),
    (r'^', include('django.contrib.auth.urls')),
    url(r'^admin/(.*)', admin.site.root, name='admin_root'),
    (r'^blog/', include('basic.blog.urls')),
    (r'^comments/', include('django.contrib.comments.urls')),
    url(r'^twitter/', include('twitter_app.urls')),
)

if settings.DEBUG:
    urlpatterns += patterns('django.views.static',
    (r'^static/(?P<path>.*)$', 
        'serve', {
        'document_root': settings.MEDIA_ROOT,
        'show_indexes': True }),)