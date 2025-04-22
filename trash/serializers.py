from rest_framework import serializers

class TrashItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    type = serializers.CharField()
    deleted_at = serializers.DateTimeField()
    
    # Additional details that might be useful in the trash view
    details = serializers.SerializerMethodField()
    
    def get_details(self, obj):
        """Return type-specific details for different items"""
        if obj['type'] == 'document':
            return {
                'file_type': obj.get('file_type', ''),
                'size': obj.get('file_size', 0)
            }
        elif obj['type'] == 'bill':
            return {
                'amount': str(obj.get('amount', '')),
                'category': obj.get('category', '')
            }
        elif obj['type'] == 'application':
            return {
                'company': obj.get('company', ''),
                'job_title': obj.get('job_title', '')
            }
        elif obj['type'] == 'password':
            return {
                'category': obj.get('category', '')
            }
        return {}