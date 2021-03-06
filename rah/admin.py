from django.contrib import admin
from django.contrib.auth.models import User, Group, Permission
from django.contrib.auth.admin import (UserAdmin as BaseUserAdmin,
                                       GroupAdmin)
from django.contrib.comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.contrib.flatpages.admin import FlatPageAdmin
from django.contrib.flatpages.models import FlatPage
from django import forms
from django.http import HttpResponse
from django.utils.translation import ugettext_lazy as _

from tinymce.widgets import TinyMCE

from models import Profile
from forms import ProfileEditForm
from rateable.models import Rating

User._meta.get_field('email').user_country_filter = True
User._meta.get_field('first_name').user_state_filter = True
User._meta.get_field('last_name').user_city_filter = True
User._meta.get_field('date_joined').user_region_filter = True

class UserAdmin(BaseUserAdmin):
    valid_lookups = ("profile__geom",)
    list_display = ("email", "first_name", "last_name", "geom", "date_joined", "username",
                    "language", "phone")
    ordering = ("id",)
    date_hierarchy = "date_joined"
    search_fields = ("email", "first_name", "last_name",)
    list_filter = BaseUserAdmin.list_filter + (
        "date_joined", "email", "first_name", "last_name")

    def lookup_allowed(self, lookup, *args, **kwargs):
        for valid_lookup in self.valid_lookups:
            if lookup.startswith(valid_lookup):
                return True
        return admin.ModelAdmin.lookup_allowed(self, lookup, *args, **kwargs)

    def phone(self, obj):
        return obj.get_profile().phone

    def language(self, obj):
        return obj.get_profile().language

    def geom(self, obj):
        return obj.get_profile().geom
    geom.short_description = _("Location")

class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "geom", "is_profile_private", "facebook_connect_only", "language", "phone")
    search_fields = ("user__email",)
    form = ProfileEditForm

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Permission)
admin.site.register(Profile, ProfileAdmin)

class CommentAdmin(admin.ModelAdmin):
    list_display = ("user_name", "parent", "comment", "likes", "dislikes", "submit_date",)

    def __init__(self, *args, **kwargs):
        super(CommentAdmin, self).__init__(*args, **kwargs)
        self.content_type = ContentType.objects.get_for_model(Comment)

    def parent(self, obj):
        return str(obj.content_object)
    parent.short_description = _("Parent")

    def likes(self, obj):
        return Rating.objects.filter(content_type=self.content_type, object_pk=obj.id,
            score=1).count()
    likes.short_description = _("Likes")

    def dislikes(self, obj):
        return Rating.objects.filter(content_type=self.content_type, object_pk=obj.id,
            score=0).count()
    dislikes.short_description = _("Dislikes")

admin.site.register(Comment, CommentAdmin)

class TinyMCEFlatPageAdmin(FlatPageAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        if db_field.name == 'content':
            return forms.CharField(widget=TinyMCE(attrs={'cols': 80, 'rows': 30}))
        return super(TinyMCEFlatPageAdmin, self).formfield_for_dbfield(db_field, **kwargs)
admin.site.unregister(FlatPage)
admin.site.register(FlatPage, TinyMCEFlatPageAdmin)
