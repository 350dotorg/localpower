import csv

from django.contrib import admin
from django.http import HttpResponse
from django.template.defaultfilters import slugify
from django.utils.encoding import smart_str

def admin_list_export(modeladmin, request, queryset):
    model = queryset.model
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % slugify(model.__name__)
    writer = csv.writer(response)
    model_admin = admin.site._registry[model]
    list_display = getattr(model_admin, 'csv_export_fields', None) or \
        model_admin.list_display
    # Write headers to CSV file
    if list_display and len(list_display) > 0:
        if list_display[0] == "action_checkbox":
            headers = list_display[1:]
        else:
            headers = list_display
    else:
        headers = []
        for field in model._meta.fields:
            headers.append(field.name)
    writer.writerow(headers)
    # Write data to CSV file
    for obj in queryset:
        row = []
        for field in headers:
            if field in headers:
                try:
                    val = getattr(admin.site._registry[model], field)
                    if callable(val):
                        try:
                            val = val(obj)
                        except TypeError:
                            val = val()
                except AttributeError:
                    if "__" in field:
                        vals = field.split("__")
                        val = obj
                        while vals:
                            val = getattr(val, vals.pop(0))
                    else:
                        val = getattr(obj, field)
                    if callable(val):
                        val = val()
                row.append(smart_str(val or ''))
        writer.writerow(row)
    # Return CSV file to browser as download
    return response
