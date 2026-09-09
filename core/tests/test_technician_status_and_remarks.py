"""Technician work status (Active / On Leave / Suspended) and remark history.

presence_status used to hold six values that mixed a desk decision with live
app presence, and only 'suspended' actually stopped anything. These tests pin
the collapsed behaviour: three values, one meaning, enforced everywhere, plus
the remark history the CRM edit page writes.
"""

from datetime import date, time
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from core.models import City, Client, Country, JobCard, Location, State, Technician, TechnicianRemark
from core.services import JobCardService
from partner.models import Partner
from partner.services import PartnerBookingError, partner_accept_booking
from partner.utils import generate_partner_tokens


def _selfie_file():
    buf = BytesIO()
    Image.new('RGB', (48, 48), color=(20, 40, 60)).save(buf, format='JPEG')
    return SimpleUploadedFile('start.jpg', buf.getvalue(), content_type='image/jpeg')


class TechnicianStatusChoiceTests(TestCase):
    def test_only_three_statuses_exist(self):
        self.assertEqual(
            [value for value, _label in Technician.PresenceStatus.choices],
            ['active', 'on_leave', 'suspended'],
        )

    def test_new_technicians_start_active(self):
        tech = Technician.objects.create(name='Fresh', mobile='9600000001')
        self.assertEqual(tech.presence_status, Technician.PresenceStatus.ACTIVE)
        self.assertTrue(tech.is_available_for_work)

    def test_on_leave_and_suspended_are_both_unavailable(self):
        for status in (
            Technician.PresenceStatus.ON_LEAVE,
            Technician.PresenceStatus.SUSPENDED,
        ):
            with self.subTest(status=status):
                tech = Technician(presence_status=status, is_active=True)
                self.assertFalse(tech.is_available_for_work)

    def test_deactivated_technician_is_unavailable_even_when_active_status(self):
        """is_active and the status are separate switches; either one blocks."""
        tech = Technician(
            presence_status=Technician.PresenceStatus.ACTIVE, is_active=False
        )
        self.assertFalse(tech.is_available_for_work)


