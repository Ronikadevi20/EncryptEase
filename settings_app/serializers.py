from rest_framework import serializers
from .models import UserSettings
from django.contrib.auth.models import User

class UserSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSettings
        fields = (
            'id', 'theme', 'enable_notifications', 'enable_email_alerts',
            'default_job_app_view', 'encrypt_passwords', 'auto_logout_minutes'
        )
        read_only_fields = ('id',)