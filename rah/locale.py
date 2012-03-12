"this is the locale selecting middleware that will look at accept headers"

from django.utils.cache import patch_vary_headers
from django.utils import translation
from django.conf import settings

class LocaleMiddleware(object):
    """
    This is a very simple middleware that parses a request
    and decides what translation object to install in the current
    thread context. This allows pages to be dynamically
    translated to the language the user desires (if the language
    is available, of course).
    """

    def get_language_from_profile(self, profile):
        language = profile.language
        if not language:
            return None
        supported = dict(settings.LANGUAGES)
        if language in supported and translation.check_for_language(language):
            return language

    def process_request(self, request):
        profile = None; language = None
        if not request.user.is_anonymous():
            profile = request.user.get_profile()
            language = self.get_language_from_profile(profile)
        if not language:
            language = translation.get_language_from_request(request)
        translation.activate(language)
        if profile:
            if not profile.language or profile.language != language:
                profile.language = language
                profile.save()
        request.LANGUAGE_CODE = translation.get_language()
        request.LANGUAGE_VERBOSE_NAME = dict(settings.LANGUAGES)[
            request.LANGUAGE_CODE]

    def process_response(self, request, response):
        patch_vary_headers(response, ('Accept-Language',))
        if 'Content-Language' not in response:
            response['Content-Language'] = translation.get_language()
        translation.deactivate()
        return response
