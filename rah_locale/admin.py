from django.contrib import admin

from rah_locale.models import (TranslatedFlatPage, TranslatedAction,
                               TranslatedMessage)

class TranslatedActionAdmin(admin.ModelAdmin):
    list_display = ("action", "language")
    list_filter = ("action", "language")

class TranslatedMessageAdmin(admin.ModelAdmin):
    list_display = ("message", "language")
    list_filter = ("message", "language")

class TranslatedFlatPageAdmin(admin.ModelAdmin):
    list_display = ("flatpage", "language")
    list_filter = ("flatpage", "language")

admin.site.register(TranslatedFlatPage, TranslatedFlatPageAdmin)
admin.site.register(TranslatedAction, TranslatedActionAdmin)
admin.site.register(TranslatedMessage, TranslatedMessageAdmin)
