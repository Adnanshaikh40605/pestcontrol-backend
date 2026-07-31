"""
End-to-end lifecycle: website enquiry → convert → send-to-app → accept → start → complete.

Also covers CRM enquiry convert, double-convert guard, desk-assign vs app-pool conflict,
and revenue payout after partner complete.
"""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from core.models import (
    Client,
    CRMInquiry,
    Inquiry,
    JobCard,
    JobCardTechnicianParticipation,
    Technician,
)
from partner.models import Partner, PartnerEarning
from partner.utils import generate_partner_tokens


def _selfie_file():
    buf = BytesIO()
    Image.new('RGB', (48, 48), color=(20, 40, 60)).save(buf, format='JPEG')
    return SimpleUploadedFile('start.jpg', buf.getvalue(), content_type='image/jpeg')


@override_settings(REVENUE_MODEL_V2=True)
class EnquiryToCompleteE2ETests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username='crm_ops',
            password='pass1234',
            is_staff=True,
        )
        self.crm = APIClient()
        self.crm.force_authenticate(user=self.staff)

        self.tech = Technician.objects.create(
            name='Lineup Tech',
            mobile='9000011111',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ONLINE,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Lineup Tech',
            mobile='9000011111',
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

        self.public = APIClient()  # website — unauthenticated create

    def test_website_enquiry_convert_send_accept_start_complete_payout(self):
        # 1) Customer website enquiry
        create = self.public.post(
            '/api/v1/inquiries/',
            {
                'name': 'Website Customer',
                'mobile': '9111222333',
                'city': 'Pune',
                'service_interest': 'General Pest Control',
                'message': 'Need service this week',
                'service_frequency': 'one_time',
            },
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.data)
        inquiry_id = create.data['id']
        inquiry = Inquiry.objects.get(id=inquiry_id)
        self.assertEqual(inquiry.status, Inquiry.InquiryStatus.NEW)

        # 2) Staff converts enquiry → booking
        schedule = (timezone.now() + timedelta(days=1)).isoformat()
        convert = self.crm.post(
            f'/api/v1/inquiries/{inquiry_id}/convert/',
            {
                'price': '2500',
                'schedule_datetime': schedule,
                'client_address': '12 Website Lane, Pune',
            },
            format='json',
        )
        self.assertEqual(convert.status_code, 201, convert.data)
        job_id = convert.data['id']
        job = JobCard.objects.get(id=job_id)
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.status, Inquiry.InquiryStatus.CONVERTED)
        self.assertEqual(job.reference, 'Website')
        self.assertEqual(job.status, JobCard.JobStatus.PENDING)
        self.assertEqual(job.payment_model, JobCard.PaymentModel.REVENUE_SHARING)
        self.assertNotEqual(job.payout_status, JobCard.PayoutStatus.LEGACY_EXEMPT)
        self.assertEqual(job.total_amount, Decimal('2500.00'))

        # Double-convert must fail
        again = self.crm.post(
            f'/api/v1/inquiries/{inquiry_id}/convert/',
            {'price': '2500', 'schedule_datetime': schedule},
            format='json',
        )
        self.assertEqual(again.status_code, 400, again.data)

        # 3) Send to partner app (technician lineup pool)
        send = self.crm.post(f'/api/v1/jobcards/{job_id}/send-to-app/', {}, format='json')
        self.assertEqual(send.status_code, 200, send.data)
        self.assertTrue(send.data['success'])
        job.refresh_from_db()
        self.assertIsNotNone(job.sent_to_app_at)
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.PENDING)
        self.assertIsNone(job.partner_id)

        available = self.partner_api.get('/api/partner/bookings/available/')
        self.assertEqual(available.status_code, 200, available.data)
        ids = [row['id'] for row in available.data['results']]
        self.assertIn(job_id, ids)

        # 4) Technician accepts → lineup lead row created
        accept = self.partner_api.post(f'/api/partner/bookings/{job_id}/accept/')
        self.assertEqual(accept.status_code, 200, accept.data)
        job.refresh_from_db()
        self.tech.refresh_from_db()
        self.assertEqual(job.partner_id, self.partner.id)
        self.assertEqual(job.technician_id, self.tech.id)
        self.assertEqual(job.assigned_to, self.tech.name)
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.ACCEPTED)
        self.assertEqual(job.status, JobCard.JobStatus.ON_PROCESS)
        self.assertEqual(self.tech.presence_status, Technician.PresenceStatus.BUSY)
        self.assertTrue(
            JobCardTechnicianParticipation.objects.filter(
                jobcard=job, technician=self.tech, role='lead'
            ).exists()
        )

        # Second partner cannot steal
        tech2 = Technician.objects.create(
            name='Other Tech',
            mobile='9000022222',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ONLINE,
            is_active=True,
        )
        partner2 = Partner.objects.create(
            full_name='Other Tech',
            mobile='9000022222',
            password='x',
            core_technician=tech2,
            is_app_approved=True,
            is_active=True,
        )
        partner2.set_password('testpass')
        partner2.save()
        tokens2 = generate_partner_tokens(partner2)
        other_api = APIClient()
        other_api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens2['access']}")
        steal = other_api.post(f'/api/partner/bookings/{job_id}/accept/')
        self.assertIn(steal.status_code, (400, 409), steal.data)
        self.assertEqual(steal.data.get('code'), 'already_accepted')

        # 5) Start with selfie
        start = self.partner_api.post(
            f'/api/partner/bookings/{job_id}/start/',
            {'selfie': _selfie_file()},
            format='multipart',
        )
        self.assertEqual(start.status_code, 200, start.data)
        job.refresh_from_db()
        self.tech.refresh_from_db()
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.IN_SERVICE)
        self.assertIsNotNone(job.started_at)
        self.assertEqual(self.tech.presence_status, Technician.PresenceStatus.ON_SERVICE)

        # 6) Complete → payment + payout
        complete = self.partner_api.post(
            f'/api/partner/bookings/{job_id}/complete/',
            {'payment_mode': 'Cash'},
            format='json',
        )
        self.assertEqual(complete.status_code, 200, complete.data)
        job.refresh_from_db()
        self.tech.refresh_from_db()
        self.assertEqual(job.status, JobCard.JobStatus.DONE)
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.COMPLETED)
        self.assertEqual(job.payment_status, JobCard.PaymentStatus.PAID)
        self.assertEqual(job.payout_status, JobCard.PayoutStatus.PENDING)
        self.assertEqual(job.technician_pool_amount, Decimal('1000.00'))  # 40% of 2500
        earning = PartnerEarning.objects.filter(partner=self.partner, job=job).first()
        self.assertIsNotNone(earning)
        self.assertEqual(earning.amount, Decimal('1000.00'))
        self.assertEqual(self.tech.presence_status, Technician.PresenceStatus.ONLINE)

    def test_crm_enquiry_convert_applies_revenue_defaults(self):
        inquiry = CRMInquiry.objects.create(
            name='CRM Lead',
            mobile='9222333444',
            pest_type='Cockroach / Ants',
            service_frequency='one_time',
            location='Kothrud, Pune',
            status=CRMInquiry.InquiryStatus.NEW,
        )
        convert = self.crm.post(f'/api/v1/crm-inquiries/{inquiry.id}/convert/', {}, format='json')
        self.assertEqual(convert.status_code, 200, convert.data)
        job = JobCard.objects.get(id=convert.data['job_card_id'])
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.status, CRMInquiry.InquiryStatus.CONVERTED)
        self.assertEqual(job.reference, 'CRM Inquiry')
        self.assertEqual(job.payment_model, JobCard.PaymentModel.REVENUE_SHARING)
        self.assertNotEqual(job.payout_status, JobCard.PayoutStatus.LEGACY_EXEMPT)

        # Already converted
        again = self.crm.post(f'/api/v1/crm-inquiries/{inquiry.id}/convert/', {}, format='json')
        self.assertEqual(again.status_code, 400, again.data)

    def test_desk_assign_pulls_job_from_open_app_pool(self):
        client = Client.objects.create(full_name='Desk Assign', mobile='9333444555')
        job = JobCard.objects.create(
            client=client,
            service_type='General Pest Control',
            price='1500',
            total_amount=Decimal('1500.00'),
            status=JobCard.JobStatus.PENDING,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.NOT_APPLICABLE,
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        send = self.crm.post(f'/api/v1/jobcards/{job.id}/send-to-app/', {}, format='json')
        self.assertEqual(send.status_code, 200, send.data)

        desk_tech = Technician.objects.create(
            name='Desk Tech',
            mobile='9444555666',
            is_active=True,
        )
        assign = self.crm.post(
            f'/api/v1/jobcards/{job.id}/assign/',
            {'technician_id': desk_tech.id},
            format='json',
        )
        self.assertEqual(assign.status_code, 200, assign.data)
        self.assertTrue(assign.data.get('pulled_from_app'))
        job.refresh_from_db()
        self.assertEqual(job.technician_id, desk_tech.id)
        self.assertEqual(job.status, JobCard.JobStatus.ON_PROCESS)
        self.assertIsNone(job.sent_to_app_at)
        self.assertIsNone(job.partner_id)

        available = self.partner_api.get('/api/partner/bookings/available/')
        ids = [row['id'] for row in available.data['results']]
        self.assertNotIn(job.id, ids)

    def test_cannot_desk_assign_after_partner_accepted(self):
        client = Client.objects.create(full_name='Taken Job', mobile='9555666777')
        job = JobCard.objects.create(
            client=client,
            service_type='General Pest Control',
            price='1500',
            total_amount=Decimal('1500.00'),
            status=JobCard.JobStatus.PENDING,
            partner_status=JobCard.PartnerStatus.PENDING,
            sent_to_app_at=timezone.now(),
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            payout_status=JobCard.PayoutStatus.NOT_APPLICABLE,
            job_type=JobCard.JobType.CUSTOMER,
            commercial_type=JobCard.CommercialType.HOME,
        )
        accept = self.partner_api.post(f'/api/partner/bookings/{job.id}/accept/')
        self.assertEqual(accept.status_code, 200, accept.data)

        desk_tech = Technician.objects.create(
            name='Late Desk',
            mobile='9666777888',
            is_active=True,
        )
        assign = self.crm.post(
            f'/api/v1/jobcards/{job.id}/assign/',
            {'technician_id': desk_tech.id},
            format='json',
        )
        self.assertEqual(assign.status_code, 400, assign.data)
        self.assertEqual(assign.data.get('code'), 'partner_in_progress')
        job.refresh_from_db()
        self.assertEqual(job.partner_id, self.partner.id)
        self.assertEqual(job.technician_id, self.tech.id)
