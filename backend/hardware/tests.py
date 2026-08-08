import json
import os
import tempfile
from datetime import date, timedelta
from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from .models import Hardware


def run_import(payload, dry_run=False):
    """Write `payload` to a temp file and run the import command against it.

    `payload` is written as-is if it's a string (for malformed-JSON tests),
    otherwise it's JSON-serialized (the normal case: a list of record dicts).
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        if isinstance(payload, str):
            f.write(payload)
        else:
            json.dump(payload, f)
        path = f.name

    args = ['--file', path]
    if dry_run:
        args.append('--dry-run')
    try:
        return call_command('import_hardware', *args, stdout=StringIO())
    finally:
        os.unlink(path)


class AnomalyDetectionTests(TestCase):
    def test_clean_record_imports_without_review(self):
        run_import([
            {'id': 1, 'name': 'Widget', 'brand': 'Acme', 'purchaseDate': '2022-01-01', 'status': 'Available'},
        ])
        hw = Hardware.objects.get()
        self.assertFalse(hw.needs_review)
        self.assertEqual(hw.review_notes, '')
        self.assertEqual(hw.purchase_date, date(2022, 1, 1))
        self.assertEqual(hw.status, Hardware.Status.AVAILABLE)

    def test_external_id_is_kept_separate_from_the_primary_key(self):
        run_import([
            {'id': 999, 'name': 'Widget', 'brand': 'Acme', 'purchaseDate': '2022-01-01', 'status': 'Available'},
        ])
        hw = Hardware.objects.get()
        self.assertEqual(hw.external_id, 999)
        self.assertNotEqual(hw.pk, 999)

    def test_duplicate_ids_are_both_flagged_with_distinct_primary_keys(self):
        run_import([
            {'id': 4, 'name': 'First', 'brand': 'A', 'purchaseDate': '2022-01-01', 'status': 'Available'},
            {'id': 4, 'name': 'Second', 'brand': 'B', 'purchaseDate': '2022-01-01', 'status': 'Available'},
        ])
        rows = list(Hardware.objects.filter(external_id=4).order_by('name'))
        self.assertEqual(len(rows), 2)
        for hw in rows:
            self.assertTrue(hw.needs_review)
            self.assertIn('duplicate id', hw.review_notes)
        self.assertNotEqual(rows[0].pk, rows[1].pk)

    def test_unique_id_is_not_flagged_as_duplicate(self):
        run_import([{'id': 1, 'name': 'A', 'brand': 'A', 'purchaseDate': '2022-01-01', 'status': 'Available'}])
        hw = Hardware.objects.get()
        self.assertNotIn('duplicate', hw.review_notes)

    def test_inconsistent_date_format_is_flagged_but_still_parsed(self):
        run_import([{'id': 1, 'name': 'A', 'brand': 'A', 'purchaseDate': '22-05-2023', 'status': 'Available'}])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        self.assertIn('inconsistent date format', hw.review_notes)
        self.assertEqual(hw.purchase_date, date(2023, 5, 22))

    def test_unparseable_date_is_flagged_and_left_null(self):
        run_import([{'id': 1, 'name': 'A', 'brand': 'A', 'purchaseDate': 'not-a-date', 'status': 'Available'}])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        self.assertIn('unparseable purchase date', hw.review_notes)
        self.assertIsNone(hw.purchase_date)

    def test_null_purchase_date_is_flagged(self):
        run_import([{'id': 1, 'name': 'A', 'brand': 'A', 'purchaseDate': None, 'status': 'Available'}])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        self.assertIn('missing purchase date', hw.review_notes)
        self.assertIsNone(hw.purchase_date)

    def test_future_purchase_date_is_flagged(self):
        future = (date.today() + timedelta(days=365)).isoformat()
        run_import([{'id': 1, 'name': 'A', 'brand': 'A', 'purchaseDate': future, 'status': 'Available'}])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        self.assertIn('purchase date in the future', hw.review_notes)
        self.assertEqual(hw.purchase_date.isoformat(), future)

    def test_unrecognized_status_is_flagged_and_left_blank(self):
        run_import([{'id': 1, 'name': 'A', 'brand': 'A', 'purchaseDate': '2022-01-01', 'status': 'Unknown'}])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        self.assertIn('unrecognized status', hw.review_notes)
        self.assertEqual(hw.status, '')

    def test_word_unknown_anywhere_in_the_record_is_flagged(self):
        run_import([{
            'id': 1, 'name': 'Totally Unknown Gadget', 'brand': 'Acme',
            'purchaseDate': '2022-01-01', 'status': 'Available',
        }])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        self.assertIn('unknown', hw.review_notes)

    def test_missing_name_is_flagged(self):
        run_import([{'id': 1, 'name': '', 'brand': 'A', 'purchaseDate': '2022-01-01', 'status': 'Available'}])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        self.assertIn('missing name', hw.review_notes)
        self.assertEqual(hw.name, '(unnamed)')

    def test_record_with_every_anomaly_records_all_of_them(self):
        run_import([{'id': 10, 'name': 'Unknown Device', 'brand': '', 'purchaseDate': None, 'status': 'Unknown'}])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        for fragment in ('missing purchase date', 'unrecognized status', 'unknown'):
            self.assertIn(fragment, hw.review_notes)


class StructurallyInvalidInputTests(TestCase):
    def test_additional_unexpected_keys_are_preserved_and_not_flagged(self):
        run_import([{
            'id': 1, 'name': 'A', 'brand': 'A', 'purchaseDate': '2022-01-01', 'status': 'Available',
            'serialNumber': 'XZ-42', 'warrantyExpires': '2025-01-01',
        }])
        hw = Hardware.objects.get()
        self.assertFalse(hw.needs_review)
        self.assertEqual(hw.extra, {'serialNumber': 'XZ-42', 'warrantyExpires': '2025-01-01'})

    def test_missing_required_keys_entirely_are_treated_like_missing_values(self):
        # No 'name', 'purchaseDate', or 'status' keys at all — not just empty/null values.
        run_import([{'id': 1, 'brand': 'A'}])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        self.assertIn('missing name', hw.review_notes)
        self.assertIn('missing purchase date', hw.review_notes)
        self.assertIn('unrecognized status', hw.review_notes)

    def test_missing_id_key_has_no_external_id_and_is_not_a_false_duplicate(self):
        run_import([{'name': 'A', 'brand': 'A', 'purchaseDate': '2022-01-01', 'status': 'Available'}])
        hw = Hardware.objects.get()
        self.assertIsNone(hw.external_id)
        self.assertNotIn('duplicate', hw.review_notes)

    def test_completely_empty_record_does_not_crash(self):
        run_import([{}])
        hw = Hardware.objects.get()
        self.assertTrue(hw.needs_review)
        self.assertEqual(hw.name, '(unnamed)')

    def test_non_object_array_entries_are_skipped_not_crashed(self):
        run_import([
            'this is not a hardware record',
            42,
            {'id': 1, 'name': 'A', 'brand': 'A', 'purchaseDate': '2022-01-01', 'status': 'Available'},
        ])
        self.assertEqual(Hardware.objects.count(), 1)

    def test_malformed_json_syntax_raises_a_clear_error_and_writes_nothing(self):
        with self.assertRaises(CommandError):
            run_import('{ this is not valid json ]')
        self.assertEqual(Hardware.objects.count(), 0)

    def test_top_level_object_instead_of_array_raises_a_clear_error(self):
        with self.assertRaises(CommandError):
            run_import({'id': 1, 'name': 'A'})
        self.assertEqual(Hardware.objects.count(), 0)

    def test_missing_file_raises_a_clear_error(self):
        with self.assertRaises(CommandError):
            call_command('import_hardware', '--file', '/no/such/file.json', stdout=StringIO())


class ImportBehaviorTests(TestCase):
    def test_dry_run_does_not_write_to_the_database(self):
        run_import(
            [{'id': 1, 'name': 'A', 'brand': 'A', 'purchaseDate': '2022-01-01', 'status': 'Available'}],
            dry_run=True,
        )
        self.assertEqual(Hardware.objects.count(), 0)

    def test_rerunning_import_replaces_previous_data(self):
        run_import([{'id': 1, 'name': 'First run', 'brand': 'A', 'purchaseDate': '2022-01-01', 'status': 'Available'}])
        self.assertEqual(Hardware.objects.count(), 1)

        run_import([{'id': 2, 'name': 'Second run', 'brand': 'B', 'purchaseDate': '2022-01-01', 'status': 'Available'}])
        self.assertEqual(Hardware.objects.count(), 1)
        self.assertEqual(Hardware.objects.get().name, 'Second run')
