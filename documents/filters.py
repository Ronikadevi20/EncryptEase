# filters.py
from django_filters import FilterSet
from .models import Document

class DocumentFilter(FilterSet):
    class Meta:
        model = Document
        fields = {
            'file_type': ['exact'],
            'is_deleted': ['exact'],
            'upload_date': ['gte', 'lte'],
            'expiry_date': ['gte', 'lte', 'isnull'],
        }