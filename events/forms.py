import datetime
import hashlib
import re
import urllib2
import json

from django import forms
from django.forms import formsets
from django.conf import settings
from django.contrib import auth
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.core.mail import EmailMessage
from django.template import Context, loader
from django.utils.dateformat import format

from geo.models import Location
from invite.models import Invitation
from invite.forms import InviteForm
from invite.fields import MultiEmailField
from messaging.models import Stream
from commitments.models import Survey, Commitment, Contributor

from models import Event, Guest, rsvp_recieved, GroupAssociationRequest
from widgets import SelectTimeWidget

def _durations():
    durations = []
    hours = range(1,4)
    for hour in hours:
        for minute in [0,15,30,45]:
            durations.append(("%s" % (hour*60+minute), "%sh %0.2dm" % (hour, minute)))
    next_hour = hours[-1] + 1
    durations.append(("%s" % (next_hour*60), "%sh 00m" % next_hour))
    return durations
DURATIONS = _durations()

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ("title", "where", "details", "when", "start", "duration", "is_private", "lat", "lon", "groups")
        widgets = {
            "when": forms.DateInput(format="%m/%d/%Y", attrs={"class": "datepicker future_date_warning"}),
            "start": SelectTimeWidget(minute_step=15, twelve_hr=True, use_seconds=False),
            "duration": forms.Select(choices=[("", "---")]+DURATIONS),
            "lat": forms.HiddenInput(),
            "lon": forms.HiddenInput(),
            "groups": forms.CheckboxSelectMultiple(),
        }

    def __init__(self, user, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.fields["start"].initial = datetime.time(18,0)
        self.user = user
        groups = self.fields["groups"]
        groups.queryset = groups.queryset.filter(groupusers__user=user)
        if not groups.queryset:
            groups.help_text = "You need to be a member of a team first"
        else:
            groups.help_text = None

    def clean_groups(self):
        data = self.cleaned_data["groups"]
        approved_groups, self.requested_groups = [], []
        for g in data:
            if g.is_user_manager(self.user) or GroupAssociationRequest.objects.filter(
                event=self.instance, group=g, approved=True).exists():
                approved_groups.append(g)
            else:
                self.requested_groups.append(g)
        return approved_groups

    def clean(self):
        if "where" in self.cleaned_data:
            error = False
            raw_address = self.cleaned_data["where"]
            url = "http://maps.googleapis.com/maps/api/geocode/json?sensor=false"
            url += "&address=%s" % urllib2.quote(raw_address)

            try:
                resp = json.load(urllib2.urlopen(url))
            except:
                pass
            else:
                if resp['status'] == 'OK':
                    self.cleaned_data['lat'] = resp['results'][0]['geometry']['location']['lat']
                    self.cleaned_data['lon'] = resp['results'][0]['geometry']['location']['lng']
                    self.cleaned_data['where'] = resp['results'][0]['formatted_address']

                    # look for a postal_code and then lookup the location
                    for component in resp['results'][0]['address_components']:
                        if "postal_code" in component['types']:
                            zipcode = component['short_name']
                            break
                    try:
                        self.cleaned_data['location'] = Location.objects.get(zipcode=zipcode)
                    except:
                        error = True
                else:
                    error = True
            if error:
                del self.cleaned_data['where']
                self._errors['where'] = self.error_class(
                    ['We couldn\'t locate this address on our map.'])
        return self.cleaned_data

    def save(self, *args, **kwargs):
        self.instance.creator = self.user
        self.instance.location = self.cleaned_data["location"]
        event = super(EventForm, self).save(*args, **kwargs)
        for g in self.requested_groups:
            request, created = GroupAssociationRequest.objects.get_or_create(
                event=event, group=g)
            # TODO: notify user of groups requested
        return event

class GuestInviteForm(InviteForm):
    emails = MultiEmailField(label="Email addresses", required=True,
        widget=forms.Textarea(attrs={"rows": 5}),
        help_text="For multiple email addresses, seperate them with a comma")
    note = forms.CharField(label="Personal note (optional)", required=False,
        widget=forms.Textarea(attrs={"rows": 5}))
    rsvp_notification = forms.BooleanField(required=False, label="Email me when people RSVP")
    copy_me = forms.BooleanField(required=False, label="Send me a copy of the invitation")

    def save(self, *args, **kwargs):
        guest_invites = []
        event = self.instance.content_object
        rsvp_notification = self.cleaned_data["rsvp_notification"]
        for email in self.cleaned_data["emails"]:
            contributor, created = Contributor.objects.get_or_create(email=email)
            guest, created = Guest.objects.get_or_create(event=event, contributor=contributor,
                defaults={"invited":datetime.date.today()})
            guest.notify_on_rsvp = rsvp_notification
            guest.save()
            guest_invites.append(guest)
        if self.cleaned_data["copy_me"]:
            self.cleaned_data["emails"].append(self.instance.user.email)
        super(GuestInviteForm, self).save(*args, **kwargs)
        return guest_invites

class GuestAddForm(forms.ModelForm):
    first_name = forms.CharField(required=True, max_length=50)
    last_name = forms.CharField(required=False, max_length=50)
    email = forms.EmailField(required=False, max_length=75)
    phone = forms.CharField(required=False, max_length=12)
    zipcode = forms.CharField(required=False, max_length=5, min_length=5)
    rsvp_status = forms.ChoiceField(choices=Guest.RSVP_STATUSES,
        label="Is this person planning on attending?", widget=forms.RadioSelect)

    class Meta:
        model = Guest
        fields = ("first_name", "last_name", "email", "phone", "zipcode", "rsvp_status",)
        widgets = {
            "rsvp_status": forms.RadioSelect,
        }

    def clean_email(self):
        email = self.cleaned_data["email"]
        if email:
            return email
        return None

    def clean_zipcode(self):
        data = self.cleaned_data["zipcode"]
        if data:
            try:
                self.location = Location.objects.get(zipcode=data)
            except Location.DoesNotExist:
                raise forms.ValidationError("Invalid zipcode %s" % data)
        else:
            self.location = None
        return data

    def save(self, *args, **kwargs):
        email = self.cleaned_data["email"]
        contributor = Contributor(email=email)
        if email:
            try:
                contributor = Contributor.objects.get(email=self.cleaned_data["email"])
            except Contributor.DoesNotExist:
                pass
        contributor.first_name = self.cleaned_data["first_name"]
        contributor.last_name = self.cleaned_data["last_name"]
        contributor.phone = self.cleaned_data["phone"]
        contributor.location = self.location
        contributor.save()
        try:
            guest = Guest.objects.get(event=self.instance.event, contributor=contributor)
            self.instance.pk = guest.pk
            self.instance.created = guest.created
        except Guest.DoesNotExist:
            pass
        self.instance.contributor = contributor
        self.instance.added = datetime.date.today()
        return super(GuestAddForm, self).save(*args, **kwargs)

class GuestListForm(forms.Form):
    from guest_actions import attending, not_attending, announcement_email, invitation_email, \
        reminder_email, remove, make_host, unmake_host
    EMAIL_ACTIONS = {
        # "1_SA": ("Mark as Attending", attending),
        # "2_SN": ("Mark as Not Attending", not_attending),
        "3_EA": ("Send Announcement Email", announcement_email),
        "4_EI": ("Send Invitation Email", invitation_email),
        "5_ER": ("Send Reminder Email", reminder_email),
    }
    MISC_ACTIONS = {
        "6_MR": ("Remove from guest list", remove),
        "7_MH": ("Make a guest a host", make_host),
        "8_MU": ("Remove host privledges", unmake_host),
    }
    ACTIONS = dict(EMAIL_ACTIONS.items() + MISC_ACTIONS.items())

    ACTION_CHOICES = [("", "- Select One -")] + \
        sorted([(k, v[0]) for k,v in EMAIL_ACTIONS.iteritems()]) + \
        [(" ", "------------------")] + \
        sorted([(k, v[0]) for k,v in MISC_ACTIONS.iteritems()])

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    guests = forms.ModelMultipleChoiceField(queryset=None, widget=forms.CheckboxSelectMultiple)

    def __init__(self, event, *args, **kwargs):
        super(GuestListForm, self).__init__(*args, **kwargs)
        self.event = event
        self.fields["guests"].queryset = event.guest_set.all()

    def clean(self):
        action = self.cleaned_data.get("action", "")
        # Check to see if the action is of type Email
        if re.search("^\d+_E", action):
            # Action of type Email can only be performed on guests with emails
            if any([not g.contributor.email for g in self.cleaned_data["guests"]]):
                raise forms.ValidationError("All guests must have an email address")
        if action in ["6_MR", "8_MU"]:
            guests = self.cleaned_data["guests"]
            # get all of the guests not selected
            not_selected_guests = [g for g in self.event.guest_set.all() if not (g in guests)]
            if not any([g.is_host for g in not_selected_guests]):
                raise forms.ValidationError("You must leave at least one host for the event")
        return self.cleaned_data

    def save(self, *args, **kwargs):
        action = GuestListForm.ACTIONS[self.cleaned_data["action"]][1]
        return action(self.cleaned_data["guests"])

class GuestEditForm(forms.ModelForm):
    name = forms.CharField(required=False, max_length=100)
    email = forms.EmailField(required=False, max_length=75)
    phone = forms.CharField(required=False, max_length=12)
    zipcode = forms.CharField(required=False, max_length=5)

    class Meta:
        model = Guest

    def clean_email(self):
        data = self.cleaned_data["email"]
        if data and Guest.objects.filter(event=self.instance.event, contributor__email=data).exclude(
            id=self.instance.id).exists():
            raise forms.ValidationError("A Guest with this email address already exists.")
        return data

    def clean_zipcode(self):
        data = self.cleaned_data["zipcode"]
        if data:
            try:
                self.cleaned_data["location"] = Location.objects.get(zipcode=data)
            except Location.DoesNotExist:
                raise forms.ValidationError("Invalid zipcode %s" % data)
        return data

    def save(self, *args, **kwargs):
        name = self.cleaned_data.get("name", None)
        if name:
            self.instance.contributor.name = name
        email = self.cleaned_data.get("email", None)
        if email:
            self.instance.contributor.email = email
        phone = self.cleaned_data.get("phone", None)
        if phone:
            self.instance.contributor.phone = phone
        zipcode = self.cleaned_data.get("zipcode", None)
        if zipcode:
            self.instance.contributor.zipcode = zipcode
        return super(GuestEditForm, self).save(*args, **kwargs)

class HostForm(forms.Form):
    guests = forms.ModelMultipleChoiceField(queryset=None, widget=forms.CheckboxSelectMultiple)

    def __init__(self, event, *args, **kwargs):
        super(HostForm, self).__init__(*args, **kwargs)
        self.event = event
        self.fields["guests"].queryset = event.guest_set
        self.fields["guests"].initial = [g.id for g in event.hosts()]

    def save(self):
        self.cleaned_data["guests"].update(is_host=True)

class RsvpForm(forms.ModelForm):
    rsvp_status = forms.ChoiceField(choices=Guest.RSVP_STATUSES, widget=forms.RadioSelect)
    token = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model = Guest
        fields = ("rsvp_status", "comments", "token",)
        widgets = {
            "comments": forms.Textarea(attrs={"cols": "17", "rows": "3"})
        }

    def clean_token(self):
        data = self.cleaned_data["token"]
        event = self.instance.event
        if event.is_private and not event.is_token_valid(data):
            return forms.ValidationError("Invalid token")
        return data

    def store(self, request):
        guest = self.instance
        guest.event.save_guest_in_session(request=request, guest=guest)
        return guest

    def save(self, *args, **kwargs):
        guest = super(RsvpForm, self).save(*args, **kwargs)
        rsvp_recieved.send(sender=self, guest=guest)
        return guest

class RsvpConfirmForm(forms.ModelForm):
    first_name = forms.CharField(required=True, max_length=50)
    last_name = forms.CharField(required=False, max_length=50)
    email = forms.EmailField(required=True)
    phone = forms.CharField(required=False, max_length=12)

    class Meta:
        model = Guest
        fields = ("first_name", "last_name", "email", "phone",)

    def clean_email(self):
        data = self.cleaned_data["email"]
        if data:
            try:
                existing = Guest.objects.get(event=self.instance.event, contributor__email=data)
                existing.rsvp_status = self.instance.rsvp_status
                existing.comments = self.instance.comments
                self.instance = existing
            except Guest.DoesNotExist:
                pass
        return data

    def save(self, request, *args, **kwargs):
        first_name = self.cleaned_data.get("first_name", None)
        if first_name:
            self.instance.contributor.first_name = first_name
        last_name = self.cleaned_data.get("last_name", None)
        if last_name:
            self.instance.contributor.last_name = last_name
        email = self.cleaned_data.get("email", None)
        if email:
            self.instance.contributor.email = email
        phone = self.cleaned_data.get("phone", None)
        if phone:
            self.instance.contributor.phone = phone
        guest = super(RsvpConfirmForm, self).save(*args, **kwargs)
        guest.event.save_guest_in_session(request=request, guest=guest)
        rsvp_recieved.send(sender=self, guest=guest)
        return guest

class RsvpAccountForm(forms.ModelForm):
    zipcode = forms.CharField(max_length=10, required=False)
    password1 = forms.CharField(label='Password', min_length=5, widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    class Meta:
        model = Guest
        fields = ("zipcode", "password1", "password2",)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1", "")
        password2 = self.cleaned_data["password2"]
        if password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        if len(password2) < 5:
            raise forms.ValidationError("Your password must contain at least 5 characters.")
        return password2

    def clean_zipcode(self):
        data = self.cleaned_data['zipcode'].strip()
        if not len(data):
            self.instance.contributor.location = None
            return
        if len(data) <> 5:
            raise forms.ValidationError("Please enter a 5 digit zipcode")
        try:
            self.cleaned_data["location"] = Location.objects.get(zipcode=data)
        except Location.DoesNotExist, e:
            raise forms.ValidationError("Zipcode is invalid")
        else:
            self.instance.contributor.location = self.cleaned_data["location"]

    def save(self, request, *args, **kwargs):
        from rah.signals import logged_in
        user = User(first_name=self.instance.contributor.first_name, last_name=self.instance.contributor.last_name,
            email=self.instance.contributor.email)
        user.username = hashlib.md5(self.instance.contributor.email).hexdigest()[:30]
        user.set_password(self.cleaned_data.get("password1", auth.models.UNUSABLE_PASSWORD))
        user.save()

        # Connect the new user with the contributor
        self.instance.contributor.user = user

        # Set the location on the new user's profile
        profile = user.get_profile()
        profile.location = self.instance.contributor.location
        profile.save()

        guest = super(RsvpAccountForm, self).save(*args, **kwargs)
        guest.event.save_guest_in_session(request=request, guest=guest)
        return guest

class MessageForm(forms.Form):
    note = forms.CharField(label="Personal Note", widget=forms.Textarea,
        help_text="Enter a brief note that will be included in your email")
    guests = forms.ModelMultipleChoiceField(queryset=None, widget=forms.MultipleHiddenInput)

    def __init__(self, user, event, type, *args, **kwargs):
        super(MessageForm, self).__init__(*args, **kwargs)
        self.user = user
        self.event = event
        self.type = type
        self.fields["guests"].queryset = event.guest_set.all()

    def save(self, *args, **kwargs):
        extra_params={"author": self.user, "note": self.cleaned_data["note"]}
        if self.type == "reminder":
            for guest in self.cleaned_data["guests"]:
                Stream.objects.get(slug="event-reminder").enqueue(content_object=guest,
                    start=datetime.datetime.now(), extra_params=extra_params)
        elif self.type == "announcement":
            for guest in self.cleaned_data["guests"]:
                Stream.objects.get(slug="event-announcement").enqueue(content_object=guest,
                    start=datetime.datetime.now(), extra_params=extra_params)
        else:
            raise AttributeError("Unknown message type: %s" % self.type)
