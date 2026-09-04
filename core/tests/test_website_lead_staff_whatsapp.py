"""Website lead create: Telegram + staff WhatsApp only (no customer WhatsApp)."""
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Inquiry


@override_settings(
    TELEGRAM_NOTIFICATIONS_ENABLED=False,
    WHATSFLOW_API_KEY='test-key',
    WEBSITE_LEAD_STAFF_WHATSAPP='917710032627',
    WEBSITE_LEAD_STAFF_WHATSAPP_TEMPLATE='pc99_staff_inquiry_notice',
    WEBSITE_LEAD_STAFF_WHATSAPP_ENABLED=True,
)
class WebsiteLeadStaffWhatsAppTests(TestCase):
    def setUp(self):
        self.api = APIClient()

    def _payload(self):
        return {
            'name': 'Raj Sharma',
            'mobile': '9876543210',
            'city': 'Mumbai',
            'service_interest': 'Termites',
            'message': 'Need termite treatment for my flat',
            'premise_type': 'residential',
            'email': 'raj@example.com',
        }

    @patch('core.services.notify_staff_website_lead')
    @patch('core.services.notify_inquiry_received', create=True)
    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_staff_whatsapp_sent_persisted(self, _tg, cust_mock, staff_mock):
        staff_mock.return_value = {
            'ok': True,
            'message_id': 'wamid.TEST123',
            'error': '',
            'skipped': False,
        }
        res = self.api.post('/api/inquiries/', self._payload(), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        lead = Inquiry.objects.get(pk=res.data['id'])
        self.assertEqual(lead.staff_whatsapp_status, Inquiry.StaffWhatsAppStatus.SENT)
        self.assertEqual(lead.staff_whatsapp_message_id, 'wamid.TEST123')
        self.assertIsNotNone(lead.staff_whatsapp_sent_at)
        staff_mock.assert_called_once()
        cust_mock.assert_not_called()

    @patch('core.services.notify_staff_website_lead')
    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_customer_whatsapp_not_triggered(self, _tg, staff_mock):
        staff_mock.return_value = {
            'ok': True,
            'message_id': 'wamid.OK',
            'error': '',
            'skipped': False,
        }
        with patch('core.services.notify_inquiry_received', create=True) as cust_mock:
            res = self.api.post('/api/inquiries/', self._payload(), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        cust_mock.assert_not_called()
        staff_mock.assert_called_once()
        kwargs = staff_mock.call_args.kwargs
        self.assertEqual(kwargs['name'], 'Raj Sharma')
        self.assertEqual(kwargs['mobile'], '9876543210')
        self.assertEqual(kwargs['city'], 'Mumbai')
        self.assertEqual(kwargs['service'], 'Termites')

    @patch('core.services.notify_staff_website_lead')
    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_whatsapp_failure_keeps_crm_lead(self, _tg, staff_mock):
        staff_mock.return_value = {
            'ok': False,
            'message_id': '',
            'error': 'meta_timeout',
            'skipped': False,
        }
        res = self.api.post('/api/inquiries/', self._payload(), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        lead = Inquiry.objects.get(pk=res.data['id'])
        self.assertEqual(lead.name, 'Raj Sharma')
        self.assertEqual(lead.staff_whatsapp_status, Inquiry.StaffWhatsAppStatus.FAILED)
        self.assertIn('meta_timeout', lead.staff_whatsapp_error)

    @patch('core.services.notify_staff_website_lead')
    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_idempotent_skip_when_already_sent(self, _tg, staff_mock):
        from core.services import InquiryService

        lead = Inquiry.objects.create(
            name='Raj Sharma',
            mobile='9876543210',
            city='Mumbai',
            service_interest='Termites',
            message='Need termite treatment for my flat',
            staff_whatsapp_status=Inquiry.StaffWhatsAppStatus.SENT,
            staff_whatsapp_message_id='already',
        )
        InquiryService._notify_staff_website_lead_whatsapp(lead)
        staff_mock.assert_not_called()

    @override_settings(WEBSITE_LEAD_STAFF_WHATSAPP='917710032627')
    @patch('core.whatsflow_pc99.send_template_by_phone')
    def test_staff_send_uses_staff_number_not_customer(self, send_mock):
        from core.whatsflow_pc99 import notify_staff_website_lead

        send_mock.return_value = {'ok': True, 'message_id': 'wamid.X', 'error': ''}
        result = notify_staff_website_lead(
            inquiry_id=999,
            name='Raj Sharma',
            mobile='9876543210',
            city='Mumbai',
            service='Termites',
            property_type='Residential',
            message='Need treatment',
        )
        self.assertTrue(result['ok'])
        kwargs = send_mock.call_args.kwargs
        self.assertEqual(kwargs['phone'], '917710032627')
        self.assertEqual(kwargs['template_name'], 'pc99_staff_inquiry_notice')
        self.assertEqual(kwargs['body_params'][0], 'Raj Sharma')
        self.assertEqual(kwargs['body_params'][1], '9876543210')
        self.assertIn('Termites', kwargs['body_params'][2])
        self.assertIn('Residential', kwargs['body_params'][2])
        self.assertIn('Mumbai', kwargs['body_params'][3])
        self.assertNotEqual(kwargs['phone'], '9876543210')
