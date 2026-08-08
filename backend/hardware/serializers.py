from rest_framework import serializers

from .models import Hardware

STATUS_BY_LABEL = {label.lower(): value for value, label in Hardware.Status.choices}


class HardwareStatusField(serializers.CharField):
    """Reads/writes status as its human-readable label ("Repair", "Available", ...)
    while the model stores the internal value ("repair", "available", ...)."""

    def to_representation(self, value):
        return Hardware.Status(value).label if value else value

    def to_internal_value(self, data):
        label = super().to_internal_value(data)
        value = STATUS_BY_LABEL.get(label.strip().lower())
        if not value:
            raise serializers.ValidationError(f'"{data}" is not a valid status.')
        return value


class HardwareSerializer(serializers.ModelSerializer):
    status = HardwareStatusField()

    class Meta:
        model = Hardware
        fields = ['id', 'name', 'brand', 'purchase_date', 'status']
