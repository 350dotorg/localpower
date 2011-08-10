DEBUG = False
TEMPLATE_DEBUG = DEBUG
SEND_BROKEN_LINK_EMAILS = not DEBUG
IGNORABLE_404_ENDS = ("ga.js/", "b.js/",)

INTERNAL_IPS = ("127.0.0.1")

ADMINS = (
    ('Server Errors', 'servererrors@repowerathome.com'),
)
MANAGERS = ADMINS

DATABASE_ENGINE   = 'mysql'
DATABASE_NAME     = 'lp'
DATABASE_USER     = 'lp_db_user'
DATABASE_PASSWORD = "_db_password"
DATABASE_HOST     = "_db_host"
DATABASE_PORT     = "_db_port"

# Email Settings
EMAIL_HOST = "localhost"
DEFAULT_FROM_EMAIL = "No Reply <noreply@repowerathome.com>"
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_USE_TLS = True
EMAIL_BACKEND = 'postmark.django_backend.EmailBackend'
POSTMARK_API_KEY = '_postmark_api_key'

MEDIA_URL = 'http://_s3_bucket_name/'
MEDIA_URL_HTTPS = 'https://s3.amazonaws.com/_s3_bucket_name/'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'

# Secrets and Keys
SECRET_KEY = '_secret_key'
AWS_BUCKET_NAME = '_s3_bucket_name'
AWS_STORAGE_BUCKET_NAME = AWS_BUCKET_NAME
AWS_ACCESS_KEY_ID = "_aws_access_key"
AWS_SECRET_ACCESS_KEY = "_aws_secret_key"
TWITTER_CONSUMER_KEY = '_twitter_consumer_key'
TWITTER_CONSUMER_SECRET = '_twitter_consumer_secret'
FACEBOOK_APPID = '_facebook_appid'
FACEBOOK_SECRET = '_facebook_secret'
ACTIONKIT_API_HOST = '_ak_api_host'
ACTIONKIT_API_USER = '_ak_api_user'
ACTIONKIT_API_PASSWORD = '_ak_api_pass'
