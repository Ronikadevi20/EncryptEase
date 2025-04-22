# documents/management/commands/check_expiry.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from documents.models import Document

class Command(BaseCommand):
    help = 'Sends expiry notifications for documents'

    def handle(self, *args, **options):
        now = timezone.now()
        threshold = now + timezone.timedelta(days=7)
        
        documents = Document.objects.filter(
            expiry_date__lte=threshold,
            expiry_date__gte=now,
            is_deleted=False,
            expiry_notified=False
        ).select_related('user__settings')

        for doc in documents:
            if not doc.user.settings.enable_email_alerts:
                continue

            context = {
                'user': doc.user,
                'document': doc,
                'expiry_date': doc.expiry_date.strftime('%Y-%m-%d'),
                'document_url': f"{settings.FRONTEND_URL}/documents/{doc.id}"
            }

            html_message = render_to_string(
                'emails/document_expiry_alert.html',
                context
            )
            
            send_mail(
                subject=f"Document Expiring: {doc.title}",
                message=strip_tags(html_message),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[doc.user.email],
                html_message=html_message
            )

            doc.expiry_notified = True
            doc.last_notification_sent = timezone.now()
            doc.save()

        self.stdout.write(f"Sent {documents.count()} notifications")