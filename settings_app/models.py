from django.db import models
from django.contrib.auth.models import User

class UserSettings(models.Model):
    THEME_CHOICES = (
        ('light', 'Light'),
        ('dark', 'Dark'),
        ('system', 'System Default'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='settings')
    theme = models.CharField(max_length=10, choices=THEME_CHOICES, default='system')
    enable_notifications = models.BooleanField(default=True)
    enable_email_alerts = models.BooleanField(default=True)
    default_job_app_view = models.CharField(max_length=20, default='list', choices=(
        ('list', 'List View'),
        ('kanban', 'Kanban View'),
        ('calendar', 'Calendar View'),
    ))
    encrypt_passwords = models.BooleanField(default=True)
    auto_logout_minutes = models.IntegerField(default=30)
    
    def __str__(self):
        return f"Settings for {self.user.username}"