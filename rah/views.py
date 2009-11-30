from django import forms
from django.http import HttpResponseRedirect
from django.contrib import auth
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import get_object_or_404
from rah.models import Action, ActionCat

def index(request):
    """
    Home Page
    """
    # If the user is not logged in, show them the logged out homepage and bail
    if not request.user.is_authenticated():
        return render_to_response('rah/home_logged_out.html')
    
    # Get a list of relevant actions
    
    # Get a list of completed actions
    
    # Get a list of the user's earned points
    
    
    
    return render_to_response('rah/home_logged_in.html', {}, context_instance=RequestContext(request))

@csrf_protect
def register(request):
    from www.rah.forms import RegistrationForm
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            new_user = form.save()
            user = auth.authenticate(username=form.cleaned_data["username"], password=form.cleaned_data["password1"])
            auth.login(request, user)
            return HttpResponseRedirect("/")
    else:
        form = RegistrationForm()
    return render_to_response("registration/register.html", {
        'form': form,
    }, context_instance=RequestContext(request))

def actionBrowse(request):
    """Browse all actions by category"""
    cats = ActionCat.objects.all()
    return render_to_response('rah/actionBrowse.html', {'cats':cats})

def actionCat(request, catSlug):
    """View an action category page with links to actions in that category"""
    cat     = get_object_or_404(ActionCat, slug=catSlug)
    actions = Action.objects.filter(category=cat.id)
    return render_to_response('rah/actionCat.html', {'cat':cat, 'actions':actions})

def actionDetail(request, catSlug, actionSlug):
    """Detail page for an action"""
    action = get_object_or_404(Action, slug=actionSlug)
    cat    = ActionCat.objects.get(slug=catSlug)
    return render_to_response('rah/actionDetail.html', {'action':action, 'cat':cat})