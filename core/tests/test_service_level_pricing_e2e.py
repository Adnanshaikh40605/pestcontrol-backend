"""
End-to-end service-level pricing scenarios.

Covers create/edit/ledger consistency for:
- single service
- multi-service with discount on one line
- multi-service with different discounts
- zero discount
- edit parent discounts → day-1 children + payout refresh
- no combined-total split for tech share
"""
from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.customer_revenue import service_line_breakdown
from core.models import City, Client, Country, JobCard, Location, State, Technician
from core.payment_utils import effective_service_total, parse_jobcard_price
from core.payout_engine import calculate_and_apply_payout, service_line_package_amount
from core.technician_ledger import serialize_ledger_row


@override_settings(REVENUE_MODEL_V2=True)
class ServiceLevelPricingE2ETests(TestCase):
    def setUp(self):
        self.api = APIClient()
        from django.contrib.auth import get_user_model

        User = get_user_model()
        self.user = User.objects.create_user(username='pricing_admin', password='pass12345')
        self.user.is_staff = True
        self.user.is_superuser = True
        self.user.save()
        self.api.force_authenticate(user=self.user)

        self.client_obj = Client.objects.create(
            full_name='Pricing Test Client',
            mobile='9123456789',
        )
        country, _ = Country.objects.get_or_create(name='India')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra Pricing')
        self.city, _ = City.objects.get_or_create(state=state, name='Mumbai Pricing')
        norm = Location.normalize_text('Dadar Pricing')
        self.location, _ = Location.objects.get_or_create(
            city=self.city,
            normalized_name=norm,
            defaults={'name': 'Dadar Pricing', 'is_active': True},
        )
        self.tech = Technician.objects.create(
            name='Tech Pricing',
            mobile='9000000001',
            is_active=True,
        )
        self.schedule = timezone.now() + timezone.timedelta(days=2)

    def _create_payload(self, items, price, discount_amount=None):
        body = {
            'client_data': {
                'full_name': self.client_obj.full_name,
                'mobile': self.client_obj.mobile,
            },
            'service_type': ', '.join(i['service'] for i in items),
            'service_category': 'One-Time Service',
            'schedule_datetime': self.schedule.isoformat(),
            'price': str(price),
            'reference': 'Instagram',
            'status': 'Pending',
            'master_location': self.location.id,
            'payment_model': 'revenue_sharing',
            'technician_share_percent': 40,
            'company_share_percent': 60,
            'technician': self.tech.id,
            'service_items': items,
        }
        if discount_amount is not None:
            body['discount_amount'] = discount_amount
        return body

    def test_single_service_with_discount(self):
        items = [
            {
                'service': 'Termite',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 3000,
                'discount': 500,
                'amount': 2500,
            },
        ]
        res = self.api.post('/api/v1/jobcards/', self._create_payload(items, 2500, 500), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        job = JobCard.objects.get(id=res.data['id'])
        self.assertEqual(job.price, '2500')
        self.assertEqual(float(job.discount_amount), 500.0)
        self.assertEqual(job.service_items[0]['amount'], 2500.0)
        self.assertEqual(effective_service_total(job), Decimal('2500.00'))
        # Single-service: no day-1 children
        self.assertFalse(JobCard.objects.filter(parent_job=job, service_cycle=1).exists())

    def test_multi_service_discount_only_on_one_line(self):
        items = [
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
        ]
        res = self.api.post('/api/v1/jobcards/', self._create_payload(items, 4000, 500), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        shell = JobCard.objects.get(id=res.data['id'])
        self.assertEqual(float(shell.discount_amount), 500.0)
        self.assertEqual(parse_jobcard_price(shell.price), Decimal('4000.00'))

        children = list(JobCard.objects.filter(parent_job=shell, service_cycle=1).order_by('source_service'))
        self.assertEqual(len(children), 2)
        by_name = {c.source_service: c for c in children}
        self.assertEqual(parse_jobcard_price(by_name['Termite'].price), Decimal('2500.00'))
        self.assertEqual(parse_jobcard_price(by_name['Cockroach / Ants'].price), Decimal('1500.00'))
        self.assertEqual(float(by_name['Termite'].discount_amount), 500.0)
        self.assertEqual(float(by_name['Cockroach / Ants'].discount_amount), 0.0)

        # Ledger package amounts are per-line nets — never 4000/2.
        self.assertEqual(service_line_package_amount(by_name['Termite']), Decimal('2500.00'))
        self.assertEqual(service_line_package_amount(by_name['Cockroach / Ants']), Decimal('1500.00'))

        lines = service_line_breakdown(shell)
        self.assertEqual(len(lines), 2)
        termite = next(l for l in lines if l['service'] == 'Termite')
        self.assertEqual(termite['base_amount'], '3000.00')
        self.assertEqual(termite['discount'], '500.00')
        self.assertEqual(termite['amount'], '2500.00')

    def test_multi_service_different_discounts(self):
        items = [
            {
                'service': 'Termite',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 3000,
                'discount': 300,
                'amount': 2700,
            },
            {
                'service': 'Cockroach / Ants',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 1500,
                'discount': 200,
                'amount': 1300,
            },
        ]
        res = self.api.post('/api/v1/jobcards/', self._create_payload(items, 4000, 500), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        shell = JobCard.objects.get(id=res.data['id'])
        children = {
            c.source_service: c
            for c in JobCard.objects.filter(parent_job=shell, service_cycle=1)
        }
        self.assertEqual(parse_jobcard_price(children['Termite'].price), Decimal('2700.00'))
        self.assertEqual(parse_jobcard_price(children['Cockroach / Ants'].price), Decimal('1300.00'))
        self.assertEqual(float(shell.discount_amount), 500.0)

    def test_zero_discount_multi_service(self):
        items = [
            {
                'service': 'Termite',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 3000,
                'discount': 0,
                'amount': 3000,
            },
            {
                'service': 'Rodent',
                'plan': 'One Time Service',
                'area': 'Windows',
                'base_amount': 1200,
                'discount': 0,
                'amount': 1200,
            },
        ]
        res = self.api.post('/api/v1/jobcards/', self._create_payload(items, 4200, 0), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        shell = JobCard.objects.get(id=res.data['id'])
        self.assertEqual(float(shell.discount_amount), 0.0)
        amounts = sorted(
            parse_jobcard_price(c.price)
            for c in JobCard.objects.filter(parent_job=shell, service_cycle=1)
        )
        self.assertEqual(amounts, [Decimal('1200.00'), Decimal('3000.00')])

    def test_edit_discount_updates_children_and_payout(self):
        items = [
            {
                'service': 'Termite',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 3000,
                'discount': 0,
                'amount': 3000,
            },
            {
                'service': 'Cockroach / Ants',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 1500,
                'discount': 0,
                'amount': 1500,
            },
        ]
        res = self.api.post('/api/v1/jobcards/', self._create_payload(items, 4500, 0), format='json')
        self.assertEqual(res.status_code, 201, res.data)
        shell = JobCard.objects.get(id=res.data['id'])
        termite = JobCard.objects.get(parent_job=shell, source_service='Termite', service_cycle=1)
        self.assertEqual(parse_jobcard_price(termite.price), Decimal('3000.00'))

        # Apply ₹500 Termite discount via PATCH
        patched_items = [
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
        ]
        patch = self.api.patch(
            f'/api/v1/jobcards/{shell.id}/',
            {
                'price': '4000',
                'discount_amount': 500,
                'service_items': patched_items,
            },
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        shell.refresh_from_db()
        termite.refresh_from_db()
        cockroach = JobCard.objects.get(
            parent_job=shell, source_service='Cockroach / Ants', service_cycle=1,
        )
        self.assertEqual(parse_jobcard_price(shell.price), Decimal('4000.00'))
        self.assertEqual(parse_jobcard_price(termite.price), Decimal('2500.00'))
        self.assertEqual(parse_jobcard_price(cockroach.price), Decimal('1500.00'))
        self.assertEqual(service_line_package_amount(termite), Decimal('2500.00'))

        # Complete shell → payouts use updated nets
        done = self.api.patch(
            f'/api/v1/jobcards/{shell.id}/',
            {
                'status': 'Done',
                'payment_mode': 'Cash',
                'payment_collection_type': 'full',
            },
            format='json',
        )
        self.assertEqual(done.status_code, 200, done.data)
        termite.refresh_from_db()
        cockroach.refresh_from_db()
        # 40% of each net
        self.assertEqual(termite.visit_payout_amount, Decimal('1000.00'))
        self.assertEqual(cockroach.visit_payout_amount, Decimal('600.00'))
        self.assertEqual(termite.company_share_amount, Decimal('1500.00'))
        self.assertEqual(cockroach.company_share_amount, Decimal('900.00'))

        row_t = serialize_ledger_row(termite, self.tech)
        row_c = serialize_ledger_row(cockroach, self.tech)
        self.assertEqual(Decimal(row_t['technician_share']), Decimal('1000.00'))
        self.assertEqual(Decimal(row_c['technician_share']), Decimal('600.00'))
        # Never combined 4000 * 40% / 2 = 800
        self.assertNotEqual(Decimal(row_t['technician_share']), Decimal('800.00'))

    def test_discount_greater_than_base_rejected(self):
        items = [
            {
                'service': 'Termite',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 1000,
                'discount': 1500,
                'amount': 0,
            },
        ]
        res = self.api.post('/api/v1/jobcards/', self._create_payload(items, 0), format='json')
        self.assertEqual(res.status_code, 400)

    def test_remove_service_via_patch_drops_child_pricing_alignment(self):
        items = [
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
        ]
        res = self.api.post('/api/v1/jobcards/', self._create_payload(items, 4000, 500), format='json')
        shell = JobCard.objects.get(id=res.data['id'])
        self.assertEqual(JobCard.objects.filter(parent_job=shell, service_cycle=1).count(), 2)

        # Keep only Termite
        only_termite = [
            {
                'service': 'Termite',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 3000,
                'discount': 500,
                'amount': 2500,
            },
        ]
        patch = self.api.patch(
            f'/api/v1/jobcards/{shell.id}/',
            {
                'service_type': 'Termite',
                'price': '2500',
                'discount_amount': 500,
                'service_items': only_termite,
            },
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        shell.refresh_from_db()
        self.assertEqual(len(shell.service_items), 1)
        self.assertEqual(shell.service_items[0]['service'], 'Termite')
        self.assertEqual(parse_jobcard_price(shell.price), Decimal('2500.00'))

    def test_booking_level_discount_not_double_applied_in_payout(self):
        items = [
            {
                'service': 'Cockroach / Ants',
                'plan': 'One Time Service',
                'area': '2 BHK',
                'base_amount': 1500,
                'discount': 0,
                'amount': 1500,
            },
        ]
        res = self.api.post('/api/v1/jobcards/', self._create_payload(items, 1500, 0), format='json')
        job = JobCard.objects.get(id=res.data['id'])
        job.discount_amount = Decimal('500.00')  # orphan booking-level discount
        job.status = JobCard.JobStatus.DONE
        job.technician = self.tech
        job.save()
        result = calculate_and_apply_payout(job, force=True)
        self.assertFalse(result.skipped)
        # Still 40% of 1500 — discount_amount must NOT subtract again
        self.assertEqual(result.visit_revenue, Decimal('1500.00'))
        self.assertEqual(result.technician_pool, Decimal('600.00'))
