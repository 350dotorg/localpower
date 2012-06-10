from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext, loader, Context

from django.contrib.auth.models import User
from discussions.models import Discussion, SpamFlag

@staff_member_required
def staff_review_discussions(request, user_id):
    user = get_object_or_404(User, id=user_id)
    discussions = Discussion.objects.filter(user=user).order_by("-created")

    try:
        spam_flag = SpamFlag.objects.get(user=user)
    except SpamFlag.DoesNotExist:
        spam_flag = SpamFlag(user=user, moderation_status="unreviewed")

    if request.method == "GET":
        return render_to_response("discussions/spam_moderation.html", locals(), 
                                  context_instance=RequestContext(request))
