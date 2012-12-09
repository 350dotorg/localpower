import settings
from django.conf.urls.defaults import *

# Horribly monkeypatch Django internals
from django.contrib.auth import decorators
from utils import login_required 
decorators.login_required = login_required
# And some more, for https://github.com/350org/localpower/issues/143
from django.contrib.auth.models import User
def get_full_name_anonymized(self):
    if self.last_name:
        last_initial = "%s." % self.last_name[0]
    else:
        last_initial = ''
    full_name = u'%s %s' % (self.first_name, last_initial)
    return full_name.strip()
User.get_full_name = get_full_name_anonymized
User.__unicode__ = get_full_name_anonymized

# Register apps with the admin interface
from actions import admin as actions_admin
from basic.blog import admin as blog_admin
from rah import admin as rah_admin
from rah.feeds import UserActivityFeed, CommentsFeed
from geo import admin as geo_admin
from groups import admin as groups_admin
from group_links import admin as group_links_admin
from tagging import admin as tagging_admin
from events import admin as event_admin
from media_widget import admin as media_widget_admin
from django.contrib.flatpages import admin as flatpages_admin
from messaging import admin as messaging_admin
from commitments import admin as commitments_admin
from challenges import admin as challenges_admin
from assetmanager import admin as assetmanager_admin
from rah_locale import admin as rah_locale_admin

# Unregister some models within some apps from the admin
from django.contrib import admin
from django.contrib.admin.sites import NotRegistered
from basic.blog.models import Category, BlogRoll
from tagging.models import TaggedItem

def unregister(model):
    try:
        admin.site.unregister(model)
    except NotRegistered:
        pass
unregister(Category)
unregister(BlogRoll)
unregister(TaggedItem)

# Sitemaps
from basic.blog.sitemap import BlogSitemap
from django.contrib.sitemaps import FlatPageSitemap
from actions.sitemap import ActionSitemap
from groups.sitemap import GroupSitemap
from rah.sitemap import RahSitemap
sitemaps = {
#    'blog':     BlogSitemap,
    'flat':     FlatPageSitemap,
    'actions':  ActionSitemap,
    'groups':   GroupSitemap,
    'rah':      RahSitemap,
}

# Prepare some feed classes
from basic.blog.feeds import BlogPostsFeed
from groups.feeds import GroupActivityFeed
from events.feeds import EventsFeed
#from ics_feed.feeds import CombinedICSFeed

# Import some custom forms to pass into the auth app urls
from rah.forms import AuthenticationForm, SetPasswordForm, PasswordChangeForm

from rah.export_action import admin_list_export
admin.site.add_action(admin_list_export, 'Export to CSV')

urlpatterns = patterns('rah.views',
    url(r'^$', 'index', name='index'),
    url(r'^admin/translations/reload/$', 'reload_i18n', name='reload_i18n'),                       
    url(r'^register/$', 'register', name='register'),
    url(r'^login/$', 'login', name='login'),
    url(r'^logout/$', 'logout', name='logout'),
    url(r'^password_change_done/$', 'password_change_done', name='password_change_done'),
    url(r'^password_reset_done/$', 'password_reset_done', name='password_reset_done'),
    url(r'^reset/done/$', 'password_reset_complete', name='password_reset_complete'),
    url(r'^user/(?P<user_id>\d+)/$', 'profile', name='profile'),
    url(r'^user/(?P<user_id>\d+)/contact/$', 'user_contact', name='user_contact'),
    url(r'^user/(?P<user_id>\d+)/picture/$', 'user_profile_picture', name='user_profile_picture'),
    url(r'^user/edit/(?P<user_id>\d+)/$', 'profile_edit', name='profile_edit'),
    url(r'^user/$', 'user_self_redirect', name='user_self_redirect'),
    url(r'^user/list/$', 'user_list', name='user_list'),
    url(r'^user/list/batch/$', 'user_list_batch', name='user_list_batch'),
    url(r'^validate/$', 'validate_field', name="validate_field"),
    url(r'^feedback/$', 'feedback', name='feedback'),
    url(r'^search/$', 'search', name='search'),
    url(r'^user/ga-opt-out/$', 'ga_opt_out', name='ga_opt_out'),
    url(r'user/(?P<user_id>\d+)/feed/$', UserActivityFeed(), name='user_activity_feed'),
)

urlpatterns += patterns('django.views.generic.simple',
    url(r'^vampire/$', 'redirect_to', {'url': '/actions/eliminate-standby-vampire-power/'}),
)

