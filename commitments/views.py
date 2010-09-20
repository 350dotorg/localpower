from django.contrib.auth.decorators import login_required
from django.template import RequestContext
from django.shortcuts import render_to_response

@login_required
def commitment_show(request):
    return render_to_response('commitments/show.html', {}, context_instance=RequestContext(request))
    
@login_required
def commitment_card_create(request):
    """Create a new commitment card"""
    return render_to_response('commitments/card.html', {}, context_instance=RequestContext(request))

def commitment_card(request, contributor):
    """Display an existing commitment card"""
    return render_to_response('commitments/card.html', {}, context_instance=RequestContext(request))