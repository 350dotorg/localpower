from django.contrib import admin

from rah_locale.models import TranslatedFlatPage, TranslatedAction

class TranslatedActionAdmin(admin.ModelAdmin):
    list_display = ("action", "language")
    list_filter = ("action", "language")

admin.site.register(TranslatedFlatPage)
admin.site.register(TranslatedAction, TranslatedActionAdmin)
