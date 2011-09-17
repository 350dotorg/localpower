from django.contrib import admin
from models import Group, GroupUsers, GroupAssociationRequest
from django.utils.translation import ugettext_lazy as _

class GroupAdmin(admin.ModelAdmin):
    list_display = ("name", "managers", "total_members", "committed_actions", "completed_actions", "total_points", "created",)
    readonly_fields = ("sample_location",)

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
