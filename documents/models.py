from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.core.validators import FileExtensionValidator
import os

def document_upload_path(instance, filename):
    """Custom upload path with user-specific directory structure"""
    return f"documents/user_{instance.user.id}/{timezone.now().strftime('%Y/%m/%d')}/{filename}"

class Document(models.Model):
    DOCUMENT_TYPES = [
        ('PDF', 'PDF'),
        ('DOC', 'Word Document'),
        ('IMG', 'Image'),
        ('XLS', 'Spreadsheet'),
        ('PPT', 'Presentation'),
        ('TXT', 'Text File'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    file = models.FileField(
        upload_to=document_upload_path,
        validators=[FileExtensionValidator(
            allowed_extensions=[
                'pdf', 'doc', 'docx', 'xls', 'xlsx', 
                'ppt', 'pptx', 'jpg', 'jpeg', 'png', 'gif', 'txt'
            ]
        )]
    )
    file_type = models.CharField(max_length=10, choices=DOCUMENT_TYPES)
    file_size = models.PositiveIntegerField(help_text="Size in bytes")
    upload_date = models.DateTimeField(auto_now_add=True)
    expiry_date = models.DateTimeField(blank=True, null=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    
    # Notification tracking fields
    expiry_notified = models.BooleanField(
        default=False,
        help_text="Whether expiration notification has been sent"
    )
    last_notification_sent = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Timestamp of last expiration notification"
    )

    class Meta:
        ordering = ['-upload_date']
        indexes = [
            models.Index(fields=['expiry_date']),
            models.Index(fields=['is_deleted']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.file_type})"

    def save(self, *args, **kwargs):
        # Update file metadata on initial save
        if not self.pk and self.file:
            self._set_file_metadata()
        
        # Reset notification status if expiry date changes
        if self.pk and self.expiry_date:
            original = Document.objects.get(pk=self.pk)
            if original.expiry_date != self.expiry_date:
                self.expiry_notified = False
                self.last_notification_sent = None
        
        super().save(*args, **kwargs)

    def _set_file_metadata(self):
        """Extract and set file type/size from uploaded file"""
        ext = os.path.splitext(self.file.name)[1].lower()
        self.file_type = self._map_extension_to_type(ext)
        self.file_size = self.file.size

    @staticmethod
    def _map_extension_to_type(extension):
        """Map file extensions to document types"""
        type_mapping = {
            '.pdf': 'PDF',
            '.doc': 'DOC', '.docx': 'DOC',
            '.xls': 'XLS', '.xlsx': 'XLS',
            '.ppt': 'PPT', '.pptx': 'PPT',
            '.jpg': 'IMG', '.jpeg': 'IMG',
            '.png': 'IMG', '.gif': 'IMG',
            '.txt': 'TXT',
        }
        return type_mapping.get(extension, 'OTHER')

    def soft_delete(self):
        """Mark document as deleted without permanent removal"""
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def restore(self):
        """Restore a soft-deleted document"""
        self.is_deleted = False
        self.deleted_at = None
        self.save(update_fields=['is_deleted', 'deleted_at'])

    def mark_as_notified(self):
        """Update notification tracking fields"""
        self.expiry_notified = True
        self.last_notification_sent = timezone.now()
        self.save(update_fields=['expiry_notified', 'last_notification_sent'])

    @property
    def is_expired(self):
        """Check if document has expired"""
        return bool(self.expiry_date and timezone.now() > self.expiry_date)

    @property
    def expires_soon(self):
        """Check if document expires within 7 days"""
        if not self.expiry_date:
            return False
        warning_window = timezone.now() + timezone.timedelta(days=7)
        return timezone.now() < self.expiry_date <= warning_window

    @property
    def file_name(self):
        """Extract filename from file path"""
        return os.path.basename(self.file.name)

    @property
    def download_url(self):
        """Generate download URL (to be used with your URL routing)"""
        return f"/api/documents/{self.id}/download/"
    def replace_file(self, new_file):
        """
        Safely replace the document file with proper cleanup
        """
        if self.file:
            self.file.delete(save=False)
        self.file = new_file
        self._set_file_metadata()
        self.save()