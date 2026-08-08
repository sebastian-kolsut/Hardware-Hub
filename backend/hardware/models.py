from django.db import models


class HardwareQuerySet(models.QuerySet):
    def clean(self):
        """Records safe to show outside the admin (no anomalies found on import)."""
        return self.filter(needs_review=False)

    def needs_review_only(self):
        return self.filter(needs_review=True)


class Hardware(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = 'available', 'Available'
        IN_USE = 'in_use', 'In Use'
        REPAIR = 'repair', 'Repair'

    name = models.CharField(max_length=255)
    brand = models.CharField(max_length=255, blank=True)
    purchase_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, blank=True)

    external_id = models.IntegerField(
        null=True,
        blank=True,
        help_text=(
            'id from the source data.json this row was imported from. '
            "Not a database key — duplicates are expected and don't collide with anything."
        ),
    )
    extra = models.JSONField(
        blank=True,
        default=dict,
        help_text='Any source fields not mapped to a column above (notes, assignedTo, history, ...).',
    )

    needs_review = models.BooleanField(default=False)
    review_notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = HardwareQuerySet.as_manager()

    def __str__(self):
        return self.name
