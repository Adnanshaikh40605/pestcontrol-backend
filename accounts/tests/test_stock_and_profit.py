from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import Branch, Chemical, ExpenseCategory, ExpenseEntry
from accounts.services.overhead import allocate_monthly_overhead
from accounts.services.profit import recalculate_booking_cost
from accounts.services.stock import purchase_stock, record_chemical_usage
from core.models import Client, JobCard, Technician


@override_settings(REVENUE_MODEL_V2=True)
class AccountsStockProfitTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('acc_admin', password='x', is_staff=True)
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        self.branch = Branch.objects.create(name='Mumbai', code='MUM')
        self.chemical = Chemical.objects.create(
            name='Termite Chem', unit='ml', reorder_level=Decimal('100'),
        )
        self.client_obj = Client.objects.create(full_name='Kamal', mobile='9888575737')
        self.tech = Technician.objects.create(name='Akshay', mobile='9000000001')

    def _job(self, amount='3200'):
        now = timezone.now()
        job = JobCard.objects.create(
            client=self.client_obj,
            technician=self.tech,
            service_type='Termite',
            city='Mumbai',
            price=amount,
            total_amount=Decimal(amount),
            status=JobCard.JobStatus.PENDING,
            schedule_datetime=now,
            payment_model=JobCard.PaymentModel.REVENUE_SHARING,
            created_by=self.user,
        )
        JobCard.objects.filter(pk=job.pk).update(
            status=JobCard.JobStatus.DONE,
            completed_at=now,
            visit_revenue_amount=Decimal(amount),
            technician_pool_amount=Decimal(amount) * Decimal('0.40'),
            company_share_amount=Decimal(amount) * Decimal('0.60'),
            visit_payout_amount=Decimal(amount) * Decimal('0.40'),
        )
        job.refresh_from_db()
        return job

    def test_purchase_and_usage_computes_chemical_cost(self):
        # 1L = 1000ml @ ₹2000 → ₹2/ml; 35ml → ₹70
        purchase_stock(
            branch=self.branch,
            item_type='chemical',
            chemical=self.chemical,
            quantity=Decimal('1000'),
            unit_cost=Decimal('2'),
            user=self.user,
        )
        job = self._job()
        usage = record_chemical_usage(
            job=job,
            chemical=self.chemical,
            quantity_ml=Decimal('35'),
            user=self.user,
        )
        self.assertEqual(usage.line_cost, Decimal('70.00'))
        snap = recalculate_booking_cost(job)
        self.assertEqual(snap.chemical_cost, Decimal('70.00'))
        self.assertEqual(snap.technician_cost, Decimal('1280.00'))
        self.assertEqual(snap.company_share, Decimal('1920.00'))
        # Gross = 3200 - 70 - 0 - 1280 - 0 = 1850
        self.assertEqual(snap.gross_profit, Decimal('1850.00'))
        # Company net = 1920 - 70 = 1850
        self.assertEqual(snap.company_net_profit, Decimal('1850.00'))

    def test_overhead_allocation(self):
        cat, _ = ExpenseCategory.objects.get_or_create(
            group='office', name='Office Rent', defaults={'is_overhead': True},
        )
        ExpenseEntry.objects.create(
            branch=self.branch,
            category=cat,
            amount=Decimal('1000'),
            status=ExpenseEntry.Status.POSTED,
        )
        job = self._job()
        today = timezone.localdate()
        rates = allocate_monthly_overhead(year=today.year, month=today.month, branch=self.branch)
        self.assertEqual(len(rates), 1)
        self.assertGreaterEqual(rates[0].completed_bookings, 1)
        snap = recalculate_booking_cost(job)
        self.assertGreater(snap.overhead_cost, Decimal('0'))

    def test_dashboard_api(self):
        res = self.api.get('/api/accounts/dashboard/')
        self.assertEqual(res.status_code, 200)
        self.assertIn('daily', res.data)
        self.assertIn('monthly', res.data)

    def test_purchase_api(self):
        res = self.api.post('/api/accounts/stock-movements/purchase/', {
            'branch_id': self.branch.id,
            'item_type': 'chemical',
            'chemical_id': self.chemical.id,
            'quantity': '500',
            'unit_cost': '2.5',
        }, format='json')
        self.assertEqual(res.status_code, 201)
        bal = self.api.get('/api/accounts/stock-balances/')
        self.assertEqual(bal.status_code, 200)
