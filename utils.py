import os
import re

def local_join(path):
    """Convenience function for path joining"""
    return os.path.join(os.path.dirname(__file__), path)

def hash_val(value):
    """Creates a SHA1 hash of a value with the secret key"""
    import hashlib
    from django.conf import settings
    if not value:
        raise Exception("Cannot hash a value that evaluates to False")
    try:
        hash_string = ""
        for item in value:
            hash_string += unicode(item)
    except:
        hash_string = unicode(value)

    return hashlib.sha1("%s%s" % (settings.SECRET_KEY, hash_string)).hexdigest()

QUOTE_REGEX = re.compile("""^('.*')|(".*")$""")
def strip_quotes(val):
    """Remove quote from a value"""
    return val[1:-1] if QUOTE_REGEX.match(val) else val

def forbidden(request, message="You do not have permissions."):
    """Return a 500 page with a given message"""
    from django.http import HttpResponseForbidden
    from django.template import loader, RequestContext
    return HttpResponseForbidden(loader.render_to_string('403.html', { 'message':message, }, RequestContext(request)))

def hex_to_byte(hex_str):
    """
    Convert a string hex byte values into a byte string. The Hex Byte values may
    or may not be space separated.
    """
    byte_list = []
    hex_str = ''.join(hex_str.split(" "))
    for i in range(0, len(hex_str), 2):
        byte_list.append(chr(int(hex_str[i:i+2], 16)))
    return ''.join(byte_list)

def ajax_required(f):
    """
    AJAX request required decorator
    use it in your views:

    @ajax_required
    def my_view(request):
        ....

    """
    def wrap(request, *args, **kwargs):
            if not request.is_ajax():
                return forbidden(request)
            return f(request, *args, **kwargs)
    wrap.__doc__=f.__doc__
    wrap.__name__=f.__name__
    return wrap

try:
    from functools import update_wrapper, wraps
except ImportError:
    from django.utils.functional import update_wrapper, wraps  # Python 2.4 fallback.

from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.utils.decorators import available_attrs
from django.utils.http import urlquote

from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

def user_passes_test(test_func, login_url=None, redirect_field_name=REDIRECT_FIELD_NAME,
                     message_string=_("You need to create an account first. "
                                      "Don't worry -- it only takes 15 seconds!")):
    """
    Decorator for views that checks that the user passes the given test,
    redirecting to the log-in page if necessary. The test should be a callable
    that takes the user object and returns True if the user passes.
    """
    if not login_url:
        from django.conf import settings
        login_url = settings.LOGIN_URL

    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if test_func(request.user):
                return view_func(request, *args, **kwargs)
            path = urlquote(request.get_full_path())
            tup = login_url, redirect_field_name, path
            messages.info(request, message_string)
            return HttpResponseRedirect('%s?%s=%s' % tup)
        return wraps(view_func, assigned=available_attrs(view_func))(_wrapped_view)
    return decorator


def login_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME):
    """
    Decorator for views that checks that the user is logged in, redirecting
    to the log-in page if necessary.
    """
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated(),
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

