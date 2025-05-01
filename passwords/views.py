from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.utils import timezone
from django.shortcuts import render, get_object_or_404
from .models import Password, SharedPassword
from .serializers import PasswordSerializer
from rest_framework.decorators import action
from datetime import timedelta
from django.urls import reverse
from django.http import HttpResponseRedirect
import pytz

class PasswordViewSet(viewsets.ModelViewSet):
    serializer_class = PasswordSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        # Only return non-deleted passwords for the current user
        return Password.objects.filter(user=self.request.user, is_deleted=False)
    
    def perform_destroy(self, instance):
        # Soft delete instead of actual delete
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        password = self.get_object()
        if password.user != request.user:
            return Response({'error': 'Permission denied'}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            hours = int(request.data.get('hours', 24))
        except ValueError:
            return Response({'error': 'Invalid hours value'}, status=status.HTTP_400_BAD_REQUEST)
        tzname = request.data.get('timezone', 'UTC')
        try:
            user_tz = pytz.timezone(tzname)
        except Exception:
            user_tz = pytz.UTC
        expires_at = timezone.now() + timedelta(hours=hours)

        shared = SharedPassword.objects.create(
            original_password=password,
            name=password.name,
            username=password.username,
            password_value=password.password_value,
            website_url=password.website_url,
            notes=password.notes,
            category=password.category,
            created_by=request.user,
            expires_at=expires_at
        )
        
        share_url = request.build_absolute_uri(
            reverse('shared-password', kwargs={'token': shared.token})
        )

        return Response({'share_url': share_url}, status=status.HTTP_201_CREATED)

def shared_password_view(request, token):
    shared = get_object_or_404(SharedPassword, token=token)
    
    if shared.is_expired():
        return render(request, 'passwords/shared_expired.html')
    
    if shared.original_password.is_deleted:
        return render(request, 'passwords/shared_deleted.html')
    
    # Mark as viewed (optional)
    if not shared.viewed:
        shared.viewed = True
        shared.save()
    
    return render(request, 'passwords/shared_detail.html', {
        'password': shared,
        'expires_at': shared.expires_at
    })