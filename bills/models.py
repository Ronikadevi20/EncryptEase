from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Bill(models.Model):
    CATEGORY_CHOICES = [
        ('UTILITIES', 'Utilities'),
        ('SUBSCRIPTION', 'Subscription'),
        ('LOAN', 'Loan'),
        ('INSURANCE', 'Insurance'),
        ('CREDIT_CARD', 'Credit Card'),
        ('RENT', 'Rent'),
        ('BILLS', 'Bills'),
        ('OTHER', 'Other'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bills')
    name = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    payment_date = models.DateField(null=True, blank=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='BILLS')
    notes = models.TextField(blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    password_value = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(blank=True, null=True)
    receipt = models.FileField(upload_to='bill_receipts/', blank=True, null=True)

    class Meta:
        ordering = ['-due_date']

    def __str__(self):
        return self.name

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        self.is_deleted = False
        self.deleted_at = None
        self.save()