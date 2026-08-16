"""Partner complete booking — multi-service + cancelled day-1 regression."""
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from core.models import Client, JobCard, Technician
from partner.models import Partner
from partner.services import partner_complete_booking
from partner.utils import generate_partner_tokens


def _selfie_file():
    buf = BytesIO()
    Image.new('RGB', (48, 48), color=(20, 40, 60)).save(buf, format='JPEG')
    return SimpleUploadedFile('start.jpg', buf.getvalue(), content_type='image/jpeg')


@override_settings(REVENUE_MODEL_V2=True)
class PartnerCompleteMultiServiceTests(TestCase):
    def setUp(self):
        self.tech = Technician.objects.create(
            name='Salman Test',
            mobile='9000099999',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ONLINE,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Salman Test',
            mobile='9000099999',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
            is_active=True,
        )
        self.partner.set_password('testpass')
        self.partner.save()
        tokens = generate_partner_tokens(self.partner)
        self.api = APIClient()
        self.api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        self.client_row = Client.objects.create(
            full_name='sahikh saira',
            mobile='9888877777',
            city='Mumbai',
        )

    def _make_in_service_multi(self, *, crm_cancelled=False):
        now = timezone.now()
        job = JobCard.objects.create(
            client=self.client_row,
            service_type='Bed Bugs, Cockroach / Ants',
            service_items=[
                {
                    'service': 'Bed Bugs',
                    'plan': 'One Time Service',
                    'area': '4 BHK',
                    'amount': 4000.0,
                },
                {
                    'service': 'Cockroach / Ants',
                    'plan': 'One Time Service',
                    'area': '4 BHK',
                    'amount': 2000.0,
                },
            ],
            schedule_datetime=now + timedelta(hours=1),
            time_slot='01:00 PM',
            price='6000',
            total_amount=Decimal('6000.00'),
            paid_amount=Decimal('0.00'),
            pending_amount=Decimal('6000.00'),
            payment_status=JobCard.PaymentStatus.PENDING,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            reference='Poster',
            client_address='Malad West',
            technician=self.tech,
            partner=self.partner,
            assigned_to=self.tech.name,
            status=(
                JobCard.JobStatus.CANCELLED
                if crm_cancelled
                else JobCard.JobStatus.ON_PROCESS
            ),
            partner_status=JobCard.PartnerStatus.IN_SERVICE,
            started_at=now,
            is_accepted=True,
            accepted_at=now,
        )
        for service, amount, max_cycle in (
            ('Bed Bugs', '4000', 2),
            ('Cockroach / Ants', '2000', 1),
        ):
            JobCard.objects.create(
                client=self.client_row,
                parent_job=job,
                service_type=service,
                source_service=service,
                service_cycle=1,
                max_cycle=max_cycle,
                schedule_datetime=job.schedule_datetime,
                status=JobCard.JobStatus.CANCELLED,
                price=amount,
                total_amount=Decimal(amount),
                is_auto_generated=True,
                payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            )
        return job

    def test_complete_succeeds_when_day1_children_are_cancelled(self):
        """#2350 regression: End Service must not 500 on UniqueViolation."""
        job = self._make_in_service_multi(crm_cancelled=True)
        result = partner_complete_booking(job, self.partner, 'Cash')
        result.refresh_from_db()
        self.assertEqual(result.status, JobCard.JobStatus.DONE)
        self.assertEqual(result.partner_status, JobCard.PartnerStatus.COMPLETED)
        self.assertEqual(result.payment_status, JobCard.PaymentStatus.PAID)
        day1 = list(
            JobCard.objects.filter(parent_job=result, service_cycle=1).order_by('id')
        )
        self.assertEqual(len(day1), 2)
        self.assertTrue(all(c.status == JobCard.JobStatus.DONE for c in day1))

    def test_complete_api_end_to_end_multi_cancelled_children(self):
        job = self._make_in_service_multi(crm_cancelled=False)
        # Simulate accept/start already done — hit complete endpoint
        res = self.api.post(
            f'/api/partner/bookings/{job.id}/complete/',
            {'payment_mode': 'Online'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        job.refresh_from_db()
        self.assertEqual(job.status, JobCard.JobStatus.DONE)
        self.assertEqual(job.partner_status, JobCard.PartnerStatus.COMPLETED)
        self.assertEqual(job.payment_mode, JobCard.PaymentMode.ONLINE)
