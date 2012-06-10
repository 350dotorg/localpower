from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext, loader, Context
from django.utils.translation import ugettext_lazy as _

from django.contrib.auth.models import User
from discussions.models import Discussion, SpamFlag

@staff_member_required
def staff_review_discussions(request, user_id, moderation_status="unreviewed"):
    user = get_object_or_404(User, id=user_id)
    discussions = Discussion.objects.filter(user=user).order_by("-created")

    try:
        spam_flag = SpamFlag.objects.get(user=user)
    except SpamFlag.DoesNotExist:
        spam_flag = SpamFlag(user=user, moderation_status="unreviewed")

    if request.method == "GET":
        if moderation_status != "unreviewed":
            return redirect("staff_review_discussions", user_id=user_id)
        return render_to_response("discussions/spam_moderation.html", locals(), 
                                  context_instance=RequestContext(request))
    assert moderation_status in ("unreviewed", "spam", "not_spam")
    spam_flag.moderation_status = moderation_status
    spam_flag.save()
    messages.success(request, 
                     _("User %(user)s has been marked as %(moderation_status)s") % {
            'user': user.get_full_name(), 'moderation_status': spam_flag.status_str()})
    return redirect("staff_review_discussions", user_id=user_id)

