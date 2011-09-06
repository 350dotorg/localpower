import hashlib
from smtplib import SMTPException
from urlparse import urlparse

from django import forms
from django.contrib import auth
from django.contrib.auth import forms as auth_forms
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.core.mail import send_mail, EmailMessage
from django.core.urlresolvers import resolve, Resolver404
from django.forms.widgets import CheckboxSelectMultiple
from django.template import Context, loader
from django.utils.translation import ugettext_lazy as _

from settings import SITE_FEEDBACK_EMAIL
from rah.models import Profile, Feedback, StickerRecipient
from geo.models import Location

from fields import Honeypot

class RegistrationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given email and password.
    """
    email = forms.EmailField(label='Email', widget=forms.TextInput(attrs={'id':'email_register'}))
    first_name = forms.CharField(min_length=2, widget=forms.TextInput(attrs={'class':'form_row_half'}))
    last_name = forms.CharField(required=False, min_length=2, widget=forms.TextInput(attrs={'class':'form_row_half form_row_half_last'}))

    password1 = forms.CharField(label=_('Password'), min_length=5, widget=forms.PasswordInput)
    honeypot = Honeypot()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email",)

    def clean(self):
        self.instance.username = hashlib.md5(self.cleaned_data.get("email", "")).hexdigest()[:30]
        self.instance.set_password(self.cleaned_data.get("password1", auth.models.UNUSABLE_PASSWORD))
        super(RegistrationForm, self).clean()
        return self.cleaned_data

    def clean_email(self):
        email = self.cleaned_data['email']
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            return email
        raise forms.ValidationError(_('This email address has already been registered in our system. If you have forgotten your password, please use the password reset link.'))

class RegistrationProfileForm(forms.Form):
    zipcode = forms.CharField(max_length=5, required=False, help_text=_("Leave blank if you don't have a US zipcode"), widget=forms.TextInput())

    def clean_zipcode(self):
        data = self.cleaned_data['zipcode'].strip()
        if data:
            if len(data) <> 5:
                raise forms.ValidationError(_("Please enter a 5 digit zipcode"))
            try:
                self.location = Location.objects.get(zipcode=data)
            except Location.DoesNotExist, e:
                raise forms.ValidationError(_("Zipcode is invalid"))
        return data

class AuthenticationForm(forms.Form):
   """
   Base class for authenticating users. Extend this to get a form that accepts
   username/password logins.
   """
   email = forms.EmailField(label=_("Email"))
   password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

   def __init__(self, request=None, *args, **kwargs):
       """
       If request is passed in, the form will validate that cookies are
       enabled. Note that the request (a HttpRequest object) must have set a
       cookie with the key TEST_COOKIE_NAME and value TEST_COOKIE_VALUE before
       running this validation.
       """
       self.request = request
       self.user_cache = None
       super(AuthenticationForm, self).__init__(*args, **kwargs)

   def clean(self):
       email = self.cleaned_data.get('email')
       password = self.cleaned_data.get('password')

       if email and password:
           self.user_cache = auth.authenticate(username=email, password=password)
           if self.user_cache is None:
               raise forms.ValidationError(_("Please enter a correct email and password. Note that your password is case-sensitive."))
           elif not self.user_cache.is_active:
               raise forms.ValidationError(_("This account is inactive."))

       if self.request:
           if not self.request.session.test_cookie_worked():
               raise forms.ValidationError(_("Your Web browser doesn't appear to have cookies enabled. Cookies are required for logging in."))

       return self.cleaned_data

   def get_user_id(self):
       if self.user_cache:
           return self.user_cache.id
       return None

   def get_user(self):
       return self.user_cache

class FeedbackForm(forms.ModelForm):
    class Meta:
        model = Feedback
        fields = ("comment", "beta_group", "url")

    url = forms.CharField(widget=forms.HiddenInput, required=False)
    comment = forms.CharField(widget=forms.Textarea, required=False, label=_("Your Comments"))
    beta_group = forms.BooleanField(help_text=_("Check here if you would like to be a part"
                                                "of our alpha group and receive information"
                                                "on new features before they launch."),
                                    label="", required=False, widget=forms.HiddenInput)
    def send(self, request):
        template = loader.get_template('rah/feedback_email.html')
        context  = { 'feedback': self.cleaned_data, 'request': request, }
        msg = EmailMessage('Feedback Form', template.render(Context(context)), None, ["SITE_FEEDBACK_EMAIL"])
        msg.content_subtype = "html"
        msg.send()

class ProfileEditForm(forms.ModelForm):
    about = forms.CharField(max_length=255, required=False, label=_("About you"), widget=forms.Textarea)
    zipcode = forms.CharField(max_length=5, required=False)
    is_profile_private = forms.BooleanField(label=_("Make Profile Private"), required=False)

    class Meta:
        model = Profile
        fields = ("zipcode", "about", "is_profile_private")

    def __init__(self, *args, **kwargs):
        super(ProfileEditForm, self).__init__(*args, **kwargs)
        self.fields["zipcode"].initial = self.instance.location.zipcode if self.instance.location else ""

    def clean_zipcode(self):
        data = self.cleaned_data['zipcode'].strip()
        if not len(data):
            self.instance.location = None
            return
        if len(data) <> 5:
            raise forms.ValidationError(_("Please enter a 5 digit zipcode"))
        try:
            self.instance.location = Location.objects.get(zipcode=data)
        except Location.DoesNotExist, e:
            raise forms.ValidationError(_("Zipcode is invalid"))

class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

    first_name = forms.CharField(max_length=255, required=True)

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if not len(email):
            raise ValidationError(_('Email cannot be blank'))

        if self.instance.email == email or not User.objects.filter(email=email):
            return email
        else:
             raise ValidationError(_('This email address has already been registered in our system.'))

class SetPasswordForm(auth_forms.SetPasswordForm):
    new_password1 = forms.CharField(min_length=5, label=_("New password"), widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=forms.PasswordInput)

class PasswordChangeForm(auth_forms.PasswordChangeForm):
    """
    A form that lets a user change his/her password by entering
    their old password.
    """
    old_password = forms.CharField(label="Old password", widget=forms.PasswordInput)
    new_password1 = forms.CharField(min_length=5, label=_("New password"), widget=forms.PasswordInput)
    new_password2 = forms.CharField(label=_("New password confirmation"), widget=forms.PasswordInput)

    def clean_old_password(self):
        return super(PasswordChangeForm, self).clean_old_password()
PasswordChangeForm.base_fields.keyOrder = ['old_password', 'new_password1', 'new_password2']

class GroupNotificationsForm(forms.Form):
    notifications = forms.ModelMultipleChoiceField(
        required=False, queryset=None,
        widget=forms.CheckboxSelectMultiple, 
        help_text=_("By selecting a community, you have elected to "
                    "recieve emails for each thread posted to the discussion board."), 
        label=_("Community email notifications"))

    def __init__(self, user, *args, **kwargs):
        from groups.models import Group
        super(GroupNotificationsForm, self).__init__(*args, **kwargs)
        self.user = user
        self.groups = Group.objects.filter(users=user, is_geo_group=False)
        self.fields["notifications"].queryset = self.groups
        self.not_blacklisted = [g.pk for g in Group.objects.groups_not_blacklisted_by_user(user)]
        self.fields["notifications"].initial = self.not_blacklisted

    def save(self):
        from groups.models import DiscussionBlacklist
        notifications = self.cleaned_data["notifications"]
        for group in self.groups:
            if not group in notifications and group.pk in self.not_blacklisted:
                DiscussionBlacklist.objects.create(user=self.user, group=group)
            if group in notifications and group.pk not in self.not_blacklisted:
                DiscussionBlacklist.objects.get(user=self.user, group=group).delete()

class StickerRecipientForm(forms.ModelForm):
    honeypot = Honeypot()

    class Meta:
        model = StickerRecipient
        exclude = ("user",)
