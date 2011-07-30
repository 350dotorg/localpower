from utils import hash_val, forbidden
from forms import GroupForm, MembershipForm, DiscussionSettingsForm, DiscussionCreateForm, DiscussionApproveForm, DiscussionRemoveForm
from models import Discussion
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import Context, loader, RequestContext

def create_discussion(user, group, data):
    request = None
    if not group.is_poster(user):
        return forbidden(request)

    disc_form = DiscussionCreateForm(data)
    if disc_form.is_valid():
        disc = Discussion.objects.create(
            subject=disc_form.cleaned_data['subject'],
            body=disc_form.cleaned_data['body'], 
            parent_id=disc_form.cleaned_data['parent_id'], 
            user=user, 
            group=group,
            is_public=not group.moderate_disc(user),
            reply_count=None if disc_form.cleaned_data['parent_id'] else 0
            )
        return disc

    return render_to_response("groups/group_disc_create.html", locals(), context_instance=RequestContext(request)) 
