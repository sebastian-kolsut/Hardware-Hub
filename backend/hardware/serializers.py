from rest_framework import serializers

from .models import Hardware


class HardwareSerializer(serializers.ModelSerializer):
    status = serializers.CharField(source='get_status_display')

    class Meta:
        model = Hardware
        fields = ['id', 'name', 'brand', 'purchase_date', 'status']
