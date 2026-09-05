"""Service-level discount on JobCard.service_items must drive net amount + ledger base."""
from decimal import Decimal
from unittest.mock import MagicMock

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from core.payment_utils import distribute_amount_across_service_items
from core.serializers import JobCardSerializer


class ServiceLevelPricingTests(TestCase):
    def _validate_items(self, payload: dict) -> dict:
        serializer = JobCardSerializer()
        # Bypass create-only client requirement by pretending this is an update.
        serializer.instance = MagicMock()
        return serializer.validate(payload)

    def test_serializer_normalizes_base_discount_amount(self):
        validated = self._validate_items({
            'service_items': [
                {
                    'service': 'Termite',
                    'plan': 'One Time Service',
                    'area': '2 BHK',
                    'base_amount': 3000,
                    'discount': 500,
                    'amount': 2500,
                },
                {
                    'service': 'Cockroach / Ants',
                    'plan': 'One Time Service',
                    'area': '2 BHK',
                    'base_amount': 1500,
                    'discount': 0,
                    'amount': 1500,
                },
            ],
            'price': '4000.00',
        })
        items = validated['service_items']
        self.assertEqual(items[0]['amount'], 2500.0)
        self.assertEqual(items[0]['discount'], 500.0)
        self.assertEqual(items[0]['base_amount'], 3000.0)
        self.assertEqual(items[1]['amount'], 1500.0)
        self.assertEqual(float(validated['discount_amount']), 500.0)
        self.assertEqual(sum(i['amount'] for i in items), 4000.0)

    def test_discount_cannot_exceed_base(self):
        with self.assertRaises(ValidationError):
            self._validate_items({
                'service_items': [
                    {
                        'service': 'Termite',
                        'plan': 'One Time Service',
                        'area': '2 BHK',
                        'base_amount': 1000,
                        'discount': 1500,
                        'amount': 0,
                    },
                ],
            })

    def test_distribute_clears_discounts(self):
        items = [
            {
                'service': 'A',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'amount': 2500,
                'base_amount': 3000,
                'discount': 500,
            },
            {
                'service': 'B',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'amount': 1500,
                'base_amount': 1500,
                'discount': 0,
            },
        ]
        distribute_amount_across_service_items(items, Decimal('4000'))
        self.assertEqual(sum(i['amount'] for i in items), 4000.0)
        self.assertTrue(all(i['discount'] == 0.0 for i in items))
        self.assertTrue(all(i['base_amount'] == i['amount'] for i in items))

    def test_legacy_items_without_discount_still_work(self):
        validated = self._validate_items({
            'service_items': [
                {
                    'service': 'Rodent',
                    'plan': 'One Time Service',
                    'area': 'Windows',
                    'amount': 1200,
                },
            ],
        })
        item = validated['service_items'][0]
        self.assertEqual(item['amount'], 1200.0)
        self.assertEqual(item['discount'], 0.0)
        self.assertEqual(item['base_amount'], 1200.0)
