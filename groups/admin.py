from django.contrib import admin
from models import Group, GroupUsers, GroupAssociationRequest
from django.utils.translation import ugettext_lazy as _

class GroupAdmin(admin.ModelAdmin):
    valid_lookups = ("geom",)
    list_display = ("name", "geom", "managers", "total_members",
                    "committed_actions", "completed_actions",
                    "total_points", "created",)
    readonly_fields = ("sample_location",)
    list_filter = ("disc_moderation", "sample_location", "created", "updated")

    def lookup_allowed(self, lookup, *args, **kwargs):
        for valid_lookup in self.valid_lookups:
            if lookup.startswith(valid_lookup):
                return True
        return admin.ModelAdmin.lookup_allowed(self, lookup, *args, **kwargs)
        
    def managers(self, obj):
        return ", ".join([u.get_full_name() for u in obj.managers()])
    managers.short_description = _("Managers")

    def committed_actions(self, obj):
        return sum([m.actions_committed for m in obj.members_ordered_by_points() if m.actions_committed])

    def completed_actions(self, obj):
        return sum([m.actions_completed for m in obj.members_ordered_by_points() if m.actions_completed])

admin.site.register(Group, GroupAdmin)

class GroupUsersAdmin(admin.ModelAdmin):
    list_display = ("user", "group", "is_manager", "created", "updated")
    list_filter = ("group", "user")
    search_fields = ("group__slug", "user__email", "user__first_name", "user__last_name")
    csv_export_fields = list_display + (
        "user__email", "user__first_name", "user__last_name",
        "user__profile__phone", 
        "user__profile__geom__city",
        "user__profile__geom__state",
        "user__profile__geom__country",
        "user__profile__geom__postal",
        )
    list_select_related = True

admin.site.register(GroupUsers, GroupUsersAdmin)
admin.site.register(GroupAssociationRequest)
