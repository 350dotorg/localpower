from django import http
from django.conf import settings
from django.utils.translation import check_for_language, activate, to_locale, get_language

def set_language(request):
    """
    Redirect to a given url while setting the chosen language in the
    session or cookie. The url and the language code need to be
    specified in the request parameters.

    Since this view changes how the user will see the rest of the site, it must
    only be accessed as a POST request. If called as a GET request, it will
    redirect to the page in the request (the 'next' parameter) without changing
    any state.
    """
    next = request.REQUEST.get('next', None)
    if not next:
        next = request.META.get('HTTP_REFERER', None)
    if not next:
        next = '/'
    response = http.HttpResponseRedirect(next)
    if request.method == 'GET':
        lang_code = request.GET.get('language', None)
        if lang_code and check_for_language(lang_code):
            if hasattr(request, 'session'):
                request.session['django_language'] = lang_code
            else:
                response.set_cookie(settings.LANGUAGE_COOKIE_NAME, lang_code)
            if not request.user.is_anonymous():
                profile = request.user.get_profile()
                profile.language = lang_code
                profile.save()
    return response
