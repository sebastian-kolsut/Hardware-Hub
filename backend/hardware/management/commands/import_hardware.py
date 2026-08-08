import json
from collections import Counter
from datetime import date, datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from hardware.models import Hardware

# Fields we map onto real columns; anything else in a source record is kept
# verbatim in Hardware.extra so nothing gets silently dropped on import.
KNOWN_FIELDS = {'id', 'name', 'brand', 'purchaseDate', 'status'}

STATUS_BY_LABEL = {label.lower(): value for value, label in Hardware.Status.choices}


def parse_purchase_date(raw):
    """Returns (parsed_date_or_None, was_iso_formatted)."""
    if not raw:
        return None, False
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date(), True
    except ValueError:
        pass
    # Best-effort fallback for the DD-MM-YYYY shape seen in the wild — still
    # flagged as an anomaly below, but this gives the reviewer a starting value.
    try:
        return datetime.strptime(raw, '%d-%m-%Y').date(), False
    except ValueError:
        return None, False


class Command(BaseCommand):
    help = (
        'Import hardware records from data.json, flagging duplicate ids, '
        'inconsistent/missing/future dates, unrecognized statuses, and any '
        'mention of "unknown" for manual review in the admin.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            default=str(settings.REPO_ROOT / 'data.json'),
            help='Path to the source JSON file (defaults to data.json at the repo root).',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and report anomalies without writing anything to the database.',
        )

    def handle(self, *args, file, dry_run, **options):
        records = self._load_records(file)

        valid_records = []
        for i, record in enumerate(records):
            if not isinstance(record, dict):
                self.stdout.write(self.style.ERROR(f'  skipping entry {i}: not a JSON object ({record!r})'))
                continue
            valid_records.append(record)

        external_ids = [record.get('id') for record in valid_records]
        duplicate_ids = {i for i, count in Counter(external_ids).items() if count > 1}

        rows = []
        for record in valid_records:
            hw, reasons = self._build_row(record, duplicate_ids)
            rows.append((record.get('id'), hw, reasons))

        flagged_count = sum(1 for _, _, reasons in rows if reasons)
        self.stdout.write(f'Parsed {len(rows)} records, {flagged_count} flagged for review.')
        for external_id, hw, reasons in rows:
            if reasons:
                self.stdout.write(
                    self.style.WARNING(f'  external_id={external_id} "{hw.name}": {"; ".join(reasons)}')
                )

        if dry_run:
            self.stdout.write(self.style.NOTICE('Dry run — nothing written to the database.'))
            return

        Hardware.objects.all().delete()
        Hardware.objects.bulk_create(hw for _, hw, _ in rows)
        self.stdout.write(
            self.style.SUCCESS(f'Imported {len(rows)} hardware records ({flagged_count} need review).')
        )

    def _load_records(self, file):
        try:
            with open(file) as f:
                data = json.load(f)
        except FileNotFoundError:
            raise CommandError(f'No such file: {file}')
        except json.JSONDecodeError as exc:
            raise CommandError(f'{file} is not valid JSON: {exc}')

        if not isinstance(data, list):
            raise CommandError(
                f'{file} must contain a JSON array of records at the top level, got {type(data).__name__}.'
            )
        return data

    def _build_row(self, record, duplicate_ids):
        reasons = []

        external_id = record.get('id')
        name = (record.get('name') or '').strip()
        brand = (record.get('brand') or '').strip()
        raw_status = record.get('status')
        raw_date = record.get('purchaseDate')

        if not name:
            reasons.append('missing name')

        if external_id in duplicate_ids:
            reasons.append(f'duplicate id {external_id!r} in source file')

        parsed_date, is_iso = parse_purchase_date(raw_date)
        if raw_date is None:
            reasons.append('missing purchase date')
        elif parsed_date is None:
            reasons.append(f'unparseable purchase date {raw_date!r}')
        elif not is_iso:
            reasons.append(f'inconsistent date format {raw_date!r}')
        if parsed_date and parsed_date > date.today():
            reasons.append(f'purchase date in the future ({parsed_date.isoformat()})')

        status_value = STATUS_BY_LABEL.get((raw_status or '').strip().lower())
        if not status_value:
            reasons.append(f'unrecognized status {raw_status!r}')

        haystack = ' '.join(str(v) for v in record.values() if isinstance(v, str))
        if 'unknown' in haystack.lower():
            reasons.append('record mentions "unknown" somewhere')

        extra = {k: v for k, v in record.items() if k not in KNOWN_FIELDS}

        hw = Hardware(
            name=name or '(unnamed)',
            brand=brand,
            purchase_date=parsed_date,
            status=status_value or '',
            external_id=external_id,
            extra=extra,
            needs_review=bool(reasons),
            review_notes='; '.join(reasons),
        )
        return hw, reasons
