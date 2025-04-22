# documents/admin.py
from django.contrib import admin
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 'user', 'file_type', 'upload_date', 'expiry_date', 
        'is_deleted', 'expiry_notified'
    )
    list_filter = ('file_type', 'is_deleted', 'expiry_notified', 'upload_date', 'expiry_date')
    search_fields = ('title', 'description', 'file')
    date_hierarchy = 'upload_date'
    readonly_fields = ('upload_date', 'file_size', 'file_type', 'last_notification_sent')

    def get_queryset(self, request):
        # Include soft-deleted documents in admin
        return super().get_queryset(request)

    def has_delete_permission(self, request, obj=None):
        # Prevent permanent deletion through admin
        return False

    def save_model(self, request, obj, form, change):
        # Ensure file metadata is updated on save
        if obj.file and not change:
            obj._set_file_metadata()
        super().save_model(request, obj, form, change)
