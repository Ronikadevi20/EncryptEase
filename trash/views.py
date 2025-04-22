from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q

from applications.models import JobApplication
from passwords.models import Password
from documents.models import Document
from bills.models import Bill
from .serializers import TrashItemSerializer
from datetime import datetime
import pytz  # Add this import

class TrashListView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        # Get all deleted items for the current user
        deleted_applications = JobApplication.objects.filter(
            user=request.user, 
            is_deleted=True
        )
        deleted_passwords = Password.objects.filter(
            user=request.user, 
            is_deleted=True
        )
        deleted_documents = Document.objects.filter(
            user=request.user,
            is_deleted=True
        )
        deleted_bills = Bill.objects.filter(
            user=request.user,
            is_deleted=True
        )
        
        # Create a combined list of all deleted items
        trash_items = []
        
        for app in deleted_applications:
            trash_items.append({
                'id': app.id,
                'name': f"{app.job_title} at {app.company}",
                'type': 'application',
                'deleted_at': app.deleted_at,
                'company': app.company,
                'job_title': app.job_title
            })
        
        for pwd in deleted_passwords:
            trash_items.append({
                'id': pwd.id,
                'name': pwd.name,
                'type': 'password',
                'deleted_at': pwd.deleted_at,
                'category': pwd.category
            })
            
        for doc in deleted_documents:
            trash_items.append({
                'id': doc.id,
                'name': doc.title,
                'type': 'document',
                'deleted_at': doc.deleted_at,
                'file_type': doc.file_type,
                'file_size': doc.file_size
            })
            
        for bill in deleted_bills:
            trash_items.append({
                'id': bill.id,
                'name': bill.name,
                'type': 'bill',
                'deleted_at': bill.deleted_at,
                'amount': bill.amount,
                'category': bill.category
            })
        
        # Sort by deletion date (newest first)
        trash_items.sort(
            key=lambda x: x['deleted_at'] or timezone.make_aware(datetime.min, pytz.UTC),
            reverse=True
        )
        
        serializer = TrashItemSerializer(trash_items, many=True)
        return Response(serializer.data)

class RestoreItemView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        item_id = request.data.get('id')
        item_type = request.data.get('type')
        
        if not item_id or not item_type:
            return Response({
                "error": "Both id and type are required"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if item_type == 'application':
                item = JobApplication.objects.get(id=item_id, user=request.user, is_deleted=True)
                item.is_deleted = False
                item.deleted_at = None
                item.save()
                return Response({
                    "message": "Job application restored successfully"
                }, status=status.HTTP_200_OK)
            elif item_type == 'password':
                item = Password.objects.get(id=item_id, user=request.user, is_deleted=True)
                item.restore()
                return Response({
                    "message": "Password restored successfully"
                }, status=status.HTTP_200_OK)
            elif item_type == 'document':
                item = Document.objects.get(id=item_id, user=request.user, is_deleted=True)
                item.restore()
                return Response({
                    "message": "Document restored successfully"
                }, status=status.HTTP_200_OK)
            elif item_type == 'bill':
                item = Bill.objects.get(id=item_id, user=request.user, is_deleted=True)
                item.restore()
                return Response({
                    "message": "Bill restored successfully"
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    "error": "Invalid item type"
                }, status=status.HTTP_400_BAD_REQUEST)
        except (JobApplication.DoesNotExist, Password.DoesNotExist, Document.DoesNotExist, Bill.DoesNotExist):
            return Response({
                "error": "Item not found"
            }, status=status.HTTP_404_NOT_FOUND)
class PermanentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request, item_id, item_type):  # Accept parameters from URL
        try:
            if item_type == 'application':
                item = JobApplication.objects.get(id=item_id, user=request.user, is_deleted=True)
                item.delete()
            elif item_type == 'password':
                item = Password.objects.get(id=item_id, user=request.user, is_deleted=True)
                item.delete()
            elif item_type == 'document':
                item = Document.objects.get(id=item_id, user=request.user, is_deleted=True)
                item.delete()
            elif item_type == 'bill':
                item = Bill.objects.get(id=item_id, user=request.user, is_deleted=True)
                item.delete()
            else:
                return Response({"error": "Invalid item type"}, status=status.HTTP_400_BAD_REQUEST)
            
            return Response({"message": f"{item_type} permanently deleted"}, status=status.HTTP_200_OK)
            
        except (JobApplication.DoesNotExist, Password.DoesNotExist, Document.DoesNotExist, Bill.DoesNotExist):
            return Response({"error": "Item not found"}, status=status.HTTP_404_NOT_FOUND)

class EmptyTrashView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request):
        # Permanently delete all items in trash
        JobApplication.objects.filter(user=request.user, is_deleted=True).delete()
        Password.objects.filter(user=request.user, is_deleted=True).delete()
        Document.objects.filter(user=request.user, is_deleted=True).delete()
        Bill.objects.filter(user=request.user, is_deleted=True).delete()
        
        return Response({
            "message": "Trash emptied successfully"
        }, status=status.HTTP_200_OK)