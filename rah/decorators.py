import sys

try:
    from functools import update_wrapper, wraps
except ImportError:
    from django.utils.functional import update_wrapper, wraps  # Python 2.3, 2.4 fallback.

from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.utils.http import urlquote
from django.utils.translation import ugettext_lazy as _

LRSP = "login_required_saved_POST"

def login_required_save_POST(function, redirect_field_name=REDIRECT_FIELD_NAME,
                             message_string=_("You need to create an account first. "
                                              "Don't worry -- it only takes 15 seconds!")):
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
        messages.info(request, message_string)        
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

def login_required_except_GET_save_POST(
    function, redirect_field_name=REDIRECT_FIELD_NAME,
    message_string=_("You need to create an account first. "
                     "Don't worry -- it only takes 15 seconds!")):
    def decorator(request, *args, **kwargs):
        if request.user.is_authenticated():
            return function(request, *args, **kwargs)
        if request.method == "GET":
            return function(request, *args, **kwargs)
        if request.method == "POST":
            if not LRSP in request.session:
                request.session[LRSP] = []
            queue = request.session[LRSP]
            queue.append((function.__module__, function.__name__, request.POST, args, kwargs))
            request.session[LRSP] = queue
        path = urlquote(request.get_full_path())
        tup = settings.LOGIN_URL, redirect_field_name, path
        messages.info(request, message_string)
        return HttpResponseRedirect('%s?%s=%s' % tup)
    return decorator
