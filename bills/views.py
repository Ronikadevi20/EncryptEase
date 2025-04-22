# views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Bill
from .serializers import BillSerializer
from .permissions import IsOwner
from rest_framework.parsers import MultiPartParser, FormParser

class BillViewSet(viewsets.ModelViewSet):
    serializer_class = BillSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    parser_classes = [MultiPartParser, FormParser]  # Add this line

    # ... rest of your view code
    def get_queryset(self):
        # Show only non-deleted bills by default
        queryset = Bill.objects.filter(user=self.request.user, is_deleted=False)
        
        # Option to view deleted bills if needed
        show_deleted = self.request.query_params.get('show_deleted', '').lower() == 'true'
        if show_deleted:
            queryset = Bill.objects.filter(user=self.request.user)
            
        return queryset

    def perform_create(self, serializer):
        print(serializer)
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def soft_delete(self, request, pk=None):
        bill = self.get_object()
        bill.soft_delete()
        return Response({'status': 'soft deleted'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        bill = self.get_object()
        bill.restore()
        return Response({'status': 'restored'}, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        # Override default delete to use soft delete
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def perform_destroy(self, instance):
        # Change from hard delete to soft delete
        instance.soft_delete()