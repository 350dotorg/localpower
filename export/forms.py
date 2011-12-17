from django.contrib.admin import widgets

from rah.models import Profile
from commitments.models import Contributor
from events.models import Guest

from django import forms

class UserExportForm(forms.Form):
    date_filter_start = forms.DateField(required=False, label="Filter activity before",
        widget=widgets.AdminDateWidget())
    date_filter_end = forms.DateField(required=False, label="Filter activity after",
        widget=widgets.AdminDateWidget())
    filter_inactive = forms.BooleanField(required=False, label="Filter users with no activity")
    include_guests = forms.BooleanField(required=False, label="Include contributors who have entered commitments")
    excel_friendly = forms.BooleanField(required=False)

    def save_to_writer(self, writer):
        date_start = self.cleaned_data["date_filter_start"] if "date_filter_start" in self.cleaned_data else None
        date_end = self.cleaned_data["date_filter_end"] if "date_filter_end" in self.cleaned_data else None
        queryset = Profile.objects.user_engagement(date_start=date_start, date_end=date_end)
        if self.cleaned_data["include_guests"]:
            guest_queryset = Contributor.objects.contirbutor_engagment(date_start=date_start, date_end=date_end)
            queryset = queryset + guest_queryset[1:]
        for row in queryset:
            if not self.cleaned_data["filter_inactive"] or any(row[8:]):
                writer.writerow(['="%s"' % s if s and self.cleaned_data["excel_friendly"] else s for s in row])


## This code can be cleaned up if https://code.djangoproject.com/ticket/17431 is accepted and merged to Django core
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.contrib.sites.models import get_current_site
from django.template import Context, loader
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.http import int_to_base36
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, PasswordChangeForm

class AccountConfirmForm(PasswordResetForm):

    def save(self, domain_override=None, email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator, request=None):
        """
        Generates a one-use only link for resetting password and sends to the user
        """
        from django.core.mail import send_mail, EmailMessage
        for user in self.users_cache:
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            t = loader.get_template(email_template_name)
            c = {
                'email': user.email,
                'domain': domain,
                'site_name': site_name,
                'uid': int_to_base36(user.id),
                'user': user,
                'token': token_generator.make_token(user),
                'protocol': use_https and 'https' or 'http',
                }
            msg = EmailMessage("Connect with your local 350 groups",
                               t.render(Context(c)), None, [user.email])
            msg.content_subtype = "html"
            msg.send()
