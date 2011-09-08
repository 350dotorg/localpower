import csv

from django.contrib import admin
from django.template import RequestContext
from django.shortcuts import render_to_response

from models import Message, ABTest, Stream, Queue

def preview_messages(modeladmin, request, queryset):
    previews = []
    for message in queryset:
        for preview in message.clean():
            previews.append((message.name, preview.email.body))
    return render_to_response("messaging/previews.html", {"previews": previews, "appmodel": "Messages"}, RequestContext(request))
preview_messages.short_description = "Preview Messages"

def preview_stream(modeladmin, request, queryset):
    previews = []
    for stream in queryset:
        for abtest in stream.abtest_set.all():
            for preview in abtest.message.clean():
                previews.append((abtest.message.name, preview.email.body))
    return render_to_response("messaging/previews.html", {"previews": previews, "appmodel": "Streams"}, RequestContext(request))
preview_stream.short_description = "Preview Stream"

class MessageAdmin(admin.ModelAdmin):
    list_display = ("__unicode__", "sends", "unique_opens", "click_thrus")
    readonly_fields = ("sends", "recipient_function", "extra_headers_function")
    fieldsets = (
        (None, {"fields": ("name", "subject", "body", "sends", "recipient_function", "extra_headers_function")}),
        ("Send Time", {"fields": ("message_timing", "x_value",)}),
        ("Advanced Options", {"fields": ("send_as_batch", "batch_window", "time_snap",
            "minimum_duration", "content_types", "generic_relation_content_type"),
            "classes": ("collapse",)}),
    )
    actions = [preview_messages]

class ABTestAdmin(admin.ModelAdmin):
    list_display = ("__unicode__", "control_sends", "control_opens", "test_sends", "test_opens", "stream")

class StreamAdmin(admin.ModelAdmin):
    actions = [preview_stream]

admin.site.register(Message, MessageAdmin)
admin.site.register(ABTest, ABTestAdmin)
admin.site.register(Stream, StreamAdmin)
admin.site.register(Queue)
