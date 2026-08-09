import json
import os
import tempfile
from datetime import date, timedelta
from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from .models import Hardware

User = get_user_model()


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


class PublicHardwareAPITests(APITestCase):
    """The /api/hardware/ list must never leak records still needing review —
    those are only ever meant to be seen (and fixed) in /admin/."""

    def setUp(self):
        self.clean = Hardware.objects.create(
            name='Clean Laptop', brand='Dell', purchase_date=date(2022, 1, 1),
            status=Hardware.Status.AVAILABLE, external_id=1,
        )
        self.flagged = Hardware.objects.create(
            name='Flagged Laptop', brand='Dell', purchase_date=None,
            status='', external_id=2, needs_review=True, review_notes='missing purchase date',
        )
        user = User.objects.create_user('viewer', password='viewerpass123')
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=user).key}')

    def test_anonymous_request_is_rejected(self):
        self.client.credentials()
        response = self.client.get('/api/hardware/')
        self.assertEqual(response.status_code, 401)

    def test_only_clean_records_are_returned(self):
        response = self.client.get('/api/hardware/')
        self.assertEqual(response.status_code, 200)
        names = {row['name'] for row in response.json()}
        self.assertIn('Clean Laptop', names)
        self.assertNotIn('Flagged Laptop', names)

    def test_flagged_only_fields_are_not_exposed(self):
        response = self.client.get('/api/hardware/')
        row = response.json()[0]
        self.assertNotIn('needs_review', row)
        self.assertNotIn('review_notes', row)
        self.assertNotIn('external_id', row)

    def test_status_is_returned_as_a_human_readable_label(self):
        response = self.client.get('/api/hardware/')
        row = response.json()[0]
        self.assertEqual(row['status'], 'Available')


class ManagementEndpointPermissionsTests(APITestCase):
    """Create/update/delete hardware and creating user accounts are admin-only:
    401 with no token, 403 for an authenticated non-staff user, success for staff."""

    def setUp(self):
        self.admin = User.objects.create_user('admin', password='adminpass123', is_staff=True)
        self.regular = User.objects.create_user('regular', password='regularpass123')
        self.admin_token = Token.objects.create(user=self.admin).key
        self.regular_token = Token.objects.create(user=self.regular).key
        self.hw = Hardware.objects.create(
            name='Old Laptop', brand='Dell', purchase_date=date(2022, 1, 1),
            status=Hardware.Status.AVAILABLE, external_id=5,
        )

    def _hit_all_four(self):
        return [
            self.client.post('/api/hardware/', {'name': 'X', 'status': 'Available'}),
            self.client.patch(f'/api/hardware/{self.hw.pk}/', {'status': 'Repair'}),
            self.client.delete(f'/api/hardware/{self.hw.pk}/'),
            self.client.post('/api/auth/users/', {'username': 'newperson', 'password': 'somepassword123'}),
        ]

    def test_unauthenticated_gets_401_on_all_four_endpoints(self):
        for response in self._hit_all_four():
            self.assertEqual(response.status_code, 401)

    def test_regular_user_gets_403_on_all_four_endpoints(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.regular_token}')
        for response in self._hit_all_four():
            self.assertEqual(response.status_code, 403)

    def test_admin_succeeds_on_all_four_endpoints(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token}')

        create_response = self.client.post(
            '/api/hardware/', {'name': 'New Laptop', 'brand': 'HP', 'status': 'Available'}
        )
        self.assertEqual(create_response.status_code, 201)
        new_id = create_response.json()['id']

        patch_response = self.client.patch(f'/api/hardware/{new_id}/', {'status': 'Repair'})
        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(patch_response.json()['status'], 'Repair')

        delete_response = self.client.delete(f'/api/hardware/{new_id}/')
        self.assertEqual(delete_response.status_code, 204)
        self.assertFalse(Hardware.objects.filter(pk=new_id).exists())

        user_response = self.client.post(
            '/api/auth/users/', {'username': 'newperson', 'password': 'somepassword123'}
        )
        self.assertEqual(user_response.status_code, 201)
        self.assertTrue(User.objects.filter(username='newperson').exists())
        self.assertFalse(User.objects.get(username='newperson').is_staff)

    def test_creating_hardware_with_missing_required_field_fails_validation(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.admin_token}')
        response = self.client.post('/api/hardware/', {'brand': 'HP'})
        self.assertEqual(response.status_code, 400)
        self.assertIn('name', response.json())
        self.assertIn('status', response.json())


