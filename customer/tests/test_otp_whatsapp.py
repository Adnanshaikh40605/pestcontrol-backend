"""WhatsFlow OTP helper + customer OTP WhatsApp delivery tests."""
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from core.whatsflow_pc99 import notify_customer_otp
from customer.models import CustomerAccount


class NotifyCustomerOtpTests(TestCase):
    @override_settings(CUSTOMER_OTP_WHATSAPP_TEMPLATE='', WHATSFLOW_API_KEY='wf_test')
    def test_skips_when_template_unset(self):
        with patch('core.whatsflow_pc99.send_template_by_phone') as send:
            ok = notify_customer_otp(mobile='9876543210', otp='4589', purpose='login')
        self.assertFalse(ok)
        send.assert_not_called()

    @override_settings(CUSTOMER_OTP_WHATSAPP_TEMPLATE='login_otp', WHATSFLOW_API_KEY='wf_test')
    def test_sends_only_otp_as_body_param(self):
        with patch('core.whatsflow_pc99.send_template_by_phone', return_value=True) as send:
            ok = notify_customer_otp(
                mobile='9876543210',
                otp='4589',
                purpose='register',
                customer_name='Adnan',
            )
        self.assertTrue(ok)
        send.assert_called_once()
        kwargs = send.call_args.kwargs
        self.assertEqual(kwargs['template_name'], 'login_otp')
        self.assertEqual(kwargs['body_params'], ['4589'])
        self.assertEqual(kwargs['phone'], '9876543210')
        self.assertIn('register', kwargs['external_id'])


@override_settings(DEBUG=False, CUSTOMER_OTP_FIXED='', CUSTOMER_OTP_WHATSAPP_TEMPLATE='login_otp')
class CustomerOtpWhatsAppDeliveryTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        CustomerAccount.objects.create_user_account(
            mobile='9000111333',
            full_name='Login User',
            password=None,
        ) if hasattr(CustomerAccount.objects, 'create_user_account') else None

    def _ensure_account(self):
        from core.models import Client
        client = Client.objects.create(full_name='Login User', mobile='9000111333')
        return CustomerAccount.objects.create(
            client=client,
            mobile='9000111333',
            full_name='Login User',
            is_active=True,
        )

    @patch('core.whatsflow_pc99.notify_customer_otp', return_value=True)
    def test_login_otp_send_marks_whatsapp_delivery(self, mock_notify):
        self._ensure_account()
        res = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9000111333', 'purpose': 'login'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['delivery'], 'whatsapp')
        self.assertNotIn('dev_otp', res.data)
        mock_notify.assert_called_once()
        self.assertEqual(mock_notify.call_args.kwargs['otp'].isdigit(), True)
        self.assertEqual(len(mock_notify.call_args.kwargs['otp']), 4)

    @patch('core.whatsflow_pc99.notify_customer_otp', return_value=False)
    def test_login_otp_send_pending_when_whatsapp_fails(self, mock_notify):
        self._ensure_account()
        res = self.api.post(
            '/api/customer/otp/send/',
            {'mobile': '9000111333', 'purpose': 'login'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['delivery'], 'pending_channel')
        mock_notify.assert_called_once()

    @override_settings(DEBUG=True, CUSTOMER_OTP_FIXED='1234')
    def test_debug_skips_whatsapp_and_returns_dev_otp(self):
        with patch('core.whatsflow_pc99.notify_customer_otp') as mock_notify:
            res = self.api.post(
                '/api/customer/otp/send/',
                {'mobile': '9000111444', 'purpose': 'register', 'full_name': 'Dev User'},
                format='json',
            )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['dev_otp'], '1234')
        mock_notify.assert_not_called()
