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
    # The renter's username, but only for an admin or the renter themselves.
    # Omitted (None) for everyone else — enforced here, not in the frontend,
    # since the field simply isn't in the payload for anyone not entitled to it.
    rented_by = serializers.SerializerMethodField()
    # Explanation of why the import flagged this row — informational only;
    # fixed by correcting the underlying field(s) and clearing needs_review,
    # not by editing this text directly.
    review_notes = serializers.CharField(read_only=True)

    class Meta:
        model = Hardware
        fields = [
            'id', 'name', 'brand', 'purchase_date', 'status',
            'rented_by_me', 'rented_by', 'needs_review', 'review_notes',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # needs_review/review_notes only ever make sense to someone who can
        # act on them — pop them entirely for non-admins rather than just
        # not rendering them client-side, so a regular user has no way to
        # read them straight off the API response either.
        request = self.context.get('request')
        is_admin = bool(request and request.user.is_authenticated and request.user.is_staff)
        if not is_admin:
            self.fields.pop('needs_review', None)
            self.fields.pop('review_notes', None)

    def get_rented_by_me(self, obj):
        request = self.context.get('request')
        return bool(
            request and request.user.is_authenticated and obj.rented_by_id == request.user.id
        )

    def get_rented_by(self, obj):
        request = self.context.get('request')
        if not obj.rented_by_id or not request or not request.user.is_authenticated:
            return None
        user = request.user
        if user.is_staff or obj.rented_by_id == user.id:
            return obj.rented_by.username
        return None
