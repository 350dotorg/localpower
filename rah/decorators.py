import sys

try:
    from functools import update_wrapper, wraps
except ImportError:
    from django.utils.functional import update_wrapper, wraps  # Python 2.3, 2.4 fallback.

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.http import HttpResponseRedirect
from django.utils.http import urlquote

LRSP = "login_required_saved_POST"

def login_required_save_POST(function, redirect_field_name=REDIRECT_FIELD_NAME):
    def decorator(request, *args, **kwargs):
        if request.user.is_authenticated():
            return function(request, *args, **kwargs)
        if request.method == "POST":
            if not LRSP in request.session:
                request.session[LRSP] = []
            queue = request.session[LRSP]
            queue.append((function.__module__, function.__name__, request.POST, args, kwargs))
            request.session[LRSP] = queue
        path = urlquote(request.get_full_path())
        tup = settings.LOGIN_URL, redirect_field_name, path
        return HttpResponseRedirect('%s?%s=%s' % tup)
    return decorator

def save_queued_POST(request):
    if request.user.is_authenticated and LRSP in request.session:
        queue = request.session[LRSP]
        del request.session[LRSP]
        data = request.POST.copy()
        method = request.method
        for func_mod, func_name, post, s_args, s_kwargs in queue:
            top = __import__(func_mod)
            module = sys.modules[func_mod]
            request.POST = post
            request.method = "POST"
            getattr(module, func_name)(request, *s_args, **s_kwargs)
        request.POST = data
        request.method = method
