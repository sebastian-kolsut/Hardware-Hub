from django.core.management.base import BaseCommand

from hardware.embeddings import EmbeddingError, embed_text
from hardware.models import Hardware


class Command(BaseCommand):
    help = (
        "Backfills embeddings for hardware rows that don't have one yet — "
        'notably everything loaded via import_hardware, since bulk_create() '
        "bypasses save() (and the embedding computation hooked into it). "
        'Skips rows that already have an embedding unless --force is passed.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Recompute embeddings even for rows that already have one.',
        )

    def handle(self, *args, force, **options):
        queryset = Hardware.objects.all()
        if not force:
            queryset = queryset.filter(embedding__isnull=True)

        total = queryset.count()
        if total == 0:
            self.stdout.write('Nothing to do — every row already has an embedding.')
            return

        succeeded = 0
        failed = 0
        for hw in queryset.iterator():
            text = hw.embedding_source_text()
            if not text:
                self.stdout.write(self.style.WARNING(f'  skipping "{hw}" (id={hw.pk}): nothing to embed'))
                continue

            try:
                vector = embed_text(text)
            except EmbeddingError as exc:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  failed for "{hw}" (id={hw.pk}): {exc}'))
                continue

            Hardware.objects.filter(pk=hw.pk).update(embedding=vector)
            succeeded += 1

        self.stdout.write(
            self.style.SUCCESS(f'Computed embeddings for {succeeded}/{total} rows ({failed} failed).')
        )