urlpatterns += patterns(
    '',
    url(r'^set_language/$', 'rah_locale.views.set_language', name="set_language"),

    url(r'^moderate/discussions/(?P<user_id>\d+)/$', 
        'discussions.views.staff_review_discussions',
        name="staff_review_discussions"),
    url(r'^moderate/discussions/(?P<user_id>\d+)/ham/$', 
        'discussions.views.staff_review_discussions',
        { 'moderation_status': "not_spam" },
        name="staff_review_discussions_mark_ham"),
    url(r'^moderate/discussions/(?P<user_id>\d+)/spam/$', 
        'discussions.views.staff_review_discussions',
        { 'moderation_status': "spam" },
        name="staff_review_discussions_mark_spam"),

    (r'^tinymce/', include('tinymce.urls')),
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^password_change/$', 'django.contrib.auth.views.password_change', { 'post_change_redirect': '/password_change_done/', 'password_change_form': PasswordChangeForm }, name='password_change'),
    url(r'^password_reset/$', 'django.contrib.auth.views.password_reset', { 'post_reset_redirect': '/password_reset_done/' }, name='password_reset'),
    url(r'^reset/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 
        'django.contrib.auth.views.password_reset_confirm',
        { 'post_reset_redirect': '/reset/done/',
          'set_password_form': SetPasswordForm }, 
        name='password_reset_confirm'),
    url(r'^claim_account/done/$', 'export.views.account_claim_complete', 
        name='claim_account_complete'),
    url(r'^claim_account/(?P<uidb36>[0-9A-Za-z]+)-(?P<token>.+)/$', 
        'export.views.password_reset_confirm',
        { 'post_reset_redirect': '/claim_account/done/', 
          'set_password_form': SetPasswordForm, 
          'template_name': 'export/claim_account_password_reset_confirm.html' }, 
        name='password_reset_claim_account_confirm'),

    url(r'^', include('django.contrib.auth.urls')),
    url(r'^blog/', 'rah.views.redirect_to_blog'),
#    url(r'^blog/feed/$', BlogPostsFeed(), name='blog_feed'),
    url(r'^comments/', include('django.contrib.comments.urls')),
    url(r'^twitter/', include('twitter_app.urls')),
    url(r'^rateable/', include('rateable.urls')),
    url(r'^groups/', include('groups.urls')),
    url(r'^media_widget/', include('media_widget.urls')),
    url(r'^invite/', include('invite.urls')),
    url(r'^flagged/flag/$', 'flagged.views.flag', name='flagged-flag'),
    url(r'^projects/', include('actions.urls')),
    url(r'^records/', include('records.urls')),
    url(r'^events/', include('events.urls')),
    url(r'^events/feed/$', EventsFeed(), name='events_feed'),
    url(r'^messaging/', include('messaging.urls')),
    url(r'^facebook/', include('facebook_app.urls')),
    url(r'^commitments/', include('commitments.urls')),
    url(r'^admin/export/', include('export.urls')),
    url(r'^sitemap\.xml$', 'django.contrib.sitemaps.views.sitemap', {'sitemaps': sitemaps}, name='sitemap'),
    url(r'^codebase/', include('codebase.urls')),
    url(r'^badges/', include('badges.urls')),
    url(r'^campaigns/', include('challenges.urls')),
    url(r'^admin/', include(admin.site.urls), name='admin_root'),
    #url(r'^icalfeed/', CombinedICSFeed(), name='ical_feed'),
    url(r'comments/(?P<content_type_id>\d+)/(?P<object_pk>\d+)/feed/$', CommentsFeed(), name='comments_feed'),
    url('^_inbound_mail/$', 'groups.views.receive_mail'),
)

if settings.DEBUG:
    urlpatterns += patterns('django.views.static',
        url(r'^static/(?P<path>.*)$', 'serve', {'document_root': settings.MEDIA_ROOT, 'show_indexes': True }),
    )

# These patterns are redeclared here so they can be at the domain root. e.g. /community-name instead of /communities/community-name
urlpatterns += patterns('groups.views',
    url(r'^(?P<group_slug>[a-z0-9-]+)/$', 'group_detail', name='group_detail'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/edit/$', 'group_edit', name='group_edit'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/feed/$', GroupActivityFeed(), name='group_activity_feed'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/discussions/$', 'group_disc_list', name='group_disc_list'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/discussions/create/$', 'group_disc_create', name='group_disc_create'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/discussions/(?P<disc_id>\d+)/$', 'group_disc_detail', name='group_disc_detail'),

    url(r'^(?P<group_slug>[a-z0-9-]+)/contact/$', 'group_contact_admins',
        name='group_contact_admins'),

)
