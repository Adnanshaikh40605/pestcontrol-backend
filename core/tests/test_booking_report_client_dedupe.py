from django.contrib.auth.models import User
from django.db import IntegrityError, connection
from django.test import TestCase
from rest_framework.test import APIClient

from core.booking_report_dedupe import choose_keeper, dedupe_booking_report_clients, normalize_mobile
from core.models import BookingReportClient, BookingReportClientRemark
from core.roles import ensure_user_profile


class BookingReportClientDedupeTests(TestCase):
    def test_normalize_mobile_strips_country_code(self):
        self.assertEqual(normalize_mobile('+91 98765-43210'), '9876543210')
        self.assertEqual(normalize_mobile('9876543210'), '9876543210')

    def test_choose_keeper_prefers_remarks_then_name(self):
        a = BookingReportClient(id=1, name='+919876543210', mobile='9876543210')
        b = BookingReportClient(id=2, name='Mahesh Patil', mobile='9876543210')
        a._remarks_len = 0
        b._remarks_len = 1
        self.assertEqual(choose_keeper([a, b]).id, 2)

        a._remarks_len = 0
        b._remarks_len = 0
        self.assertEqual(choose_keeper([a, b]).id, 2)

    def _drop_mobile_unique(self):
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT conname
                FROM pg_constraint
                WHERE conrelid = 'core_bookingreportclient'::regclass
                  AND contype = 'u'
                  AND pg_get_constraintdef(oid) ILIKE '%%mobile%%'
                """
            )
            for (conname,) in cursor.fetchall():
                cursor.execute(f'ALTER TABLE core_bookingreportclient DROP CONSTRAINT IF EXISTS "{conname}"')
            cursor.execute('DROP INDEX IF EXISTS core_bookin_mobile_77cf6b_idx')

    def test_dedupe_merges_duplicates_and_moves_remarks(self):
        junk = BookingReportClient.objects.create(
            name='+919876543210', mobile='9111111111', city='Mumbai'
        )
        good = BookingReportClient.objects.create(
            name='Mahesh Patil', mobile='9222222222', city='Mumbai'
        )
        self._drop_mobile_unique()
        BookingReportClient.objects.filter(pk__in=[junk.pk, good.pk]).update(mobile='9876543210')

        user = User.objects.create_user(username='9000000001', password='x')
        # Remark on the junk-named row; keeper will be that row (more remarks),
        # then name is upgraded to the better display name.
        BookingReportClientRemark.objects.create(client=junk, remark='Call back', created_by=user)

        result = dedupe_booking_report_clients(dry_run=False)
        self.assertEqual(result['remaining_duplicate_groups'], 0)
        self.assertEqual(BookingReportClient.objects.filter(mobile='9876543210').count(), 1)
        kept = BookingReportClient.objects.get(mobile='9876543210')
        self.assertEqual(kept.name, 'Mahesh Patil')
        self.assertEqual(kept.remarks.count(), 1)
        self.assertEqual(kept.pk, junk.pk)
        self.assertEqual(result['deleted_rows'], 1)

    def test_unique_mobile_enforced(self):
        BookingReportClient.objects.create(name='A', mobile='9123456780', city='Pune')
        with self.assertRaises(IntegrityError):
            BookingReportClient.objects.create(name='B', mobile='9123456780', city='Pune')


class BookingReportClientAPIDedupeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='9000000002', password='x', is_staff=True, is_superuser=True
        )
        ensure_user_profile(self.user)
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_list_returns_unique_mobiles(self):
        BookingReportClient.objects.create(name='One', mobile='9000000001', city='Mumbai')
        BookingReportClient.objects.create(name='Two', mobile='9000000002', city='Mumbai')
        resp = self.api.get('/api/booking-report-clients/', {'page_size': 100})
        self.assertEqual(resp.status_code, 200)
        mobiles = [r['mobile'] for r in resp.data['results']]
        self.assertEqual(len(mobiles), len(set(mobiles)))
        self.assertEqual(resp.data['count'], 2)

    def test_retrieve_by_id(self):
        row = BookingReportClient.objects.create(name='One', mobile='9000000003', city='Pune')
        resp = self.api.get(f'/api/booking-report-clients/{row.id}/')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data['mobile'], '9000000003')
