import csv

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import UNUSABLE_PASSWORD
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import loader, Context, RequestContext

from groups.models import Group, GroupUsers
from rah.models import Profile
from rah.forms import RegistrationForm, ProfileEditForm

from forms import UserExportForm

# writer.writerow(['="%s"' % s if s and excel_friendly else s for s in row])

@staff_member_required
def user_export(request):
    form = UserExportForm(request.POST or None)
    if form.is_valid():
        response = HttpResponse(mimetype='text/csv')
        response['Content-Disposition'] = 'attachment; filename=user_activity.csv'
        writer = csv.writer(response, dialect='excel')
        form.save_to_writer(writer)
        return response
    return render_to_response("export/user_export.html", locals(), context_instance=RequestContext(request))

@staff_member_required
def _import_users(request):
    users = []
    has_errors = False

    group = None
    if "group" in request.POST and request.POST['group']:
        try:
            group = Group.objects.get(slug=request.POST['group'])
        except Group.DoesNotExist:
            messages.error(request, "Group '%s' does not exist.")
        
    for key in request.POST.keys():
        if key.startswith("confirm_"):
            counter = key[len("confirm_"):]
            user_data = dict([
                    (i, request.POST["%s_%s" % (i, counter)])
                    for i in "first_name last_name email geom phone language".split()
                    ])
            user_data['password1'] = "password"
            user_form = RegistrationForm(data=user_data)
            profile_form = ProfileEditForm(user_data)

            if user_form.is_valid() and profile_form.is_valid():
                new_user = user_form.save(commit=False)
                new_user.set_unusable_password()
                for attr in ("geom", "language", "phone"):
                    if attr in profile_form.cleaned_data and profile_form.cleaned_data[attr]:
                        setattr(new_user, attr, profile_form.cleaned_data[attr])
                users.append(new_user)
            else:
                has_errors = True
                user_data['errors'] = errors = {}
                errors.update(user_form.errors)
                errors.update(profile_form.errors)
                users.append(user_data)

    if has_errors:
        transaction.rollback()
    else:
        for user in users:
            user.save()
            profile = user.get_profile()
            for attr in ("geom", "language", "phone"):
                if hasattr(user, attr):
                    setattr(profile, attr, getattr(user, attr))
            profile.save()

            if group is not None:
                GroupUsers.objects.create(group=group, user=user, is_manager=False)
                message = ("Added user: <a href='/admin/auth/user/%s/'>%s</a> "
                           "to group <a href='/admin/groups/group/%s/'>%s</a>" % (
                        user.pk, user.get_full_name(), group.pk, group.name))
            else:
                message = ("Added user: <a href='/admin/auth/user/%s/'>%s</a> " % (
                        user.pk, user.get_full_name(), group.pk, group.name))

            messages.success(request, message)

        return HttpResponseRedirect(".")

    groups = Group.objects.all()
    return render_to_response("export/user_import_preview.html", locals(), context_instance=RequestContext(request))
        
@staff_member_required
def user_import(request):
    if request.method == "GET":
        return render_to_response("export/user_import.html", locals(), context_instance=RequestContext(request))

    if request.POST.get("confirm", None) == "true":
        return _import_users(request)

    users = request.FILES['users']

    reader = csv.reader(users)
    lines = [i for i in reader]
    if lines[0][0].strip().lower() == "first name":
        lines.pop(0)
    
    users = []
    lineno = 0
    for line in lines:
        lineno += 1
        try:
            users.append(dict(
                    first_name=line[0].strip(),
                    last_name=line[1].strip(),
                    email=line[2].strip(),
                    geom=", ".join(i.strip() for i in line[3:7] 
                                   if i and i.strip()),
                    phone=line[7],
                    language=line[8],
                    ))
        except IndexError:
            messages.error(request, 'Error reading line %s of the spreadsheet.' % lineno)
            return HttpResponseRedirect(".")

    groups = Group.objects.all()

    return render_to_response("export/user_import_preview.html", locals(), context_instance=RequestContext(request))
