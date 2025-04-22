from django.contrib import admin
from .models import UserSettings

class UserSettingsAdmin(admin.ModelAdmin):
    list_display = ('user', 'theme', 'enable_notifications', 'enable_email_alerts')
    list_filter = ('theme', 'enable_notifications', 'enable_email_alerts')
    search_fields = ('user__username', 'user__email')

admin.site.register(UserSettings, UserSettingsAdmin)