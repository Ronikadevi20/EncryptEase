# models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid

class Password(models.Model):
    CATEGORY_CHOICES = [
        ('SOCIAL', 'Social Media'),
        ('EMAIL', 'Email Accounts'),
        ('FINANCE', 'Financial Services'),
        ('WORK', 'Work Related'),
        ('ENTERTAINMENT', 'Entertainment'),
        ('SHOPPING', 'Online Shopping'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='passwords')
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True, null=True)
    password_value = models.CharField(max_length=500)
    website_url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='OTHER')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()
    
    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()



class SharedPassword(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    original_password = models.ForeignKey(Password, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, blank=True, null=True)
    password_value = models.CharField(max_length=500)
    website_url = models.URLField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    category = models.CharField(max_length=20)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    viewed = models.BooleanField(default=False)

    def is_expired(self):
        return timezone.now() > self.expires_at