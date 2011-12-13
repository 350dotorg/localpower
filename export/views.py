import csv

from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import UNUSABLE_PASSWORD
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import loader, Context, RequestContext

from rah.models import Profile
from rah.forms import RegistrationForm, RegistrationProfileForm

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
    for key in request.POST.keys():
        if key.startswith("confirm_"):
            counter = key[len("confirm_"):]
            user_data = dict([
                    (i, request.POST["%s_%s" % (i, counter)])
                    for i in "first_name last_name email geom phone language".split()
                    ])
            user_data['password1'] = "password"
            user_form = RegistrationForm(data=user_data)
            profile_form = RegistrationProfileForm(user_data)

            user_data['location'] = user_data['geom']
            del user_data['geom']

            if user_form.is_valid() and profile_form.is_valid():
                new_user = user_form.save(commit=False)
                new_user.set_unusable_password()
                if hasattr(profile_form, 'geom'):
                    setattr(new_user, 'geom', profile_form.geom)
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
            if hasattr(user, 'geom'):
                profile = user.get_profile()
                profile.geom = user.geom
                profile.save()

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
    for line in lines:
        users.append(dict(
                first_name=line[0].strip(),
                last_name=line[1].strip(),
                email=line[2].strip(),
                geom=", ".join(i.strip() for i in line[3:7] 
                               if i and i.strip()),
                phone=line[7],
                language=line[8],
                ))



    return render_to_response("export/user_import_preview.html", locals(), context_instance=RequestContext(request))
