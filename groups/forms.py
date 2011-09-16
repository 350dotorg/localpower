import datetime
import os

from django import forms
from django.core.files.storage import default_storage
from django.core.urlresolvers import resolve, reverse
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.flatpages.models import FlatPage
from django.utils.translation import ugettext_lazy as _

from PIL.Image import open as pil_open
from utils import hash_val

from geo.models import Location
from geo.fields import GoogleLocationField

from models import Group, GroupUsers, Discussion, GroupAssociationRequest

class GroupForm(forms.ModelForm):
    IMAGE_FORMATS = {"PNG": "png", "JPEG": "jpeg", "GIF": "gif"}

    name = forms.CharField(label=_("Community name"), 
                           help_text=_("Enter a name for your new community"))
    slug = forms.SlugField(label=_("Community address"),
                           help_text=_("This will be your community's web address"))
    description = forms.CharField(label=_("Community description"),
                                  help_text=_("What is the community all about?"),
        widget=forms.Textarea(attrs={"rows": 5}))
    headquarters = GoogleLocationField(label=_("Headquarters"))
    image = forms.FileField(label=_("Upload a community image"),
                            help_text=_("(Optional) You can upload png, jpg or gif files up to 512K"),
                            required=False)

    states = ["ak", "al", "ar", "az", "ca", "co", "ct", "dc", "de", "fl", "ga", "hi", "ia", "id", "il",
        "in", "ks", "ky", "la", "ma", "md", "me", "mi", "mn", "mo", "ms", "mt", "nc", "nd", "ne",
        "nh", "nj", "nm", "nv", "ny", "oh", "ok", "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut",
        "va", "vt", "wa", "wi", "wv", "wy"]
    group_name_blacklist = ["user", "users", "admin", "event", "team", "teams", "community", "communities", "groups", "groups"]

    class Meta:
        model = Group
        exclude = ("is_featured", "lat", "lon",
                   "is_geo_group", "location_type", "sample_location", "member_count",
                   "parent", "users", "requesters", 
                   "email_blacklisted", "disc_moderation", "disc_post_perm",
                   "is_external_link_only")
        widgets = {
            "membership_type": forms.RadioSelect
        }

    def clean_image(self):
        data = self.cleaned_data["image"]
        if data:
            if data.size > 4194304:
                raise forms.ValidationError(_("Community images cannot be larger than 512K"))
            self.image_format = pil_open(data.file).format
            if not self.image_format in GroupForm.IMAGE_FORMATS:
                raise forms.ValidationError(_("Images cannot be of type %(type)s") % {
                        'type': data.content_type})
        return data

    def clean_slug(self):
        data = self.cleaned_data["slug"]
        if data in GroupForm.states or any([data.startswith("%s-" % state) for state in GroupForm.states]):
            raise forms.ValidationError(_("Community addresses cannot begin with a state name."))

        # Make sure the name is not in the blacklist or a resolvable URL
        try:
            if data in GroupForm.group_name_blacklist or resolve(reverse("group_detail", args=[data]))[0].__name__ != "group_detail":
                raise forms.ValidationError(_("This community address is not available."))
        except:
            raise forms.ValidationError(_("This community address is not available."))

        # Make sure there isn't a flatpage with this slug
        if FlatPage.objects.filter(url="/%s/" % data):
            raise forms.ValidationError(_("This community address is not available."))
        return data

    def save(self):
        if self.cleaned_data["headquarters"]:
            field = self.fields["headquarters"]
            self.instance.lat = field.raw_data["latitude"]
            self.instance.lon = field.raw_data["longitude"]
        group = super(GroupForm, self).save()
        current_image = self.cleaned_data["image"]
        if current_image and current_image != group.image.field.default:
            timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            image_name = "%s_%s.%s" % (group.pk, timestamp, GroupForm.IMAGE_FORMATS[self.image_format])
            original_file = group.image.file
            original_name = original_file.name
            group.image.save(image_name, original_file, save=True)
            group.image.storage.delete(original_name)
        return group

class GroupExternalLinkOnlyForm(GroupForm):
    class Meta:
        model = Group
        exclude = ("is_featured", "lat", "lon",
                   "is_geo_group", "location_type", "sample_location", "member_count",
                   "parent", "users", "requesters", 
                   "email_blacklisted", "disc_moderation", "disc_post_perm",
                   "is_external_link_only",
                   "membership_type")

    def save(self):
        group = super(GroupExternalLinkOnlyForm, self).save()
        group.is_external_link_only = True
        return group

