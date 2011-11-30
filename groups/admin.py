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
admin.site.register(GroupUsers)
admin.site.register(GroupAssociationRequest)
