import sys, os

from utils import local_join

sys.path.insert(0, local_join('lib'))

PROJECT_DIR = os.path.dirname(__file__)

## Configure this in local_settings
## but note the GeoDjango ENGINE
#DATABASES = {
#  'default': {
#    'ENGINE': 'django.contrib.gis.db.backends.mysql',
#      'NAME': '',
#      'USER': '',
#      'PASSWORD': '',
#      'HOST': '',
#      'PORT': '',
#      },
#  }

# Name of the site for use in templates
SITE_NAME = "[Site Name]"
SITE_DOMAIN = "http://localhost:8000"
SITE_FEEDBACK_EMAIL = "feedback@example.com"

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:


# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en'
LANGUAGES = (('en', "English"),)

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True
USE_L10N = True
USE_L10N_FALLBACKS = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = local_join('static')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'
MEDIA_URL_HTTPS = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Caching
CACHE_BACKEND = 'memcached://127.0.0.1:11211/'
CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True
CACHE_MIDDLEWARE_SECONDS = 30

SESSION_ENGINE = 'django.contrib.sessions.backends.cached_db'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

MIDDLEWARE_CLASSES = (
    # 'django.middleware.cache.UpdateCacheMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'rah.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'rah_locale.flatpage_middleware.FlatpageFallbackMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'source_tracking.middleware.SourceTrackingMiddleware',
    'django.middleware.transaction.TransactionMiddleware',
    # 'django.middleware.cache.FetchFromCacheMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.request',
    'django.core.context_processors.media',
    'django.contrib.messages.context_processors.messages',
    'facebook_app.context_processors.facebook_appid',
    'rah.context_processors.site_name',
    'records.context_processors.ask_to_share',
    'codebase.context_processors.testing_feedback_form',
)

TEMPLATE_DIRS = (
    local_join('templates'),
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.sitemaps',
    'django.contrib.flatpages',
    'django.contrib.markup',
    'django.contrib.humanize',
    'django.contrib.gis',
    'tinymce',
    'rah',
    'rateable',
    'records',
    'geo',
    'basic.blog',
    'basic.inlines',
    'tagging',
    'twitter_app',
    'django_extensions',
    'groups',
    'group_links',
    'search_widget',
    'flagged',
    'invite',
    'dated_static',
    'actions',
    'events',
    'migrations',
    'messaging',
    'facebook_app',
    'thumbnails',
    'export',
    'source_tracking',
    'commitments',
    'codebase',
    'media_widget',
    'threadedcomments',
    'rah_comments',
    'rah_locale',
    'brabeion',
    'badges',
    'challenges',
    'discussions',
    'django.contrib.comments',
    'assetmanager',
    'djcelery',
    'djkombu',
    'djsupervisor',
    'djcelery_email',
)

BROKER_URL = "django://"

import djcelery
djcelery.setup_loader()

FIXTURE_DIR = ('fixtures',)

ABSOLUTE_URL_OVERRIDES = {
    'auth.user': lambda user: "/user/%s/" % user.id,
}

AUTHENTICATION_BACKENDS = ('rah.backends.EmailBackend',)
LOGIN_REDIRECT_URL = "/user/"
LOGIN_URL = "/register/"
LOGOUT_URL = "/logout/"
AUTH_PROFILE_MODULE = 'rah.Profile'

DEFAULT_FILE_STORAGE = 'assetmanager.storage_backend.OverwritingStorage'

MESSAGE_STORAGE = 'django.contrib.messages.storage.fallback.FallbackStorage'
GA_TRACK_PAGEVIEW = 50
GA_TRACK_CONVERSION = 51
MESSAGE_TAGS = {
    GA_TRACK_PAGEVIEW: 'ga_track_pageview',
    GA_TRACK_CONVERSION: 'ga_track_conversion',
}

# sync media s3
FILTER_LIST = ['.DS_Store', '.svn', '.hg', '.git', 'Thumbs.db', 'tools', 'group_images', '*.psd', '*.eps']
GZIP_CONTENT_TYPES = (
    'text/css',
    'application/javascript',
    'application/x-javascript'
)

COMMENTS_ALLOW_PROFANITIES = True

IGNORABLE_404_ENDS = ('.google-analytics.com/ga.js/', '/b.js/', 'index.php')

THUMBMNAIL_PROCESSORS = (
    'thumbnails.processors.Colorspace',
    'thumbnails.processors.SmartCrop',
)
THUMBNAIL_EXTENSION = '.png'

MYSQLDUPLICATE_EXCLUDE = ("django_site", "messaging_queue", "messaging_sent")

POSTMARK_SENDER = SITE_FEEDBACK_EMAIL

CODEBASE_PROJECT_URL = 'https://api3.codebasehq.com/rah'
CODEBASE_USERNAME = 'rah/macgruber'

COMMENTS_APP = 'rah_comments'

# Date defaults
DATETIME_FORMAT = "N j, Y, P"
DATE_FORMAT = "F j, Y"
TIME_FORMAT = "P"
SHORT_DATE_FORMAT = "m/d/Y"
SHORT_DATETIME_FORMAT = "m/d/Y P"
YEAR_MONTH_FORMAT = "F Y"
MONTH_DAY_FORMAT = "F j"
LONG_DATE_FORMAT = "l F j, Y"

# Should be set to something that's listed in `locale -a`
LOCALE = 'en_US'
 
TINYMCE_DEFAULT_CONFIG = {
    'theme': "advanced",
    'theme_advanced_toolbar_location' : "top",
    'theme_advanced_buttons1': "link,unlink,separator,bold,italic,underline,separator,bullist,numlist,separator,outdent,indent,separator,code,separator,undo,redo",
    'theme_advanced_buttons2': "",
    'theme_advanced_buttons3': "",
#    'content_css': MEDIA_URL + 'css/style.css',
}

GROUP_CREATION_FORM = "/groups/new/"

try:
    from local_settings import *
except ImportError:
    print 'local_settings could not be imported'
else:
    try:
        INSTALLED_APPS += LOCAL_INSTALLED_APPS
    except NameError:
        pass
    try:
        MIDDLEWARE_CLASSES += LOCAL_MIDDLEWARE_CLASSES
    except NameError:
        pass