class TechnicianStatusApiTests(TestCase):
    """One backend value, written through the same endpoint the CRM uses."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='statusadmin', email='s@x.com', password='pass12345'
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.tech = Technician.objects.create(
            name='Status Tech',
            mobile='9600000010',
            technician_type=Technician.TechnicianType.PARTNER,
        )

    def _patch(self, **payload):
        return self.api.patch(
            f'/api/technicians/{self.tech.id}/', payload, format='json'
        )

    def test_each_status_round_trips_with_its_label(self):
        for value, label in Technician.PresenceStatus.choices:
            with self.subTest(status=value):
                res = self._patch(presence_status=value)
                self.assertEqual(res.status_code, 200, res.data)
                self.assertEqual(res.data['presence_status'], value)
                self.assertEqual(res.data['presence_label'], label)
                self.tech.refresh_from_db()
                self.assertEqual(self.tech.presence_status, value)

    def test_retired_status_values_are_rejected(self):
        for stale in ('online', 'offline', 'busy', 'on_service'):
            with self.subTest(status=stale):
                res = self._patch(presence_status=stale)
                self.assertEqual(res.status_code, 400, res.data)
                self.tech.refresh_from_db()
                self.assertEqual(
                    self.tech.presence_status, Technician.PresenceStatus.ACTIVE
                )

    def test_suspending_stamps_suspended_at(self):
        res = self._patch(
            presence_status='suspended', suspend_reason='Missing KYC documents'
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.tech.refresh_from_db()
        self.assertIsNotNone(self.tech.suspended_at)
        self.assertEqual(self.tech.suspend_reason, 'Missing KYC documents')
        self.assertFalse(res.data['is_available_for_work'])

    def test_reactivating_stamps_reactivated_at_and_clears_the_reason(self):
        self._patch(presence_status='suspended', suspend_reason='Missing KYC')
        res = self._patch(presence_status='active')
        self.assertEqual(res.status_code, 200, res.data)
        self.tech.refresh_from_db()
        self.assertIsNotNone(self.tech.reactivated_at)
        # A stale suspension reason would otherwise be shown to a technician
        # who is no longer suspended.
        self.assertEqual(self.tech.suspend_reason, '')
        self.assertTrue(res.data['is_available_for_work'])

    def test_the_reason_never_survives_a_status_change(self):
        """A leftover reason would explain the wrong status to the technician."""
        self._patch(presence_status='suspended', suspend_reason='Repeated no-shows')
        self._patch(presence_status='on_leave')
        self.tech.refresh_from_db()
        self.assertEqual(self.tech.suspend_reason, '')

    def test_a_fresh_reason_supplied_with_the_change_is_kept(self):
        self._patch(presence_status='suspended', suspend_reason='Repeated no-shows')
        self._patch(presence_status='on_leave', suspend_reason='Back on 20 Sept')
        self.tech.refresh_from_db()
        self.assertEqual(self.tech.suspend_reason, 'Back on 20 Sept')

    def test_editing_an_unrelated_field_leaves_the_status_alone(self):
        self._patch(presence_status='on_leave')
        res = self._patch(branch='Andheri')
        self.assertEqual(res.status_code, 200, res.data)
        self.tech.refresh_from_db()
        self.assertEqual(
            self.tech.presence_status, Technician.PresenceStatus.ON_LEAVE
        )

    def test_suspended_technicians_are_not_offered_for_assignment(self):
        self._patch(presence_status='suspended')
        res = self.api.get('/api/technicians/active/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertNotIn(self.tech.id, [row['id'] for row in res.data])

    def test_on_leave_technicians_stay_assignable_by_desk_staff(self):
        """Automatic dispatch skips them, but a human may still schedule ahead."""
        self._patch(presence_status='on_leave')
        res = self.api.get('/api/technicians/active/')
        row = next((r for r in res.data if r['id'] == self.tech.id), None)
        self.assertIsNotNone(row, 'on-leave technician should remain listed')
        self.assertEqual(row['presence_status'], 'on_leave')
        self.assertFalse(row['is_available_for_work'])


class TechnicianRemarkApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='remarkadmin', email='r@x.com', password='pass12345'
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.tech = Technician.objects.create(name='Remark Tech', mobile='9600000020')
        self.url = f'/api/technicians/{self.tech.id}/remarks/'

    def test_saving_a_remark_stores_text_date_time_and_author(self):
        res = self.api.post(
            self.url,
            {
                'remark': 'Reached the site 40 minutes late.',
                'remark_date': '2026-09-01',
                'remark_time': '14:30',
            },
            format='json',
        )
        self.assertEqual(res.status_code, 201, res.data)

        remark = TechnicianRemark.objects.get(pk=res.data['id'])
        self.assertEqual(remark.technician_id, self.tech.id)
        self.assertEqual(remark.remark, 'Reached the site 40 minutes late.')
        self.assertEqual(remark.remark_date, date(2026, 9, 1))
        self.assertEqual(remark.remark_time, time(14, 30))
        self.assertEqual(remark.created_by_id, self.user.id)
        # BaseModel's entry timestamp is separate from the date being noted.
        self.assertIsNotNone(remark.created_at)
        self.assertEqual(res.data['created_by_name'], self.user.username)

    def test_date_and_time_default_to_now_when_omitted(self):
        res = self.api.post(self.url, {'remark': 'Quick note'}, format='json')
        self.assertEqual(res.status_code, 201, res.data)
        remark = TechnicianRemark.objects.get(pk=res.data['id'])
        self.assertEqual(remark.remark_date, timezone.localdate())
        self.assertIsNotNone(remark.remark_time)

    def test_blank_remark_is_rejected(self):
        res = self.api.post(self.url, {'remark': '   '}, format='json')
        self.assertEqual(res.status_code, 400, res.data)
        self.assertEqual(TechnicianRemark.objects.count(), 0)

    def test_remarks_come_back_newest_first(self):
        for day, text in ((1, 'oldest'), (15, 'middle'), (28, 'newest')):
            self.api.post(
                self.url,
                {'remark': text, 'remark_date': f'2026-09-{day:02d}', 'remark_time': '09:00'},
                format='json',
            )
        res = self.api.get(self.url)
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual([r['remark'] for r in res.data], ['newest', 'middle', 'oldest'])

    def test_technician_detail_carries_the_history_and_the_latest_remark(self):
        self.api.post(
            self.url,
            {'remark': 'First visit', 'remark_date': '2026-09-01', 'remark_time': '09:00'},
            format='json',
        )
        self.api.post(
            self.url,
            {'remark': 'Latest issue', 'remark_date': '2026-09-05', 'remark_time': '18:15'},
            format='json',
        )
        res = self.api.get(f'/api/technicians/{self.tech.id}/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(len(res.data['remarks']), 2)
        self.assertEqual(res.data['latest_remark']['remark'], 'Latest issue')

    def test_a_remark_can_be_deleted(self):
        created = self.api.post(self.url, {'remark': 'Typed by mistake'}, format='json')
        res = self.api.delete(f'{self.url}{created.data["id"]}/')
        self.assertEqual(res.status_code, 204)
        self.assertEqual(TechnicianRemark.objects.count(), 0)

    def test_remarks_are_scoped_to_their_own_technician(self):
        other = Technician.objects.create(name='Other', mobile='9600000021')
        created = self.api.post(self.url, {'remark': 'Mine'}, format='json')

        res = self.api.get(f'/api/technicians/{other.id}/remarks/')
        self.assertEqual(res.data, [])

        res = self.api.delete(
            f'/api/technicians/{other.id}/remarks/{created.data["id"]}/'
        )
        self.assertEqual(res.status_code, 404)
        self.assertEqual(TechnicianRemark.objects.count(), 1)

    def test_deleting_a_technician_takes_their_remarks_with_it(self):
        self.api.post(self.url, {'remark': 'Note'}, format='json')
        self.tech.delete()
        self.assertEqual(TechnicianRemark.objects.count(), 0)


@override_settings(REVENUE_MODEL_V2=True)
class StatusGatesDispatchTests(TestCase):
    """The status the CRM sets has to reach the partner app and gate work."""

    def setUp(self):
        self.schedule = timezone.localtime(
            timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        )
        self.client_record = Client.objects.create(
            full_name='Status Client', mobile='9888833333'
        )
        country, _ = Country.objects.get_or_create(name='India')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra St')
        self.city, _ = City.objects.get_or_create(state=state, name='Mumbai St')
        self.location, _ = Location.objects.get_or_create(
            city=self.city,
            normalized_name=Location.normalize_text('Bandra'),
            defaults={'name': 'Bandra'},
        )
        self.tech, self.api, self.partner = self._make_tech('Gate Tech', '9600000030')

    def _make_tech(self, name, mobile):
        tech = Technician.objects.create(
            name=name,
            mobile=mobile,
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ACTIVE,
            is_active=True,
        )
        tech.service_cities.add(self.city)
        partner = Partner.objects.create(
            full_name=name,
            mobile=mobile,
            password='x',
            core_technician=tech,
            is_app_approved=True,
            is_active=True,
        )
        partner.set_password('testpass')
        partner.save()
        tokens = generate_partner_tokens(partner)
        api = APIClient()
        api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        return tech, api, partner

    def _broadcast_booking(self):
        with self.captureOnCommitCallbacks(execute=True):
            return JobCardService.create_jobcard(
                {
                    'client': self.client_record.id,
                    'service_type': 'Bed Bugs',
                    'service_category': JobCard.ServiceCategory.ONE_TIME,
                    'schedule_datetime': self.schedule,
                    'price': '5000',
                    'total_amount': Decimal('5000'),
                    'status': JobCard.JobStatus.PENDING,
                    'master_location': self.location.id,
                    'master_city': self.city.id,
                },
                user=None,
            )

    def _set_status(self, status, reason=''):
        self.tech.presence_status = status
        self.tech.suspend_reason = reason
        self.tech.save(update_fields=['presence_status', 'suspend_reason', 'updated_at'])

    def test_active_technician_sees_the_pool(self):
        job = self._broadcast_booking()
        res = self.api.get('/api/partner/bookings/available/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertIn(job.id, [r['id'] for r in res.data['results']])
        self.assertEqual(res.data['presence_status'], 'active')

    def test_on_leave_hides_the_pool_and_explains_why(self):
        self._broadcast_booking()
        self._set_status(Technician.PresenceStatus.ON_LEAVE)

        res = self.api.get('/api/partner/bookings/available/')
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['results'], [])
        self.assertTrue(res.data['is_on_leave'])
        self.assertFalse(res.data['is_suspended'])
        self.assertEqual(res.data['presence_status'], 'on_leave')
        self.assertIn('leave', res.data['message'].lower())

    def test_suspended_hides_the_pool_with_the_reason(self):
        self._broadcast_booking()
        self._set_status(Technician.PresenceStatus.SUSPENDED, 'Repeated no-shows.')

        res = self.api.get('/api/partner/bookings/available/')
        self.assertEqual(res.data['results'], [])
        self.assertTrue(res.data['is_suspended'])
        self.assertIn('Repeated no-shows.', res.data['message'])

    def test_badge_count_agrees_with_the_hidden_pool(self):
        self._broadcast_booking()
        self.assertEqual(
            self.api.get('/api/partner/bookings/counts/').data['available'], 1
        )

        self._set_status(Technician.PresenceStatus.ON_LEAVE)
        self.assertEqual(
            self.api.get('/api/partner/bookings/counts/').data['available'], 0
        )

    def test_unavailable_technicians_cannot_accept_a_job(self):
        for status, code in (
            (Technician.PresenceStatus.ON_LEAVE, 'on_leave'),
            (Technician.PresenceStatus.SUSPENDED, 'suspended'),
        ):
            with self.subTest(status=status):
                job = self._broadcast_booking()
                self._set_status(status)
                with self.assertRaises(PartnerBookingError) as ctx:
                    partner_accept_booking(job, self.partner)
                self.assertEqual(ctx.exception.code, code)
                job.refresh_from_db()
                self.assertIsNone(job.partner_id)

    def test_going_on_leave_mid_job_does_not_strand_an_accepted_booking(self):
        """
        Leave stops new work, not work already in hand.

        Blocking start here would leave the booking stuck in Accepted with no
        way for anyone to finish it.
        """
        job = self._broadcast_booking()
        partner_accept_booking(job, self.partner)
        self._set_status(Technician.PresenceStatus.ON_LEAVE)

        res = self.api.post(
            f'/api/partner/bookings/{job.id}/start/',
            {'selfie': _selfie_file()},
            format='multipart',
        )
        self.assertEqual(res.status_code, 200, res.data)
        job.refresh_from_db()
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.IN_SERVICE)

    def test_suspension_does_stop_an_accepted_booking(self):
        """Unlike leave, suspension is a hard block on all work."""
        job = self._broadcast_booking()
        partner_accept_booking(job, self.partner)
        self._set_status(Technician.PresenceStatus.SUSPENDED, 'Under review.')

        res = self.api.post(
            f'/api/partner/bookings/{job.id}/start/',
            {'selfie': _selfie_file()},
            format='multipart',
        )
        # 400 is this API's convention for booking errors; the app keys off
        # `code` rather than the HTTP status.
        self.assertEqual(res.status_code, 400, res.data)
        self.assertEqual(res.data['code'], 'suspended')
        job.refresh_from_db()
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.ACCEPTED)

    def test_pool_push_skips_unavailable_technicians(self):
        from partner.notification_service import approved_partner_ids

        self.assertIn(self.partner.id, approved_partner_ids())

        for status in Technician.UNAVAILABLE_PRESENCE:
            with self.subTest(status=status):
                self._set_status(status)
                self.assertNotIn(self.partner.id, approved_partner_ids())

    def test_directed_push_also_skips_unavailable_technicians(self):
        """Staff picking them by hand does not make the job actionable."""
        from partner.notification_service import approved_partner_ids

        self.assertEqual(
            approved_partner_ids(technician_id=self.tech.id), [self.partner.id]
        )

        for status in Technician.UNAVAILABLE_PRESENCE:
            with self.subTest(status=status):
                self._set_status(status)
                self.assertEqual(
                    approved_partner_ids(technician_id=self.tech.id), []
                )

    def test_app_reads_the_same_status_the_crm_wrote(self):
        """No parallel value: the CRM PATCH is what the app's presence returns."""
        admin = User.objects.create_superuser(
            username='syncadmin', email='sy@x.com', password='pass12345'
        )
        crm = APIClient()
        crm.force_authenticate(user=admin)

        for value, label in Technician.PresenceStatus.choices:
            with self.subTest(status=value):
                crm_res = crm.patch(
                    f'/api/technicians/{self.tech.id}/',
                    {'presence_status': value},
                    format='json',
                )
                self.assertEqual(crm_res.status_code, 200, crm_res.data)

                app_res = self.api.get('/api/partner/presence/')
                self.assertEqual(app_res.status_code, 200, app_res.data)
                self.assertEqual(app_res.data['presence_status'], value)
                self.assertEqual(app_res.data['presence_label'], label)
                self.assertEqual(
                    app_res.data['is_available'],
                    value == Technician.PresenceStatus.ACTIVE,
                )
