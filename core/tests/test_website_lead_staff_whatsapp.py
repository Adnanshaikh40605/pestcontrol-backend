"""Website lead create: Telegram + customer WhatsApp + staff WhatsApp soft-fail."""
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.models import Inquiry


@override_settings(
    TELEGRAM_NOTIFICATIONS_ENABLED=False,
    WHATSFLOW_API_KEY='test-key',
    WEBSITE_LEAD_STAFF_WHATSAPP='917710032627',
    WEBSITE_LEAD_STAFF_WHATSAPP_TEMPLATE='pc99_website_lead_alert',
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
    @patch('core.services.notify_inquiry_received', return_value=True)
    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_staff_whatsapp_sent_persisted(self, _tg, _cust, staff_mock):
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

    @patch('core.services.notify_staff_website_lead')
    @patch('core.services.notify_inquiry_received', return_value=True)
    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_whatsapp_failure_keeps_crm_lead(self, _tg, _cust, staff_mock):
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
    @patch('core.services.notify_inquiry_received', return_value=True)
    @patch('core.services.notify_new_inquiry', return_value=True)
    def test_idempotent_skip_when_already_sent(self, _tg, _cust, staff_mock):
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
