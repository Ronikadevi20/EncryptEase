# views.py
from rest_framework import viewsets, status, filters
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from django.http import FileResponse
from django.db.models import Q

from .models import Document
from .serializers import DocumentSerializer, DocumentUpdateSerializer
from .filters import DocumentFilter

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = DocumentFilter
    search_fields = ['title', 'description']
    ordering_fields = ['title', 'upload_date', 'expiry_date']
    ordering = ['-upload_date']
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Document.objects.none()

        queryset = Document.objects.filter(user=self.request.user)
        
        expiry_status = self.request.query_params.get('expiry_status', None)
        if expiry_status == 'active':
            queryset = queryset.filter(
                Q(expiry_date__gte=timezone.now()) | Q(expiry_date__isnull=True))
        elif expiry_status == 'expired':
            queryset = queryset.filter(expiry_date__lt=timezone.now())
        elif expiry_status == 'expiring_soon':
            soon = timezone.now() + timezone.timedelta(days=7)
            queryset = queryset.filter(
                expiry_date__range=(timezone.now(), soon))
        
        show_deleted = self.request.query_params.get('show_deleted', 'false').lower() == 'true'
        if not show_deleted:
            queryset = queryset.filter(is_deleted=False)
        
        return queryset

    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return DocumentUpdateSerializer
        return DocumentSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
    
    def perform_destroy(self, instance):
        instance.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        document = self.get_object()
        if not document.is_deleted:
            return Response(
                {'detail': 'Document is not deleted'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        document.restore()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        document = self.get_object()
        if document.is_expired:
            return Response(
                {'detail': 'This document has expired and cannot be downloaded'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        response = FileResponse(document.file.open('rb'))
        response['Content-Disposition'] = f'attachment; filename="{document.file_name}"'
        return response
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        user_docs = Document.objects.filter(user=request.user, is_deleted=False)
        
        total_documents = user_docs.count()
        expired_documents = user_docs.filter(expiry_date__lt=timezone.now()).count()
        expiring_soon = user_docs.filter(
            expiry_date__range=(timezone.now(), timezone.now() + timezone.timedelta(days=7))
            .count())
        
        return Response({
            'total_documents': total_documents,
            'expired_documents': expired_documents,
            'expiring_soon': expiring_soon,
        })