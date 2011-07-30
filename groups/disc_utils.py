def create_discussion(user, group, data):
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
        return_to = disc_form.cleaned_data['parent_id'] if disc_form.cleaned_data['parent_id'] else disc.id
        return redirect("group_disc_detail", group_slug=group.slug, disc_id=return_to)

    return render_to_response("groups/group_disc_create.html", locals(), context_instance=RequestContext(request)) 
