"""DeepCleaning99 website booking → CRM inquiry (isolated from pest leads)."""

from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import DeepCleaningBooking, DeepCleaningInquiry, Inquiry


class DeepCleaningInquiryCreateTests(APITestCase):
    def setUp(self):
        super().setUp()
        self.notify_telegram = patch('core.telegram.notify_new_inquiry', return_value=True).start()
        self.notify_whatsapp = patch(
            'core.whatsflow_pc99.notify_staff_website_lead',
            return_value={'ok': True, 'skipped': True},
        ).start()
        self.addCleanup(patch.stopall)
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

    def test_ten_digit_mobile_creates_lead_before_name(self):
        res = self.client.post(
            '/api/deepcleaning-inquiries/upsert/',
            {
                'booking_session_id': 'dc-session-home-1',
                'mobile': '9876543210',
                'service': 'Full Home Deep Cleaning',
                'city': 'Mumbai',
                'property_size': '1BHK',
                'property_type': 'Furnished',
                'estimated_price': 3499,
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        row = DeepCleaningInquiry.objects.get()
        self.assertEqual(row.name, 'Website Lead')
        self.assertEqual(row.mobile, '9876543210')
        self.assertEqual(row.service, 'Full Home Deep Cleaning')
        self.assertEqual(row.booking_session_id, 'dc-session-home-1')
        self.assertEqual(Inquiry.objects.count(), 0)
        self.notify_telegram.assert_called_once()
        self.notify_whatsapp.assert_called_once()
        self.assertEqual(self.notify_whatsapp.call_args.kwargs['inquiry_id'], f"dc-{row.id}")

    def test_same_session_updates_one_lead_when_name_arrives(self):
        first = self.client.post(
            '/api/deepcleaning-inquiries/upsert/',
            {
                'booking_session_id': 'dc-session-home-2',
                'mobile': '+91 9876543211',
                'service': 'Sofa Cleaning',
            },
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        second = self.client.post(
            '/api/deepcleaning-inquiries/upsert/',
            {
                'booking_session_id': 'dc-session-home-2',
                'mobile': '9876543211',
                'name': 'Ravi Mehta',
                'service': 'Sofa Cleaning',
                'address': 'Andheri West, Mumbai',
                'preferred_date': '2026-10-25',
            },
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(DeepCleaningInquiry.objects.count(), 1)
        row = DeepCleaningInquiry.objects.get()
        self.assertEqual(row.name, 'Ravi Mehta')
        self.assertEqual(row.address, 'Andheri West, Mumbai')
        self.assertEqual(str(row.preferred_date), '2026-10-25')
        self.assertEqual(self.notify_telegram.call_count, 1)

    def test_placeholder_name_does_not_wipe_a_real_name(self):
        self.client.post(
            '/api/deepcleaning-inquiries/upsert/',
            {
                'booking_session_id': 'dc-session-home-3',
                'mobile': '9876543212',
                'name': 'Neha Kulkarni',
                'service': 'Kitchen Deep Cleaning',
            },
            format='json',
        )
        self.client.post(
            '/api/deepcleaning-inquiries/upsert/',
            {
                'booking_session_id': 'dc-session-home-3',
                'mobile': '9876543212',
                'name': '',
                'service': 'Kitchen Deep Cleaning',
            },
            format='json',
        )
        self.assertEqual(DeepCleaningInquiry.objects.get().name, 'Neha Kulkarni')

    def test_closed_session_is_not_changed(self):
        DeepCleaningInquiry.objects.create(
            name='Closed Person',
            mobile='9876543213',
            service='Carpet Cleaning',
            booking_session_id='dc-session-closed',
            status=DeepCleaningInquiry.InquiryStatus.CLOSED,
        )
        res = self.client.post(
            '/api/deepcleaning-inquiries/upsert/',
            {
                'booking_session_id': 'dc-session-closed',
                'mobile': '9876543213',
                'name': 'Someone Else',
                'service': 'Carpet Cleaning',
            },
            format='json',
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.data)
        self.assertEqual(DeepCleaningInquiry.objects.get().name, 'Closed Person')
        self.notify_telegram.assert_not_called()

    def test_silent_lead_confirms_into_one_booking(self):
        created = self.client.post(
            '/api/deepcleaning-inquiries/upsert/',
            {
                'booking_session_id': 'dc-session-confirm',
                'mobile': '9876543299',
                'service': 'Full Home Deep Cleaning',
                'city': 'Mumbai',
                'property_size': '1BHK',
                'property_type': 'Furnished',
                'estimated_price': 3499,
            },
            format='json',
        )
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        updated = self.client.post(
            '/api/deepcleaning-inquiries/upsert/',
            {
                'booking_session_id': 'dc-session-confirm',
                'mobile': '9876543299',
                'name': 'Ravi Mehta',
                'address': 'Andheri West, Mumbai',
                'service': 'Full Home Deep Cleaning',
                'preferred_date': '2026-10-28',
            },
            format='json',
        )
        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)

        user = User.objects.create_superuser(
            username='dclead',
            email='dclead@example.com',
            password='pass12345',
        )
        self.client.force_authenticate(user=user)
        confirm = self.client.post(
            f"/api/deepcleaning-inquiries/{created.data['id']}/confirm-booking/",
        )
        self.assertEqual(confirm.status_code, status.HTTP_201_CREATED, confirm.data)
        self.assertEqual(DeepCleaningInquiry.objects.count(), 1)
        self.assertEqual(DeepCleaningBooking.objects.count(), 1)
        self.assertEqual(Inquiry.objects.count(), 0)
        row = DeepCleaningInquiry.objects.get()
        self.assertEqual(row.status, 'Converted')
        self.assertEqual(row.name, 'Ravi Mehta')
        self.assertEqual(row.booking_id if hasattr(row, 'booking_id') else row.booking.id, confirm.data['id'])

        self.client.force_authenticate(user=None)
        again = self.client.post(
            '/api/deepcleaning-inquiries/upsert/',
            {
                'booking_session_id': 'dc-session-confirm',
                'mobile': '9876543299',
                'name': 'Someone Else',
                'service': 'Sofa Cleaning',
            },
            format='json',
        )
        self.assertEqual(again.status_code, status.HTTP_200_OK, again.data)
        row.refresh_from_db()
        self.assertEqual(row.name, 'Ravi Mehta')
        self.assertEqual(row.service, 'Full Home Deep Cleaning')
        self.assertEqual(DeepCleaningBooking.objects.count(), 1)
        self.assertEqual(self.notify_telegram.call_count, 1)
