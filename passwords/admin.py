from django.contrib import admin
from .models import Password

class PasswordAdmin(admin.ModelAdmin):
    list_display = ('name', 'username', 'website_url', 'user', 'created_at', 'is_deleted')
    list_filter = ('created_at', 'is_deleted')
    search_fields = ('name', 'username', 'website_url', 'user__username')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'

admin.site.register(Password, PasswordAdmin)