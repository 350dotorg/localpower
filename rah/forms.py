import datetime
import hashlib
from smtplib import SMTPException
from urlparse import urlparse
from PIL.Image import open as pil_open

from django import forms
from django.conf import settings
from django.contrib import auth
from django.contrib.auth import forms as auth_forms
from django.contrib.auth.models import User
from django.forms import ValidationError
from django.core.mail import send_mail, EmailMessage
from django.core.urlresolvers import resolve, Resolver404
from django.forms.widgets import CheckboxSelectMultiple
from django.template import Context, loader
from django.utils.translation import ugettext_lazy as _
import time

from settings import SITE_FEEDBACK_EMAIL
from rah.models import Profile, Feedback, StickerRecipient

from geo.fields import GoogleLocationField

from fields import Honeypot

class RegistrationForm(forms.ModelForm):
    """
    A form that creates a user, with no privileges, from the given email and password.
    """
    email = forms.EmailField(label=_('Email address'), widget=forms.TextInput(attrs={'id':'email_register'}))
    first_name = forms.CharField(label=_("First Name"), min_length=1, widget=forms.TextInput(attrs={'class':'form_row_half'}))
    last_name = forms.CharField(label=_("Last Name"), required=False, min_length=1, widget=forms.TextInput(attrs={'class':'form_row_half form_row_half_last'}))

    password1 = forms.CharField(
        label=_('Password'), min_length=5, widget=forms.PasswordInput,
        help_text=_("Your password must be at least five digits"),)
    honeypot = Honeypot()

    class Meta:
        model = User
        fields = ("first_name", "last_name", "email",)

    def clean(self):
        user_hash = hashlib.md5("%s\0%s" % (
                self.cleaned_data.get("email", ""),
                time.time())).hexdigest()
        self.instance.username = user_hash[:30]
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
    geom = GoogleLocationField(
        label=_("Location"),
        help_text=_("(Optional) Be as specific as you're comfortable sharing"),
        required=False)

    def clean(self):
        data = self.cleaned_data.get("geom")
        if data:
            self.geom = data
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
        msg = EmailMessage('Feedback Form', template.render(Context(context)), None, 
                           [SITE_FEEDBACK_EMAIL])
        msg.content_subtype = "html"
        msg.send()

class ProfileEditForm(forms.ModelForm):
    IMAGE_FORMATS = {"PNG": "png", "JPEG": "jpeg", "GIF": "gif"}

    about = forms.CharField(required=False, label=_("About you"), widget=forms.Textarea)
    geom = GoogleLocationField(
        label=_("Location"),
        help_text=_("(Optional) Be as specific as you're comfortable sharing"),
        required=False)
    is_profile_private = forms.BooleanField(label=_("Make Profile Private"), required=False)
    image = forms.FileField(label=_("Upload a profile image"),
                            help_text=_("(Optional) You can upload png, jpg or gif files up to 512K"),
                            required=False)

    phone = forms.CharField(max_length=30, required=False,
                            widget=forms.HiddenInput)
    language = forms.CharField(max_length=10, required=True, label=_("Language"),
                               widget=forms.Select(choices=settings.LANGUAGES))


    class Meta:
        model = Profile
        fields = ("language", "about", "is_profile_private", "image", "phone")

    def __init__(self, *args, **kwargs):
        super(ProfileEditForm, self).__init__(*args, **kwargs)
        ## move geom/streetaddress to top of form
        keyOrder = self.fields.keyOrder
        keyOrder.remove("geom")
        keyOrder.insert(0, "geom")
        self.fields["geom"].initial = ""
        if self.instance and self.instance.geom:
            self.fields["geom"].initial = self.instance.geom.raw_address

        self.fields["phone"].initial = ""
        if self.instance and self.instance.phone:
            self.fields["phone"].initial = self.instance.phone

        self.fields["language"].initial = ""
        if self.instance and self.instance.language:
            self.fields["language"].initial = self.instance.language

    def clean_image(self):
        data = self.cleaned_data["image"]
        if data:
            if data.size > 4194304:
                raise forms.ValidationError(_("Profile images cannot be larger than 512K"))
            self.image_format = pil_open(data.file).format
            if not self.image_format in ProfileEditForm.IMAGE_FORMATS:
                raise forms.ValidationError(_("Images cannot be of type %(type)s") % {
                        'type': data.content_type})
        return data

    def save(self, *args, **kwargs):
        if self.cleaned_data.get("geom"):
            point = self.cleaned_data["geom"]
            self.instance.geom = point
        elif self.data.get("geom") is not None and self.data.get("geom", "").strip() == "":
            self.instance.geom = None

        if self.cleaned_data.get("phone"):
            self.instance.phone = self.cleaned_data['phone']
        if self.cleaned_data.get("language"):
            self.instance.language = self.cleaned_data['language']

        profile = super(ProfileEditForm, self).save(*args, **kwargs)

        current_image = self.cleaned_data["image"]
        if current_image and current_image != profile.image.field.default:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            image_name = "%s_%s.%s" % (profile.pk, timestamp, ProfileEditForm.IMAGE_FORMATS[self.image_format])
            original_file = profile.image.file
            original_name = original_file.name
            profile.image.save(image_name, original_file, save=True)
            profile.image.storage.delete(original_name)

        return profile

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
        self.groups = Group.objects.filter(users=user)
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
