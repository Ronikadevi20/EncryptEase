from django.contrib import admin
from .models import JobApplication, ApplicationAttachment

class ApplicationAttachmentInline(admin.TabularInline):
    model = ApplicationAttachment
    extra = 1

class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('job_title', 'company', 'status', 'applied_date', 'user', 'is_deleted')
    list_filter = ('status', 'applied_date', 'is_deleted')
    search_fields = ('job_title', 'company', 'user__username')
    inlines = [ApplicationAttachmentInline]
    date_hierarchy = 'applied_date'

admin.site.register(JobApplication, JobApplicationAdmin)
admin.site.register(ApplicationAttachment)