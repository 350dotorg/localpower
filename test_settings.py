try:
    from settings import *
except ImportError:
    print 'settings could not be imported'
    
DATABASE_ENGINE   = 'sqlite3'  # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.comments',
    'django.contrib.sites',
    'django.contrib.messages',
    'rah',
    'rateable',
    'rateable.tests',
    'records',
    'geo',
    'invite',
    'basic.blog',
    'basic.inlines',
    'tagging',
    'twitter_app',
    'search_widget',
    'groups',
    'sorl.thumbnail',
    'flagged',
    'django_extensions',
    'debug_toolbar',
)