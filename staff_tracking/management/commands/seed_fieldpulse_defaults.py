from datetime import time
from decimal import Decimal

from django.core.management.base import BaseCommand

from staff_tracking.models import TrackingProfile
from staff_tracking.operations_models import ExpenseCategory, LeaveBalance, LeaveType, Shift


DEFAULT_LEAVE_TYPES = [
    ('Casual Leave', 'CL', Decimal('12')),
    ('Sick Leave', 'SL', Decimal('12')),
    ('Earned Leave', 'EL', Decimal('15')),
    ('Compensatory Off', 'CO', Decimal('0')),
]

DEFAULT_EXPENSE_CATEGORIES = [
    ('Travel', 'TRAVEL', Decimal('8.00')),
    ('Fuel', 'FUEL', None),
    ('Food', 'FOOD', None),
    ('Accommodation', 'STAY', None),
    ('Client Entertainment', 'CLIENT', None),
]


class Command(BaseCommand):
    help = 'Seed leave types, expense categories, default shift, and staff leave balances.'

    def handle(self, *args, **options):
        Shift.objects.get_or_create(
            is_default=True,
            defaults={
                'name': 'General Shift',
                'start_time': time(9, 0),
                'end_time': time(18, 0),
                'grace_minutes': 15,
                'is_active': True,
            },
        )

        for name, code, days in DEFAULT_LEAVE_TYPES:
            LeaveType.objects.get_or_create(
                code=code,
                defaults={'name': name, 'default_days_per_year': days, 'is_active': True},
            )

        for name, code, km_rate in DEFAULT_EXPENSE_CATEGORIES:
            ExpenseCategory.objects.get_or_create(
                code=code,
                defaults={
                    'name': name,
                    'km_rate': km_rate,
                    'is_active': True,
                },
            )

        year = 2026
        leave_types = list(LeaveType.objects.filter(is_active=True))
        for profile in TrackingProfile.objects.filter(is_active=True):
            for lt in leave_types:
                LeaveBalance.objects.get_or_create(
                    profile=profile,
                    leave_type=lt,
                    year=year,
                    defaults={'allocated': lt.default_days_per_year},
                )

        self.stdout.write(self.style.SUCCESS('FieldPulse seed data created.'))
