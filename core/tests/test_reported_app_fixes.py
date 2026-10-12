"""Cross-check the customer, technician, and performance-report fixes."""
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import City, Client, Country, JobCard, Location, State, Technician
from core.payment_utils import customer_invoice_figures
from customer.models import CustomerAccount
from customer.serializers import CustomerBookingSerializer
from partner.models import Partner
from partner.serializers import PartnerBookingListSerializer
from partner.services import partner_complete_booking
from partner.utils import generate_partner_tokens


@override_settings(REVENUE_MODEL_V2=True)
class ReportedAppFixTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='fix_staff',
            password='pass1234',
            is_staff=True,
        )
        self.crm = APIClient()
        self.crm.force_authenticate(user=self.staff)

        self.customer_api = APIClient()
        registered = self.customer_api.post(
            '/api/customer/register/',
            {
                'full_name': 'Fix Customer',
                'mobile': '9222333444',
                'password': 'secret12',
                'email': 'fix@example.com',
            },
            format='json',
        )
        self.assertEqual(registered.status_code, 201, registered.data)
        self.customer_api.credentials(
            HTTP_AUTHORIZATION=f"Bearer {registered.data['access']}"
        )
        self.account = CustomerAccount.objects.get(mobile='9222333444')
        self.client_row = self.account.client

        country, _ = Country.objects.get_or_create(name='India Fix')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra Fix')
        self.city, _ = City.objects.get_or_create(
            state=state, name='Mumbai', defaults={'is_active': True},
        )
        self.location, _ = Location.objects.get_or_create(
            city=self.city,
            normalized_name=Location.normalize_text('Kondhwa'),
            defaults={'name': 'Kondhwa'},
        )

        self.tech = Technician.objects.create(
            name='Fix Tech',
            mobile='9333444555',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ACTIVE,
            is_active=True,
            city='Mumbai',
        )
        self.partner = Partner.objects.create(
            full_name='Fix Tech',
            mobile='9333444555',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
            is_active=True,
        )
        self.partner.set_password('testpass')
        self.partner.save()
        tokens = generate_partner_tokens(self.partner)
        self.partner_api = APIClient()
        self.partner_api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def _job(self, **overrides):
        data = dict(
            client=self.client_row,
            service_type='Cockroach / Ants',
            price='1800',
            total_amount=Decimal('1800.00'),
            paid_amount=Decimal('0.00'),
            status=JobCard.JobStatus.PENDING,
            partner_status=JobCard.PartnerStatus.PENDING,
            schedule_datetime=timezone.now() + timedelta(hours=2),
            time_slot='01:00 PM',
            city='Mumbai',
            client_address='Flat 12, Kondhwa, Mumbai',
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        data.update(overrides)
        return JobCard.objects.create(**data)

    def test_cash_completion_shows_paid_amount_and_invoice(self):
        parent = self._job(price='1800', total_amount=Decimal('1800.00'))
        visit = self._job(
            parent_job=parent,
            price='0',
            total_amount=Decimal('0.00'),
            paid_amount=Decimal('0.00'),
            payment_status=JobCard.PaymentStatus.PENDING,
            partner=self.partner,
            technician=self.tech,
            partner_status=JobCard.PartnerStatus.IN_SERVICE,
            status=JobCard.JobStatus.ON_PROCESS,
            service_cycle=1,
        )
        partner_complete_booking(visit, self.partner, 'Cash')
        visit.refresh_from_db()
        self.assertEqual(visit.payment_mode, JobCard.PaymentMode.CASH)
        self.assertGreater(visit.paid_amount, 0)

        payload = CustomerBookingSerializer(visit).data
        self.assertGreater(Decimal(payload['paid_amount']), 0)
        self.assertGreater(Decimal(payload['invoice_amount']), 0)
        self.assertFalse(payload['can_cancel'])

        invoice = self.customer_api.get(f'/api/customer/bookings/{visit.id}/invoice/')
        self.assertEqual(invoice.status_code, 200, invoice.data)
        self.assertGreater(Decimal(invoice.data['amount']), 0)
        self.assertGreater(Decimal(invoice.data['paid_amount']), 0)
        self.assertEqual(invoice.data['payment_mode'], JobCard.PaymentMode.CASH)

    def test_historical_cash_row_with_zero_paid_still_displays_the_price(self):
        job = self._job(
            status=JobCard.JobStatus.DONE,
            payment_status=JobCard.PaymentStatus.PAID,
            payment_mode=JobCard.PaymentMode.CASH,
            price='1600',
            total_amount=Decimal('0.00'),
            paid_amount=Decimal('0.00'),
            completed_at=timezone.now(),
        )
        figures = customer_invoice_figures(job)
        self.assertEqual(figures['amount'], Decimal('1600.00'))
        self.assertEqual(figures['paid_amount'], Decimal('1600.00'))
        self.assertFalse(CustomerBookingSerializer(job).data['can_cancel'])

    def test_support_complaint_is_visible_in_crm(self):
        self._job(status=JobCard.JobStatus.DONE, completed_at=timezone.now())
        created = self.customer_api.post(
            '/api/customer/complaints/',
            {
                'complaint_type': 'Service not effective',
                'note': 'Pests came back after the visit',
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.data)
        complaint_id = created.data['booking']['id']
        complaint = JobCard.objects.get(id=complaint_id)
        self.assertTrue(complaint.is_complaint_call)
        self.assertEqual(complaint.booking_type, JobCard.BookingType.COMPLAINT_CALL)
        self.assertIsNotNone(complaint.schedule_datetime)
        self.assertEqual(complaint.complaint_status, JobCard.ComplaintStatus.OPEN)

        listed = self.crm.get('/api/v1/complaints/')
        self.assertEqual(listed.status_code, 200, listed.data)
        rows = listed.data['results'] if isinstance(listed.data, dict) else listed.data
        ids = [row['id'] for row in rows]
        self.assertIn(complaint_id, ids)

    def test_amc_schedule_exposes_three_service_cycle(self):
        parent = self._job(
            booking_type=JobCard.BookingType.AMC_MAIN,
            is_amc_main_booking=True,
            service_category=JobCard.ServiceCategory.AMC,
            max_cycle=3,
            service_cycle=1,
            status=JobCard.JobStatus.PENDING,
        )
        self._job(
            parent_job=parent,
            status=JobCard.JobStatus.DONE,
            service_cycle=1,
            max_cycle=3,
            completed_at=timezone.now(),
        )
        res = self.customer_api.get('/api/customer/amc-schedule/')
        self.assertEqual(res.status_code, 200, res.data)
        row = res.data['results'][0]
        self.assertEqual(row['parent']['max_cycle'], 3)
        done = [visit for visit in row['visits'] if visit['status'] == 'Done']
        self.assertEqual(len(done), 1)

    def test_today_and_tomorrow_only_and_legacy_city_still_matches(self):
        today = self._job(
            sent_to_app_at=timezone.now(),
            master_city=self.city,
            master_location=self.location,
        )
        later = self._job(
            sent_to_app_at=timezone.now(),
            schedule_datetime=timezone.now() + timedelta(days=5),
            master_city=self.city,
        )
        self.tech.service_cities.clear()
        self.tech.city = 'Mumbai'
        self.tech.save(update_fields=['city'])

        available = self.partner_api.get('/api/partner/bookings/available/')
        self.assertEqual(available.status_code, 200, available.data)
        ids = [row['id'] for row in available.data['results']]
        self.assertIn(today.id, ids)
        self.assertNotIn(later.id, ids)
        shown = next(row for row in available.data['results'] if row['id'] == today.id)
        self.assertEqual(shown['locality_name'], 'Kondhwa')
        self.assertIn('Mumbai', shown['city_name'])

    def test_locality_is_read_from_the_address_when_area_is_missing(self):
        job = self._job(
            master_location=None,
            master_city=None,
            city='Pune',
            client_address='Flat 12, Kondhwa, Pune, Maharashtra 411048, India',
        )
        data = PartnerBookingListSerializer(job).data
        self.assertEqual(data['locality_name'], 'Kondhwa')
        self.assertEqual(data['city_name'], 'Pune')

    def test_crm_technician_removal_returns_booking_to_available(self):
        job = self._job(
            sent_to_app_at=timezone.now(),
            master_city=self.city,
            master_location=self.location,
            price='1800',
            total_amount=Decimal('1800.00'),
        )
        self.tech.service_cities.add(self.city)
        accepted = self.partner_api.post(f'/api/partner/bookings/{job.id}/accept/')
        self.assertEqual(accepted.status_code, 200, accepted.data)
        job.refresh_from_db()
        self.assertEqual(job.partner_id, self.partner.id)
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.ACCEPTED)

        removed = self.crm.patch(
            f'/api/v1/jobcards/{job.id}/',
            {
                'technician': None,
                'status': 'Pending',
                'removal_remarks': 'Desk removed this technician',
            },
            format='json',
        )
        self.assertEqual(removed.status_code, 200, removed.data)
        job.refresh_from_db()
        self.assertIsNone(job.technician_id)
        self.assertIsNone(job.partner_id)
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.PENDING)
        self.assertEqual(job.status, JobCard.JobStatus.PENDING)
        self.assertIsNotNone(job.sent_to_app_at)

        accepted_list = self.partner_api.get('/api/partner/bookings/accepted/')
        accepted_ids = [row['id'] for row in accepted_list.data['results']]
        self.assertNotIn(job.id, accepted_ids)

        available = self.partner_api.get('/api/partner/bookings/available/')
        available_ids = [row['id'] for row in available.data['results']]
        self.assertIn(job.id, available_ids)

    def test_completed_booking_is_performed_with_time_and_locality(self):
        job = self._job(
            technician=self.tech,
            status=JobCard.JobStatus.DONE,
            schedule_datetime=timezone.now(),
            completed_at=timezone.now(),
            time_slot='01:00 PM',
            client_address='Flat 12, Kondhwa, Mumbai',
            city='Mumbai',
        )
        day = timezone.localtime().date().isoformat()
        res = self.crm.get(
            '/api/v1/technicians/daily_type_report/',
            {'date': day, 'technician_type': 'priority'},
        )
        self.assertEqual(res.status_code, 200, res.data)
        performed = res.data['performed']
        row = next(item for item in performed if item['id'] == self.tech.id)
        self.assertEqual(row['performance_status'], 'Performed')
        booking = next(item for item in row['bookings'] if item['id'] == job.id)
        self.assertEqual(booking['time_slot'], '01:00 PM')
        self.assertIn('Kondhwa', booking['location'])
        self.assertTrue(booking['schedule_datetime'])
        not_ids = [item['id'] for item in res.data['not_performed']]
        self.assertNotIn(self.tech.id, not_ids)
