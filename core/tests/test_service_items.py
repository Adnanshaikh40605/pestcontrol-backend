from datetime import date, datetime, timezone as dt_timezone

from django.test import TestCase

from core.models import Client, JobCard
from core.services import JobCardService


class ServiceItemsNextDateTests(TestCase):
    def setUp(self):
        self.client = Client.objects.create(full_name='Test', mobile='9123456780')
        self.job = JobCard.objects.create(
            client=self.client,
            service_type='Cockroach / Ants, Bed Bugs',
            schedule_datetime=datetime(2026, 6, 11, 10, 0, tzinfo=dt_timezone.utc),
            price='5500',
            reference='Other',
            service_items=[
                {
                    'service': 'Cockroach / Ants',
                    'plan': 'AMC 3 Services',
                    'area': '2 BHK',
                    'amount': 2500,
                },
                {
                    'service': 'Bed Bugs',
                    'plan': 'One Time Service',
                    'area': '2 BHK',
                    'amount': 3000,
                },
            ],
            service_category=JobCard.ServiceCategory.AMC,
        )

    def test_cockroach_amc_takes_priority_for_next_date(self):
        next_date, max_cycle = JobCardService.calculate_next_service_date(self.job)
        self.assertEqual(max_cycle, 3)
        self.assertEqual(next_date, date(2026, 10, 11))
