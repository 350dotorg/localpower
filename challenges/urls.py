from django.conf.urls.defaults import *

urlpatterns = patterns('challenges.views',
    url(r'^$', 'list', name='challenges_list'),
    url(r'^create/$', 'create', name='challenges_create'),
    url(r'^(?P<challenge_id>\d+)/$', 'detail', name='challenges_detail'),
    url(r'^(?P<challenge_id>\d+)/edit/$', 'edit', name='challenges_edit'),
    url(r'^(?P<challenge_id>\d+)/sign/$', 'detail', name='challenges_sign'),
    url(r'^(?P<challenge_id>\d+)/pdf/$', 'pdf_download', name='challenges_pdf'),

    url(r'^(?P<challenge_id>\d+)/discussions/create/$', 'challenges_disc_create', name='challenges_disc_create'),
    url(r'^(?P<challenge_id>\d+)/contact/$', 'challenge_contact_admins', name='challenge_contact_admins'),

)
