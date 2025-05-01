# serializers.py
from rest_framework import serializers
from .models import Document
from django.utils import timezone

class DocumentSerializer(serializers.ModelSerializer):
    file_name = serializers.SerializerMethodField()
    is_expired = serializers.SerializerMethodField()
    expires_soon = serializers.SerializerMethodField()
    expiry_notified = serializers.BooleanField(read_only=True)
    last_notification_sent = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = Document
        fields = (
            'id', 'title', 'description', 'file', 'file_name', 'file_type', 
            'file_size', 'upload_date', 'expiry_date', 'is_expired', 'expires_soon',
            'expiry_notified', 'last_notification_sent'
        )
        read_only_fields = (
            'id', 'file_type', 'file_size', 'upload_date', 'file_name',
            'expiry_notified', 'last_notification_sent'
        )

    def get_file_name(self, obj):
        return obj.file_name
    
    def get_is_expired(self, obj):
        return obj.is_expired
    
    def get_expires_soon(self, obj):
        return obj.expires_soon
    
    def validate_expiry_date(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Expiry date cannot be in the past")
        
        # Reset notification status if expiry date changes
        if self.instance and value != self.instance.expiry_date:
            self.instance.expiry_notified = False
            self.instance.last_notification_sent = None
            
        return value

class DocumentUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('title', 'description', 'expiry_date', 'file') 
    
    def validate_expiry_date(self, value):
        if value and value < timezone.now():
            raise serializers.ValidationError("Expiry date cannot be in the past")
        
        # Reset notification status if expiry date changes
        if self.instance and value != self.instance.expiry_date:
            self.instance.expiry_notified = False
            self.instance.last_notification_sent = None
            
        return value
    def update(self, instance, validated_data):
        instance.title = validated_data.get('title', instance.title)
        instance.description = validated_data.get('description', instance.description)
        instance.expiry_date = validated_data.get('expiry_date', instance.expiry_date)

        if 'file' in validated_data:
            # ✅ Delete old file
            if instance.file:
                instance.file.delete(save=False)

            # ✅ Set new file and update metadata
            instance.file = validated_data['file']
            instance._set_file_metadata()

        instance.save()
        return instance