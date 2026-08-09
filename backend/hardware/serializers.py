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
    # Whether the requesting user is the current renter — not who the renter
    # actually is, so the list endpoint doesn't leak other users' identities
    # to every authenticated viewer. Enough for the frontend to decide
    # whether to show a Return button.
    rented_by_me = serializers.SerializerMethodField()

    class Meta:
        model = Hardware
        fields = ['id', 'name', 'brand', 'purchase_date', 'status', 'rented_by_me']

    def get_rented_by_me(self, obj):
        request = self.context.get('request')
        return bool(
            request and request.user.is_authenticated and obj.rented_by_id == request.user.id
        )