class RentReturnTests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user('rr_admin', password='adminpass123', is_staff=True)
        self.renter = User.objects.create_user('rr_renter', password='renterpass123')
        self.other = User.objects.create_user('rr_other', password='otherpass123')

        self.available = Hardware.objects.create(
            name='Available Laptop', brand='Dell', status=Hardware.Status.AVAILABLE,
        )
        self.in_use = Hardware.objects.create(
            name='In-Use Laptop', brand='Dell', status=Hardware.Status.IN_USE,
        )
        self.in_repair = Hardware.objects.create(
            name='Broken Laptop', brand='Dell', status=Hardware.Status.REPAIR,
        )
        self.flagged_but_available = Hardware.objects.create(
            name='Flagged Laptop', brand='Dell', status=Hardware.Status.AVAILABLE,
            needs_review=True, review_notes='missing purchase date',
        )

    def as_(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=user).key}')

    def test_renting_available_item_succeeds(self):
        self.as_(self.renter)
        response = self.client.post(f'/api/hardware/{self.available.pk}/rent/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'In Use')
        self.assertTrue(response.json()['rented_by_me'])

        self.available.refresh_from_db()
        self.assertEqual(self.available.status, Hardware.Status.IN_USE)
        self.assertEqual(self.available.rented_by, self.renter)
        self.assertIsNotNone(self.available.rented_at)

    def test_rented_by_me_is_false_for_other_users(self):
        self.as_(self.renter)
        self.client.post(f'/api/hardware/{self.available.pk}/rent/')

        self.as_(self.other)
        response = self.client.get('/api/hardware/')
        row = next(r for r in response.json() if r['id'] == self.available.pk)
        self.assertFalse(row['rented_by_me'])

    def test_renter_username_is_hidden_from_other_regular_users(self):
        self.as_(self.renter)
        self.client.post(f'/api/hardware/{self.available.pk}/rent/')

        self.as_(self.other)
        response = self.client.get('/api/hardware/')
        # Not just the field — the username must not appear anywhere in the
        # payload, since a regular user could otherwise read it off the raw
        # response regardless of which field it showed up in.
        self.assertNotIn(self.renter.username, response.content.decode())

        row = next(r for r in response.json() if r['id'] == self.available.pk)
        self.assertIsNone(row['rented_by'])

    def test_renter_can_see_their_own_username(self):
        self.as_(self.renter)
        self.client.post(f'/api/hardware/{self.available.pk}/rent/')

        response = self.client.get('/api/hardware/')
        row = next(r for r in response.json() if r['id'] == self.available.pk)
        self.assertEqual(row['rented_by'], self.renter.username)

    def test_admin_can_see_renter_username(self):
        self.as_(self.renter)
        self.client.post(f'/api/hardware/{self.available.pk}/rent/')

        self.as_(self.admin)
        response = self.client.get('/api/hardware/')
        row = next(r for r in response.json() if r['id'] == self.available.pk)
        self.assertEqual(row['rented_by'], self.renter.username)

    def test_renting_already_rented_item_fails(self):
        self.as_(self.other)
        response = self.client.post(f'/api/hardware/{self.in_use.pk}/rent/')
        self.assertEqual(response.status_code, 409)
        self.assertIn('already rented', response.json()['detail'])

        self.in_use.refresh_from_db()
        self.assertIsNone(self.in_use.rented_by)

    def test_renting_item_in_repair_fails(self):
        self.as_(self.renter)
        response = self.client.post(f'/api/hardware/{self.in_repair.pk}/rent/')
        self.assertEqual(response.status_code, 409)
        self.assertIn('repair', response.json()['detail'])

    def test_renting_flagged_item_fails_even_though_status_is_available(self):
        self.as_(self.renter)
        response = self.client.post(f'/api/hardware/{self.flagged_but_available.pk}/rent/')
        self.assertEqual(response.status_code, 409)
        self.assertIn('flagged', response.json()['detail'])

        self.flagged_but_available.refresh_from_db()
        self.assertIsNone(self.flagged_but_available.rented_by)
        self.assertEqual(self.flagged_but_available.status, Hardware.Status.AVAILABLE)

    def test_unauthenticated_cannot_rent(self):
        response = self.client.post(f'/api/hardware/{self.available.pk}/rent/')
        self.assertEqual(response.status_code, 401)

    def test_returning_by_renting_user_succeeds(self):
        self.as_(self.renter)
        self.client.post(f'/api/hardware/{self.available.pk}/rent/')

        response = self.client.post(f'/api/hardware/{self.available.pk}/return/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'Available')
        self.assertFalse(response.json()['rented_by_me'])

        self.available.refresh_from_db()
        self.assertEqual(self.available.status, Hardware.Status.AVAILABLE)
        self.assertIsNone(self.available.rented_by)
        self.assertIsNone(self.available.rented_at)

    def test_returning_by_different_regular_user_fails_with_403(self):
        self.as_(self.renter)
        self.client.post(f'/api/hardware/{self.available.pk}/rent/')

        self.as_(self.other)
        response = self.client.post(f'/api/hardware/{self.available.pk}/return/')
        self.assertEqual(response.status_code, 403)

        self.available.refresh_from_db()
        self.assertEqual(self.available.status, Hardware.Status.IN_USE)
        self.assertEqual(self.available.rented_by, self.renter)

    def test_returning_by_admin_succeeds_regardless_of_renter(self):
        self.as_(self.renter)
        self.client.post(f'/api/hardware/{self.available.pk}/rent/')

        self.as_(self.admin)
        response = self.client.post(f'/api/hardware/{self.available.pk}/return/')
        self.assertEqual(response.status_code, 200)

        self.available.refresh_from_db()
        self.assertEqual(self.available.status, Hardware.Status.AVAILABLE)
        self.assertIsNone(self.available.rented_by)

    def test_returning_item_that_was_never_rented_fails_cleanly(self):
        self.as_(self.renter)
        response = self.client.post(f'/api/hardware/{self.available.pk}/return/')
        self.assertEqual(response.status_code, 409)
        self.assertIn('not currently rented', response.json()['detail'])

        self.available.refresh_from_db()
        self.assertEqual(self.available.status, Hardware.Status.AVAILABLE)


class NeedsReviewVisibilityTests(APITestCase):
    """Flagged items stay invisible to regular users everywhere, but admins
    should see them in the main list (sorted first) and be able to clear the
    flag from there instead of only through /admin/."""

    def setUp(self):
        self.admin = User.objects.create_user('nr_admin', password='adminpass123', is_staff=True)
        self.regular = User.objects.create_user('nr_regular', password='regularpass123')

        self.clean_a = Hardware.objects.create(
            name='Aardvark Laptop', brand='Dell', status=Hardware.Status.AVAILABLE,
        )
        self.clean_z = Hardware.objects.create(
            name='Zebra Laptop', brand='Dell', status=Hardware.Status.AVAILABLE,
        )
        self.flagged = Hardware.objects.create(
            name='Middle Laptop', brand='Dell', status=Hardware.Status.AVAILABLE,
            needs_review=True, review_notes='missing purchase date',
        )

    def as_(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=user).key}')

    def test_regular_user_never_sees_flagged_items(self):
        self.as_(self.regular)
        response = self.client.get('/api/hardware/')
        ids = [row['id'] for row in response.json()]
        self.assertNotIn(self.flagged.pk, ids)
        self.assertNotIn('needs_review', response.json()[0])

    def test_admin_sees_flagged_items_sorted_first(self):
        self.as_(self.admin)
        response = self.client.get('/api/hardware/')
        rows = response.json()

        ids = [row['id'] for row in rows]
        self.assertIn(self.flagged.pk, ids)
        self.assertEqual(rows[0]['id'], self.flagged.pk)
        self.assertTrue(rows[0]['needs_review'])
        self.assertEqual(rows[0]['review_notes'], 'missing purchase date')

    def test_clearing_needs_review_makes_item_visible_to_regular_users(self):
        self.as_(self.admin)
        patch_response = self.client.patch(
            f'/api/hardware/{self.flagged.pk}/', {'needs_review': False}
        )
        self.assertEqual(patch_response.status_code, 200)
        self.flagged.refresh_from_db()
        self.assertFalse(self.flagged.needs_review)

        self.as_(self.regular)
        response = self.client.get('/api/hardware/')
        ids = [row['id'] for row in response.json()]
        self.assertIn(self.flagged.pk, ids)

    def test_admin_can_fix_fields_and_clear_needs_review_in_one_patch(self):
        self.as_(self.admin)
        response = self.client.patch(f'/api/hardware/{self.flagged.pk}/', {
            'name': 'Fixed Laptop',
            'brand': 'HP',
            'purchase_date': '2022-06-01',
            'status': 'Repair',
            'needs_review': False,
        })
        self.assertEqual(response.status_code, 200)

        self.flagged.refresh_from_db()
        self.assertEqual(self.flagged.name, 'Fixed Laptop')
        self.assertEqual(self.flagged.brand, 'HP')
        self.assertEqual(self.flagged.purchase_date.isoformat(), '2022-06-01')
        self.assertEqual(self.flagged.status, Hardware.Status.REPAIR)
        self.assertFalse(self.flagged.needs_review)


class MineFilterTests(APITestCase):
    """?mine=true is a hard override of the normal role-based visibility
    rules — it's scoped to "what did I personally rent," full stop."""

    def setUp(self):
        self.admin = User.objects.create_user('mine_admin', password='adminpass123', is_staff=True)
        self.renter = User.objects.create_user('mine_renter', password='renterpass123')
        self.other = User.objects.create_user('mine_other', password='otherpass123')

        self.my_item = Hardware.objects.create(
            name='My Laptop', brand='Dell', status=Hardware.Status.IN_USE, rented_by=self.renter,
        )
        self.other_item = Hardware.objects.create(
            name='Other Laptop', brand='Dell', status=Hardware.Status.IN_USE, rented_by=self.other,
        )
        self.unrented_item = Hardware.objects.create(
            name='Unrented Laptop', brand='Dell', status=Hardware.Status.AVAILABLE,
        )

    def as_(self, user):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {Token.objects.create(user=user).key}')

    def test_mine_filter_returns_only_items_rented_by_the_requesting_user(self):
        self.as_(self.renter)
        response = self.client.get('/api/hardware/?mine=true')
        ids = {row['id'] for row in response.json()}
        self.assertEqual(ids, {self.my_item.pk})

    def test_mine_filter_excludes_items_rented_by_others_even_for_an_admin(self):
        # The admin can normally see every record, but ?mine=true must still
        # be scoped to only what the admin themselves has rented — not what
        # their broader admin visibility would otherwise show.
        admin_item = Hardware.objects.create(
            name='Admin Laptop', brand='Dell', status=Hardware.Status.IN_USE, rented_by=self.admin,
        )
        self.as_(self.admin)
        response = self.client.get('/api/hardware/?mine=true')
        ids = {row['id'] for row in response.json()}
        self.assertEqual(ids, {admin_item.pk})

    def test_mine_filter_is_empty_when_the_user_has_no_rentals(self):
        self.as_(self.admin)
        response = self.client.get('/api/hardware/?mine=true')
        self.assertEqual(response.json(), [])

    def test_mine_filter_still_hides_flagged_items_from_regular_users(self):
        flagged_and_rented = Hardware.objects.create(
            name='Flagged Rented Laptop', brand='Dell', status=Hardware.Status.IN_USE,
            rented_by=self.renter, needs_review=True, review_notes='data issue',
        )
        self.as_(self.renter)
        response = self.client.get('/api/hardware/?mine=true')
        ids = {row['id'] for row in response.json()}
        self.assertNotIn(flagged_and_rented.pk, ids)
