from django.conf.urls.defaults import *

urlpatterns = patterns('actions.views',
    url(r'^$', 'action_show', name='action_show'),
    url(r'^tag/(?P<tag_slug>\w+)/$', 'action_show', name='action_tag'),
    url(r'^(?P<action_slug>[a-z0-9-]+)/$', 'action_detail', name='action_detail'),
    url(r'^(?P<action_slug>[a-z0-9-]+)/complete/$', 'action_complete', name='action_complete'),
    url(r'^(?P<action_slug>[a-z0-9-]+)/undo/$', 'action_undo', name='action_undo'),
    url(r'^(?P<action_slug>[a-z0-9-]+)/commit/$', 'action_commit', name='action_commit'),
    url(r'^(?P<action_slug>[a-z0-9-]+)/cancel/$', 'action_cancel', name='action_cancel'),

    url(r'^(?P<action_slug>[a-z0-9-]+)/(?P<form_name>\w+)/save/$', 'save_action_form', name='save_action_form'),
)

urlpatterns += patterns('django.views.generic.simple',
    url(r'^eliminate-standby-vampire-power/power_strip/help/$', 'direct_to_template',
        {'template': 'actions/vampire_power/power_strip_help.html'}, name='power_strip_help'),
    url(r'^eliminate-standby-vampire-power/smart_power_strip/help/$', 'direct_to_template',
        {'template': 'actions/vampire_power/smart_power_strip_help.html'}, name='smart_power_strip_help'),
)
