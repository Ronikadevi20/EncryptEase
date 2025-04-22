from rest_framework import serializers
from .models import Bill

class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = [
            'id', 'name', 'amount', 'due_date', 'is_paid', 'payment_date',
            'category', 'notes', 'website_url', 'username', 'password_value',
            'created_at', 'updated_at', 'receipt', 'is_deleted', 'deleted_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'is_deleted', 'deleted_at']
        extra_kwargs = {
            'receipt': {'required': False, 'allow_null': True}
        }

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)
    def update(self, instance, validated_data):
        # Handle receipt deletion if client sends "receipt": null or empty string
        if 'receipt' in validated_data:
            if validated_data['receipt'] in [None, '']:
                if instance.receipt:
                    instance.receipt.delete(save=False)
                validated_data['receipt'] = None

        return super().update(instance, validated_data)