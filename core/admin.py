from django.contrib import admin
from .models import UserProfile

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'otp_verified')
    search_fields = ('user__username', 'user__email')

admin.site.register(UserProfile, UserProfileAdmin)