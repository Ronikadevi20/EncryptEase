from rest_framework import generics, permissions
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

from .models import UserSettings
from .serializers import UserSettingsSerializer

class UserSettingsView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSettingsSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        # Get or create settings for the current user
        settings, created = UserSettings.objects.get_or_create(user=self.request.user)
        return settings