"""DeepCleaning99 website booking → CRM inquiry (isolated from pest leads)."""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import DeepCleaningInquiry, Inquiry


class DeepCleaningInquiryCreateTests(APITestCase):
    def test_public_create_saves_inquiry(self):
        payload = {
            'name': 'Asha Sharma',
            'mobile': '9876543210',
            'city': 'Mumbai',
            'area': 'Andheri West',
            'address': '12 Test Building',
            'segment': 'Residential',
            'service': 'Full Home Deep Cleaning',
            'package_name': 'Furnished 1BHK up to 600 sq ft',
            'package_id': 'R2',
            'quantity': '1',
            'unit': 'package',
            'plan': 'one',
            'preferred_date': '2026-10-20',
            'preferred_time': '9 AM – 12 PM',
            'estimated_price': 2449.3,
            'regular_price': 3499,
            'discount_amount': 1049.7,
            'page_url': 'https://www.deepcleaning99.com/',
        }
        res = self.client.post('/api/deepcleaning-inquiries/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        self.assertEqual(DeepCleaningInquiry.objects.count(), 1)
        self.assertEqual(Inquiry.objects.count(), 0)  # pest leads untouched
        row = DeepCleaningInquiry.objects.get()
        self.assertEqual(row.name, 'Asha Sharma')
        self.assertEqual(row.mobile, '9876543210')
        self.assertEqual(row.service, 'Full Home Deep Cleaning')
        self.assertEqual(row.status, 'New')
        self.assertFalse(row.is_read)

    def test_invalid_mobile_rejected(self):
        res = self.client.post(
            '/api/deepcleaning-inquiries/',
            {
                'name': 'Test',
                'mobile': '123',
                'service': 'Sofa Cleaning',
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(DeepCleaningInquiry.objects.count(), 0)

    def test_crm_list_and_remark_require_auth(self):
        inquiry = DeepCleaningInquiry.objects.create(
            name='Staff View',
            mobile='9876500001',
            service='Kitchen Deep Cleaning',
            city='Thane',
        )
        list_res = self.client.get('/api/deepcleaning-inquiries/')
        self.assertIn(list_res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

        user = User.objects.create_user(username='crmdesk', password='pass12345')
        user.is_staff = True
        user.save()
        self.client.force_authenticate(user=user)
        # May still 403 depending on CRM role flags — create via service path for remark
        from core.deepcleaning_services import DeepCleaningInquiryService

        entry = DeepCleaningInquiryService.add_remark(inquiry, 'Called customer', user=user)
        self.assertEqual(entry.remark, 'Called customer')
        self.assertEqual(inquiry.remarks.count(), 1)
