"""Not Booked flag on CRM and Website inquiry lists — synced to JobCard mobiles."""
from django.contrib.auth.models import User
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from core.models import CRMInquiry, Client, Inquiry, JobCard


class InquiryNotBookedApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='notbooked_staff', password='pass1234')
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.mobile_open = '9111222333'
        self.mobile_booked = '9444555666'

    def _create_booking(self, mobile: str) -> JobCard:
        client = Client.objects.create(full_name='Booked Customer', mobile=mobile)
        return JobCard.objects.create(
            client=client,
            service_type='Cockroach Control',
            schedule_datetime=timezone.now(),
            status=JobCard.JobStatus.PENDING,
            price='1000',
            city='Mumbai',
            reference='CRM',
        )

    def test_website_inquiry_not_booked_without_jobcard(self):
        Inquiry.objects.create(
            name='Open Lead',
            mobile=self.mobile_open,
            message='Need pest control',
            service_interest='Cockroach',
            status=Inquiry.InquiryStatus.NEW,
        )
        res = self.api.get('/api/v1/inquiries/')
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data['results'] if r['mobile'] == self.mobile_open)
        self.assertFalse(row['has_booking'])
        self.assertTrue(row['not_booked'])

    def test_website_inquiry_booked_when_jobcard_exists_for_mobile(self):
        job = self._create_booking(self.mobile_booked)
        Inquiry.objects.create(
            name='Booked Lead',
            mobile=self.mobile_booked,
            message='Already booked',
            service_interest='Cockroach',
            status=Inquiry.InquiryStatus.NEW,
            linked_jobcard=job,
        )
        res = self.api.get('/api/v1/inquiries/')
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data['results'] if r['mobile'] == self.mobile_booked)
        self.assertTrue(row['has_booking'])
        self.assertFalse(row['not_booked'])

    def test_website_inquiry_booked_by_mobile_even_if_status_still_new(self):
        self._create_booking(self.mobile_booked)
        Inquiry.objects.create(
            name='Same Mobile Later Lead',
            mobile=self.mobile_booked,
            message='Second inquiry',
            service_interest='Rodent',
            status=Inquiry.InquiryStatus.NEW,
        )
        res = self.api.get('/api/v1/inquiries/')
        self.assertEqual(res.status_code, 200, res.data)
        row = next(
            r
            for r in res.data['results']
            if r['mobile'] == self.mobile_booked and r['name'] == 'Same Mobile Later Lead'
        )
        self.assertTrue(row['has_booking'])
        self.assertFalse(row['not_booked'])

    def test_crm_inquiry_not_booked_without_jobcard(self):
        CRMInquiry.objects.create(
            name='CRM Open',
            mobile=self.mobile_open,
            pest_type='Cockroach',
            inquiry_date=timezone.localdate(),
            inquiry_time=timezone.localtime().time().replace(microsecond=0),
            status=CRMInquiry.InquiryStatus.NEW,
            created_by=self.user,
        )
        res = self.api.get('/api/v1/crm-inquiries/')
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data['results'] if r['mobile'] == self.mobile_open)
        self.assertFalse(row['has_booking'])
        self.assertTrue(row['not_booked'])

    def test_crm_inquiry_converted_status_still_not_booked_without_jobcard(self):
        """Manual Converted status without a JobCard must stay Not Booked."""
        CRMInquiry.objects.create(
            name='CRM Fake Converted',
            mobile=self.mobile_open,
            pest_type='Cockroach',
            inquiry_date=timezone.localdate(),
            inquiry_time=timezone.localtime().time().replace(microsecond=0),
            status=CRMInquiry.InquiryStatus.CONVERTED,
            created_by=self.user,
        )
        res = self.api.get('/api/v1/crm-inquiries/')
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data['results'] if r['name'] == 'CRM Fake Converted')
        self.assertFalse(row['has_booking'])
        self.assertTrue(row['not_booked'])

    def test_crm_inquiry_booked_when_jobcard_exists(self):
        self._create_booking(self.mobile_booked)
        CRMInquiry.objects.create(
            name='CRM Booked',
            mobile=self.mobile_booked,
            pest_type='Cockroach',
            inquiry_date=timezone.localdate(),
            inquiry_time=timezone.localtime().time().replace(microsecond=0),
            status=CRMInquiry.InquiryStatus.NEW,
            created_by=self.user,
        )
        res = self.api.get('/api/v1/crm-inquiries/')
        self.assertEqual(res.status_code, 200, res.data)
        row = next(r for r in res.data['results'] if r['mobile'] == self.mobile_booked)
        self.assertTrue(row['has_booking'])
        self.assertFalse(row['not_booked'])

    def test_website_filter_not_booked(self):
        self._create_booking(self.mobile_booked)
        Inquiry.objects.create(
            name='Open Lead',
            mobile=self.mobile_open,
            message='Need pest control',
            service_interest='Cockroach',
            status=Inquiry.InquiryStatus.NEW,
        )
        Inquiry.objects.create(
            name='Booked Lead',
            mobile=self.mobile_booked,
            message='Already booked',
            service_interest='Cockroach',
            status=Inquiry.InquiryStatus.NEW,
        )
        res = self.api.get('/api/v1/inquiries/', {'booking': 'not_booked'})
        self.assertEqual(res.status_code, 200, res.data)
        mobiles = {r['mobile'] for r in res.data['results']}
        self.assertIn(self.mobile_open, mobiles)
        self.assertNotIn(self.mobile_booked, mobiles)
        self.assertTrue(all(r['not_booked'] for r in res.data['results']))

    def test_crm_filter_booked(self):
        self._create_booking(self.mobile_booked)
        CRMInquiry.objects.create(
            name='CRM Open',
            mobile=self.mobile_open,
            pest_type='Cockroach',
            inquiry_date=timezone.localdate(),
            inquiry_time=timezone.localtime().time().replace(microsecond=0),
            status=CRMInquiry.InquiryStatus.NEW,
            created_by=self.user,
        )
        CRMInquiry.objects.create(
            name='CRM Booked',
            mobile=self.mobile_booked,
            pest_type='Cockroach',
            inquiry_date=timezone.localdate(),
            inquiry_time=timezone.localtime().time().replace(microsecond=0),
            status=CRMInquiry.InquiryStatus.NEW,
            created_by=self.user,
        )
        res = self.api.get('/api/v1/crm-inquiries/', {'booking': 'booked'})
        self.assertEqual(res.status_code, 200, res.data)
        mobiles = {r['mobile'] for r in res.data['results']}
        self.assertIn(self.mobile_booked, mobiles)
        self.assertNotIn(self.mobile_open, mobiles)
        self.assertTrue(all(r['has_booking'] for r in res.data['results']))
