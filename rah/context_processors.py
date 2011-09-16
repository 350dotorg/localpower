from django.conf import settings

def site_name(request):
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_DOMAIN': settings.SITE_DOMAIN,
        'SITE_FEEDBACK_EMAIL': settings.SITE_FEEDBACK_EMAIL,
        'settings': settings,
    }
