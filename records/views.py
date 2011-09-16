import json

from django.core.urlresolvers import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext, loader, Context

from models import Record
from forms import AskToShareForm

def chart(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if not request.is_ajax():
        return redirect("index")
    tooltip_template = loader.get_template("records/_chart_tooltip.html")
    chart_points = Record.objects.get_chart_data(user)
    point_data = [(cp.get_date_as_milli_from_epoch(), cp.points) for cp in chart_points]
    tooltips = [tooltip_template.render(Context({"records": cp.records, "request": request})) for cp in chart_points]
    context = {'chart_data': json.dumps({"point_data": point_data, "tooltips": tooltips})}
    return render_to_response("records/_chart.js", context, RequestContext(request), mimetype="text/javascript")

@login_required
def ask_to_share(request):
    form = AskToShareForm(request=request, data=(request.POST or None))
    profile = request.user.get_profile()

    if form.is_valid():
        is_shared = form.save(request=request)
        message_html = False
        if is_shared:
            messages.success(request, "Your activity is now being shared")
        else:
            messages.error(request, "There was a problem linking your accounts")
        if request.is_ajax():
            return render_to_response("_messages.html", {}, RequestContext(request))
        return redirect("profile_edit", user_id=request.user.id)
    template = "records/_ask_to_share.html" if request.is_ajax() else "records/ask_to_share.html"
    return render_to_response(template, locals(), RequestContext(request))

@login_required
def dont_ask_again(request):
    profile = request.user.get_profile()
    profile.ask_to_share = False
    profile.save()
    messages.success(request, "You won't be asked to share again, but the option is available \
        on your profile page if you ever change your mind", extra_tags="sticky")
    next = request.GET.get("next", None)
    return redirect(next) if next else redirect("index")
