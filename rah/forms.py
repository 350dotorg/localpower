import hashlib
from smtplib import SMTPException
from urlparse import urlparse

from django import forms
from django.contrib import auth
from django.contrib.auth import forms as auth_forms
from django.contrib.auth.models import User
from django.contrib.gis import geos
from django.core.mail import send_mail, EmailMessage
from django.core.urlresolvers import resolve, Resolver404
from django.forms import ValidationError
from django.forms.widgets import CheckboxSelectMultiple
from django.template import Context, loader

from settings import SITE_FEEDBACK_EMAIL
from rah.models import Profile, Feedback, StickerRecipient
from geo.fields import GoogleLocationField
from geo.models import Location
from geo.models import Point

from fields import Honeypot

class RegistrationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given email and password.
    """
    email = forms.EmailField(label='Email', widget=forms.TextInput(attrs={'id':'email_register'}))
    first_name = forms.CharField(min_length=2, widget=forms.TextInput(attrs={'class':'form_row_half'}))
    last_name = forms.CharField(required=False, min_length=2, widget=forms.TextInput(attrs={'class':'form_row_half form_row_half_last'}))

    password1 = forms.CharField(label='Password', min_length=5, widget=forms.PasswordInput)
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
        raise forms.ValidationError('This email address has already been registered in our system. If you have forgotten your password, please use the password reset link.')

class RegistrationProfileForm(forms.Form):
    address = GoogleLocationField(required=False,
                                  help_text="Be as specific or nonspecific as you feel like")

    def save(self):
        if self.cleaned_data['address']:
            field = self.fields['address']
            point = geos.Point((field.raw_data['latitude'], field.raw_data['longitude']))
            geom = Point.objects.create(latlon=point, 
                                        address=field.raw_data['user_input'])
            geom.save()
            self.instance.geom = geom
        profile = forms.ModelForm.save(self)
        return profile

class AuthenticationForm(forms.Form):
   """
   Base class for authenticating users. Extend this to get a form that accepts
   username/password logins.
   """
   email = forms.EmailField(label="Email")
   password = forms.CharField(label="Password", widget=forms.PasswordInput)

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
               raise forms.ValidationError("Please enter a correct email and password. Note that your password is case-sensitive.")
           elif not self.user_cache.is_active:
               raise forms.ValidationError("This account is inactive.")

       if self.request:
           if not self.request.session.test_cookie_worked():
               raise forms.ValidationError("Your Web browser doesn't appear to have cookies enabled. Cookies are required for logging in.")

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
    comment = forms.CharField(widget=forms.Textarea, required=False, label="Your Comments")
    beta_group = forms.BooleanField(help_text="""Check here if you would like to be a part
                                                of our alpha group and receive information
                                                on new features before they launch.""", label="", required=False, widget=forms.HiddenInput)
    def send(self, request):
        template = loader.get_template('rah/feedback_email.html')
        context  = { 'feedback': self.cleaned_data, 'request': request, }
        msg = EmailMessage('Feedback Form', template.render(Context(context)), None, ["SITE_FEEDBACK_EMAIL"])
        msg.content_subtype = "html"
        msg.send()

class ProfileEditForm(forms.ModelForm):
    about = forms.CharField(max_length=255, required=False, label="About you", widget=forms.Textarea)
    address = GoogleLocationField(required=False,
                                  help_text="Be as specific or nonspecific as you feel like")
    is_profile_private = forms.BooleanField(label="Make Profile Private", required=False)

    class Meta:
        model = Profile
        fields = ("address", "building_type", "about", "is_profile_private")

    def __init__(self, *args, **kwargs):
        super(ProfileEditForm, self).__init__(*args, **kwargs)
        self.fields["address"].initial = self.instance.geom.address if self.instance.geom else ""

    def save(self):
        if self.cleaned_data['address']:
            field = self.fields['address']
            point = geos.Point((field.raw_data['latitude'], field.raw_data['longitude']))
            geom, _ = Point.objects.get_or_create(latlon=point,
                                                  address=field.raw_data['user_input'])
            geom.save()
            self.instance.geom = geom
        profile = forms.ModelForm.save(self)
        return profile

class AccountForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name')

    first_name = forms.CharField(max_length=255, required=True)

    def clean_email(self):
        email = self.cleaned_data['email'].strip()
        if not len(email):
            raise ValidationError('Email cannot be blank')

        if self.instance.email == email or not User.objects.filter(email=email):
            return email
        else:
             raise ValidationError('This email address has already been registered in our system.')

class SetPasswordForm(auth_forms.SetPasswordForm):
    new_password1 = forms.CharField(min_length=5, label="New password", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="New password confirmation", widget=forms.PasswordInput)

class PasswordChangeForm(auth_forms.PasswordChangeForm):
    """
    A form that lets a user change his/her password by entering
    their old password.
    """
    old_password = forms.CharField(label="Old password", widget=forms.PasswordInput)
    new_password1 = forms.CharField(min_length=5, label="New password", widget=forms.PasswordInput)
    new_password2 = forms.CharField(label="New password confirmation", widget=forms.PasswordInput)

    def clean_old_password(self):
        return super(PasswordChangeForm, self).clean_old_password()
PasswordChangeForm.base_fields.keyOrder = ['old_password', 'new_password1', 'new_password2']

class GroupNotificationsForm(forms.Form):
    notifications = forms.ModelMultipleChoiceField(required=False, queryset=None,
            widget=forms.CheckboxSelectMultiple, help_text="By selecting a community, you have elected to \
        recieve emails for each thread posted to the discussion board.", label="Community email notifications")

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
