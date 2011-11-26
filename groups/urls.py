from django.conf.urls.defaults import *

from search_widget.views import search_list

from models import Group
from feeds import GroupActivityFeed

group_search_info = {
    'queryset': Group.objects.all().order_by("-created"),
    'paginate_by': 5,
    'search_fields': ['name', 'description',],
    'template_name': 'groups/_search_listing',
    'object_rendering_template': 'groups/_group_search_result.html',
}

urlpatterns = patterns(
    'groups.views',

    url(r'^$', 'group_list', name='group_list'),
    url(r'^create/$', 'group_create', name='group_create'),
    url(r'^create/external/$', 'group_external_link_only_create', 
        name='group_external_link_only_create'),

    url(r'^(?P<group_id>\d+)/facebook/edit/$', 'group_external_link_form',
        {'link_type': "facebook"},
        name='group_facebook_link_form'),
    url(r'^(?P<group_id>\d+)/twitter/edit/$', 'group_external_link_form', 
        {'link_type': "twitter"},
        name='group_twitter_link_form'),

    url(r'^(?P<group_id>\d+)/leave/$', 'group_leave', name='group_leave'),
    url(r'^(?P<group_id>\d+)/join/$', 'group_join', name='group_join'),
    url(r'^(?P<group_id>\d+)/approve/(?P<user_id>\d+)/$', 'group_membership_request', {'action': 'approve'}, name='group_approve'),
    url(r'^(?P<group_id>\d+)/deny/(?P<user_id>\d+)/$', 'group_membership_request', {'action': 'deny'}, name='group_deny'),

    url(r'^search/$', search_list, group_search_info, name='group_search'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/$', 'group_detail', name='group_detail'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/edit/$', 'group_edit', name='group_edit'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/feed/$', GroupActivityFeed(), name='group_activity_feed'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/discussions/$', 'group_disc_list', name='group_disc_list'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/discussions/create/$', 'group_disc_create', name='group_disc_create'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/discussions/(?P<disc_id>\d+)/$', 'group_disc_detail', name='group_disc_detail'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/discussions/(?P<disc_id>\d+)/remove/$', 'group_disc_remove', name='group_disc_remove'),
    url(r'^(?P<group_slug>[a-z0-9-]+)/discussions/(?P<disc_id>\d+)/approve/$', 'group_disc_approve', name='group_disc_approve'),

    url(r'^(?P<group_slug>[a-z0-9-]+)/contact/$', 'group_contact_admins',
        name='group_contact_admins'),

    url(r'^(?P<group_id>\d+)/event_approve/(?P<object_id>\d+)/$', 
        'group_association_request', 
        {'action': 'approve', 'content_type': 'events.event'}, 
        name='group_event_approve'),
    url(r'^(?P<group_id>\d+)/event_deny/(?P<object_id>\d+)/$', 
        'group_association_request', 
        {'action': 'deny', 'content_type': 'events.event'}, 
        name='group_event_deny'),
    
    url(r'^(?P<group_id>\d+)/challenge_approve/(?P<object_id>\d+)/$', 
        'group_association_request', 
        {'action': 'approve', 'content_type': 'challenges.challenge'}, 
        name='group_challenge_approve'),
    url(r'^(?P<group_id>\d+)/challenge_deny/(?P<object_id>\d+)/$', 
        'group_association_request', 
        {'action': 'deny', 'content_type': 'challenges.challenge'}, 
        name='group_challenge_deny'),

    url(r'^(?P<group_id>\d+)/action_approve/(?P<object_id>\d+)/$', 
        'group_association_request', 
        {'action': 'approve', 'content_type': 'actions.action'}, 
        name='group_action_approve'),
    url(r'^(?P<group_id>\d+)/action_deny/(?P<object_id>\d+)/$', 
        'group_association_request', 
        {'action': 'deny', 'content_type': 'actions.action'}, 
        name='group_action_deny'),

)
