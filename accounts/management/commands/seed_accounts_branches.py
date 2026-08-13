from django.core.management.base import BaseCommand

from accounts.models import Branch, BranchCityMap, ExpenseCategory
from core.models import City, State


DEFAULT_CATEGORIES = [
    ('office', 'Office Rent', True),
    ('office', 'Staff Salary', True),
    ('office', 'Electricity Bill', True),
    ('office', 'Phone Bill', True),
    ('office', 'Internet Bill', True),
    ('office', 'Office Purchases', True),
    ('office', 'Printing', True),
    ('office', 'Repairs', True),
    ('office', 'Miscellaneous', True),
    ('marketing', 'Google Ads', True),
    ('marketing', 'Facebook / Instagram Ads', True),
    ('marketing', 'SEO', True),
    ('marketing', 'WhatsApp Marketing', True),
    ('marketing', 'Other Marketing', True),
    ('technician', 'Travel', False),
    ('technician', 'Parking', False),
    ('technician', 'Toll', False),
    ('technician', 'Food', False),
    ('technician', 'Other Expenses', False),
    ('purchase', 'Chemical Purchase', False),
    ('purchase', 'Equipment Purchase', False),
]


class Command(BaseCommand):
    help = 'Seed Mumbai/Pune branches, city maps, and expense categories'

    def handle(self, *args, **options):
        state = State.objects.filter(name__iexact='Maharashtra').first() or State.objects.first()
        for name, code in (('Mumbai', 'MUM'), ('Pune', 'PUN')):
            branch, created = Branch.objects.get_or_create(
                code=code,
                defaults={'name': name, 'is_active': True},
            )
            if not created and branch.name != name:
                branch.name = name
                branch.save(update_fields=['name'])
            city = City.objects.filter(name__iexact=name).first()
            if not city and state:
                city = City.objects.create(state=state, name=name, is_active=True)
                self.stdout.write(f'Created city {name}')
            if city:
                if not branch.city_id:
                    branch.city = city
                    branch.save(update_fields=['city'])
                BranchCityMap.objects.get_or_create(branch=branch, city=city)
                self.stdout.write(f'Branch {name} mapped to city {city.name}')
            else:
                self.stdout.write(self.style.WARNING(f'City {name} not found — branch created without map'))

        for group, cat_name, is_overhead in DEFAULT_CATEGORIES:
            ExpenseCategory.objects.get_or_create(
                group=group,
                name=cat_name,
                defaults={'is_overhead': is_overhead, 'is_active': True},
            )
        self.stdout.write(self.style.SUCCESS('Accounts seed complete'))
