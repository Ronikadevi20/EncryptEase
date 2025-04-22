from django.contrib import admin
from .models import Bill
from django.utils.html import format_html
from django.utils.timezone import now

@admin.register(Bill)
class BillAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'user', 'amount', 'due_date', 'category', 'is_paid', 
        'is_deleted', 'deleted_at', 'created_at'
    )
    list_filter = ('category', 'is_paid', 'is_deleted', 'due_date')
    search_fields = ('name', 'notes', 'username', 'user__username')
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

    actions = ['soft_delete_selected', 'restore_selected', 'permanently_delete_selected']

    def soft_delete_selected(self, request, queryset):
        updated = 0
        for obj in queryset:
            if not obj.is_deleted:
                obj.soft_delete()
                updated += 1
        self.message_user(request, f"{updated} bill(s) soft deleted.")
    soft_delete_selected.short_description = "Soft delete selected bills"

    def restore_selected(self, request, queryset):
        restored = 0
        for obj in queryset:
            if obj.is_deleted:
                obj.restore()
                restored += 1
        self.message_user(request, f"{restored} bill(s) restored.")
    restore_selected.short_description = "Restore selected bills"

    def permanently_delete_selected(self, request, queryset):
        count = queryset.filter(is_deleted=True).count()
        queryset.filter(is_deleted=True).delete()
        self.message_user(request, f"{count} bill(s) permanently deleted.")
    permanently_delete_selected.short_description = "Permanently delete selected bills (only soft-deleted ones)"

