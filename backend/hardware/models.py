import logging

from django.conf import settings
from django.db import models

logger = logging.getLogger(__name__)


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

    # Who currently has this item, if anyone — current state only, no rental
    # history. Cleared back to null on return.
    rented_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='rented_hardware',
    )
    rented_at = models.DateTimeField(null=True, blank=True)

    # Precomputed via the Gemini embedding API from embedding_source_text()
    # (see save() below) — null until computed. Rows created via
    # bulk_create() (the data.json import) never go through save(), so they
    # stay null until `generate_embeddings` backfills them. A null
    # embedding just means "not searchable yet", not an error state.
    embedding = models.JSONField(null=True, blank=True, default=None, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = HardwareQuerySet.as_manager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Captured on load (or initial construction) so save() can tell
        # whether the text that matters for search actually changed,
        # instead of recomputing the embedding on every save — a rent,
        # return, or status toggle shouldn't cost a Gemini API call.
        self._embedding_source_snapshot = self.embedding_source_text()

    def __str__(self):
        return self.name

    def embedding_source_text(self):
        """Text fed to the embedding model: name, brand, and any values in
        `extra` — a note like "Battery swelling" can matter to a search
        just as much as the mapped fields do."""
        parts = [self.name, self.brand]
        if self.extra:
            parts.extend(str(v) for v in self.extra.values())
        return ' '.join(p for p in parts if p).strip()

    def save(self, *args, **kwargs):
        is_new = self._state.adding
        current_text = self.embedding_source_text()
        text_changed = current_text != self._embedding_source_snapshot

        super().save(*args, **kwargs)
        self._embedding_source_snapshot = current_text

        if is_new or text_changed:
            self._refresh_embedding(current_text)

    def _refresh_embedding(self, text):
        if not text:
            return

        from .embeddings import EmbeddingError, embed_text

        try:
            vector = embed_text(text)
        except EmbeddingError as exc:
            logger.warning('Could not compute embedding for Hardware %s: %s', self.pk, exc)
            return

        self.embedding = vector
        # .update() rather than self.save() — avoids re-entering this same
        # save() override (and thus re-embedding) for what is just writing
        # the result of the embedding we already computed.
        Hardware.objects.filter(pk=self.pk).update(embedding=vector)