class MembershipForm(forms.Form):
    MEMBERSHIP_ROLES = (
        ('', _('--Set Membership Role--')),
        ('M', _('Manager'),),
        ('N', _('Regular Member'),),
        ('D', _('Remove from Community'),),
    )
    role = forms.ChoiceField(label="", choices=MEMBERSHIP_ROLES, 
                             error_messages={
            "required": _("You must select a membership action.")})
    memberships = forms.ModelMultipleChoiceField(queryset=GroupUsers.objects.all(), 
                                                 widget=forms.CheckboxSelectMultiple,
                                                 error_messages={
            "required": _("You must select at least one member from the community.")})

    def __init__(self, group, *args, **kwargs):
        super(MembershipForm, self).__init__(*args, **kwargs)
        self.group = group
        self.fields["memberships"].queryset = GroupUsers.objects.filter(group=group)

    def clean(self):
        data = self.cleaned_data
        role = data["role"] if "role" in data else ""
        memberships = data["memberships"] if "memberships" in data else []
        if (role == "N" or role == "D") and self.group.number_of_managers() == len(memberships):
            self._errors["memberships"] = forms.util.ErrorList([
                    _("You must leave at least one manager in the community.")])
            del self.cleaned_data["memberships"]
        return self.cleaned_data

    def save(self):
        role = self.cleaned_data["role"]
        memberships = self.cleaned_data["memberships"]
        if role == "M":
            memberships.update(is_manager=True)
        elif role == "N":
            memberships.update(is_manager=False)
        elif role == "D":
            memberships.delete()
        else:
            raise NameError(_("Role option %(role)s does not exist") % {'role': role})

class DiscussionSettingsForm(forms.ModelForm):
    class Meta:
        model = Group
        fields = ("disc_moderation", "disc_post_perm", )
        widgets = {
            "disc_moderation": forms.RadioSelect,
            "disc_post_perm": forms.RadioSelect
        }

class DiscussionCreateForm(forms.Form):
    subject = forms.CharField()
    body = forms.CharField(widget=forms.Textarea, label=_("Comment"))
    parent_id = forms.IntegerField(widget=forms.HiddenInput, required=False)
    parent_id_sig = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        super(DiscussionCreateForm, self).__init__(*args, **kwargs)
        # If a parent_id was passed in, sign it
        if 'parent_id' in self.initial:
            self.fields['parent_id_sig'].initial = hash_val(self.initial.get('parent_id'))
            self.fields['subject'].widget = forms.HiddenInput()

    def clean_parent_id(self):
        """Verify the parent_id_sig"""
        parent_id = self.cleaned_data['parent_id']
        if parent_id:
            sig_check = hash_val(parent_id)
            if parent_id and sig_check <> self.data['parent_id_sig']:
                raise forms.ValidationError(_('Parent ID is currupted'))
        return parent_id

class DiscussionApproveForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['is_public']
        widgets = {
            "is_public": forms.HiddenInput
        }

    def __init__(self, *args, **kwargs):
        super(DiscussionApproveForm, self).__init__(*args, **kwargs)
        self.fields['is_public'].initial = True

class DiscussionRemoveForm(forms.ModelForm):
    class Meta:
        model = Discussion
        fields = ['is_removed']
        widgets = {
            "is_removed": forms.HiddenInput
        }

    def __init__(self, *args, **kwargs):
        super(DiscussionRemoveForm, self).__init__(*args, **kwargs)
        self.fields['is_removed'].initial = True

class GroupAssociationRequestRelatedForm(object):
    """
    Use as a mixin base class for other model-backed forms that provide group
    associations for their content objects and want to hook in to the machinery
    for associating with groups directly for each requested group for which the
    requesting user is an admin, and issuing a Group Association Request for each
    requested group for which the requesting user is not an admin.  The form's 
    related model must have a `ManyToManyField("groups.Group")` named `groups`.

    To use this form, your ModelForm subclass must:
    * also subclass this base
    * require a `user` argument to its `__init__`, and stash it as an attribute
    * call `self.init_groups(user)` at some point in its `__init__()`
    * specify "groups" in `fields` on its `Meta` class
    * specify a `forms.CheckboxSelectMultiple()` for "groups" in `widgets` on
      its `Meta` class
    * not implement a method `clean_groups`
    * call `self.save_groups(content_object)` at some point in its `save()`

    For examples, look at `events.forms.EventForm` and `challenges.forms.ChallengeForm`.
    """

    def init_groups(self, user):
        groups = self.fields["groups"]
        if user is None or user.is_anonymous():
            groups.queryset = groups.queryset.none()
        else:
            groups.queryset = groups.queryset.filter(groupusers__user=user)
        if not groups.queryset:
            groups.help_text = _("You need to be a member of a community first")
        else:
            groups.help_text = None

    def clean_groups(self):
        data = self.cleaned_data["groups"]
        approved_groups, self.requested_groups = [], []
        content_type = ContentType.objects.get_for_model(self.instance)
        for g in data:
            if g.is_user_manager(self.user) or GroupAssociationRequest.objects.filter(
                content_type=content_type, object_id=self.instance.pk,
                group=g, approved=True).exists():
                approved_groups.append(g)
            else:
                self.requested_groups.append(g)
        return approved_groups

    def save_groups(self, content_object):
        content_type = ContentType.objects.get_for_model(content_object)
        for g in self.requested_groups:
            request, created = GroupAssociationRequest.objects.get_or_create(
                content_type=content_type, object_id=content_object.pk,
                group=g)
            # TODO: notify user of groups requested
