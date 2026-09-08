"""Editing a quotation's price must actually change the saved price."""
from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework.test import APIClient, APITestCase

from core.models import Quotation


class QuotationPriceUpdateTests(APITestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user(username='q_price', password='testpass123')
        self.api.force_authenticate(user=self.user)

    def _create(self, *, rate, is_amc=False, frequency='One Time Service', visit_count=1):
        payload = {
            'customer_name': 'Coffee By The Bella',
            'mobile': '9619732371',
            'contact_person': 'THOMAS',
            'address': 'mumbai',
            'city': 'Mumbai',
            'state': 'Maharashtra',
            'quotation_type': 'AMC Package' if is_amc else 'Restaurant',
            'property_type': 'Restaurant / Cafe',
            'template_service_type': 'General Pest Control',
            'status': 'Draft',
            'discount': '0.00',
            'is_amc': is_amc,
            'visit_count': visit_count,
            'contract_amount': '0.00',
            'gst_percent': '18.00',
            'price_includes_gst': True,
            'license_number': 'LAID020185',
            'items': [{
                'service_name': 'General Pest Control',
                'frequency': frequency,
                'quantity': 1,
                'rate': f'{rate}.00',
                'total': f'{rate}.00',
                'description': frequency,
            }],
        }
        response = self.api.post('/api/v1/quotations/', payload, format='json')
        self.assertEqual(response.status_code, 201, response.data)
        return Quotation.objects.get(pk=response.data['id'])

    def _patch_rate(self, quotation, new_rate):
        """Mimic what the edit screen sends: items plus its own resolved totals."""
        payload = {
            'items': [{
                'service_name': 'General Pest Control',
                'frequency': quotation.items.first().frequency,
                'quantity': 1,
                'rate': f'{new_rate}.00',
                'total': f'{new_rate}.00',
                'description': quotation.items.first().description or '',
            }],
            'is_amc': quotation.is_amc,
            'visit_count': quotation.visit_count,
            'discount': '0.00',
            'gst_percent': '18.00',
            'price_includes_gst': True,
            # The frontend recomputes these before sending. For AMC it sends
            # max(old contract, new grand total), which is the ratchet.
            'total_amount': f'{new_rate}.00',
            'grand_total': f'{new_rate}.00',
            'contract_amount': (
                f'{max(new_rate, int(quotation.contract_amount))}.00'
                if quotation.is_amc else '0.00'
            ),
        }
        response = self.api.patch(
            f'/api/v1/quotations/{quotation.pk}/', payload, format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        quotation.refresh_from_db()
        return response

    def test_one_time_price_can_be_raised(self):
        q = self._create(rate=5000)
        self._patch_rate(q, 7000)
        self.assertEqual(q.total_amount, Decimal('7000.00'))
        self.assertEqual(q.grand_total, Decimal('7000.00'))

    def test_one_time_price_can_be_lowered(self):
        q = self._create(rate=5000)
        self._patch_rate(q, 3000)
        self.assertEqual(q.total_amount, Decimal('3000.00'))
        self.assertEqual(q.grand_total, Decimal('3000.00'))

    def test_amc_price_can_be_raised(self):
        q = self._create(rate=12000, is_amc=True, frequency='12 Service', visit_count=12)
        self._patch_rate(q, 18000)
        self.assertEqual(q.total_amount, Decimal('18000.00'))
        self.assertEqual(q.grand_total, Decimal('18000.00'))

    def test_amc_price_can_be_lowered(self):
        """The reported bug: reducing an AMC price silently keeps the old one."""
        q = self._create(rate=12000, is_amc=True, frequency='12 Service', visit_count=12)
        self._patch_rate(q, 9000)
        self.assertEqual(q.total_amount, Decimal('9000.00'))
        self.assertEqual(q.grand_total, Decimal('9000.00'))
        self.assertEqual(q.items.first().rate, Decimal('9000.00'))

    def test_blank_contract_amount_is_not_auto_filled(self):
        """The original defect: saving quietly wrote grand_total into a blank field,
        which then blocked every later price reduction."""
        q = self._create(rate=12000, is_amc=True, frequency='12 Service', visit_count=12)
        self.assertEqual(q.contract_amount, Decimal('0.00'))

    def test_amc_price_can_be_lowered_repeatedly(self):
        q = self._create(rate=12000, is_amc=True, frequency='12 Service', visit_count=12)
        for rate in (9000, 7000, 5000):
            self._patch_rate(q, rate)
            self.assertEqual(q.total_amount, Decimal(f'{rate}.00'))

    def test_contract_amount_still_prices_a_quotation_with_no_priced_lines(self):
        q = self._create(rate=12000, is_amc=True, frequency='12 Service', visit_count=12)
        response = self.api.patch(
            f'/api/v1/quotations/{q.pk}/',
            {
                'contract_amount': '20000.00',
                'items': [{
                    'service_name': 'General Pest Control',
                    'frequency': '12 Service',
                    'quantity': 1,
                    'rate': '0.00',
                    'total': '0.00',
                    'description': '12 Service',
                }],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        q.refresh_from_db()
        self.assertEqual(q.total_amount, Decimal('20000.00'))
        self.assertEqual(q.contract_amount, Decimal('20000.00'))

    def test_contract_amount_mistaken_for_a_visit_count_is_ignored(self):
        q = self._create(rate=12000, is_amc=True, frequency='12 Service', visit_count=12)
        response = self.api.patch(
            f'/api/v1/quotations/{q.pk}/',
            {'contract_amount': '12.00'},
            format='json',
        )
        self.assertEqual(response.status_code, 200, response.data)
        q.refresh_from_db()
        self.assertEqual(q.total_amount, Decimal('12000.00'))
        self.assertEqual(q.contract_amount, Decimal('0.00'))
