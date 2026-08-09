from django.contrib import admin

from .models import Hardware


@admin.register(Hardware)
class HardwareAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'brand', 'purchase_date', 'status', 'needs_review', 'external_id', 'has_embedding',
    )
    list_filter = ('needs_review', 'status', 'brand')
    search_fields = ('name', 'brand', 'external_id', 'review_notes')
    readonly_fields = ('external_id', 'extra', 'embedding', 'created_at', 'updated_at')
    ordering = ('-needs_review', 'name')

    @admin.display(boolean=True, description='Has embedding')
    def has_embedding(self, obj):
        return obj.embedding is not None
