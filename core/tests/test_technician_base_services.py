"""Tests for technician base services matching + partner pool filter."""
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import City, Client, Country, JobCard, Location, State, Technician
from core.services import JobCardService
from core.technician_base_services import (
    canonicalize_service_name,
    job_matches_technician_base_services,
    normalize_base_services,
    set_technician_base_services,
)
from partner.models import Partner
from partner.utils import generate_partner_tokens


class BaseServicesHelperTests(TestCase):
    def test_canonicalize_aliases(self):
        self.assertEqual(canonicalize_service_name('termite'), 'Termite')
        self.assertEqual(canonicalize_service_name('Bed Bug'), 'Bed Bugs')
        self.assertEqual(canonicalize_service_name('Cockroach / Ants'), 'Cockroach / Ants')
        self.assertIsNone(canonicalize_service_name('Plumbing'))
        # Hotel / Commercial is a property category, not a pest service
        self.assertIsNone(canonicalize_service_name('Hotel / Commercial'))
        self.assertIsNone(canonicalize_service_name('hotel'))

    def test_normalize_dedupes_and_orders(self):
        self.assertEqual(
            normalize_base_services(['Rodent', 'termite', 'Rodent', 'Bed Bugs']),
            ['Bed Bugs', 'Termite', 'Rodent'],
        )
        self.assertEqual(
            normalize_base_services(['Termite', 'Hotel / Commercial', 'Rodent']),
            ['Termite', 'Rodent'],
        )

    def test_default_base_services_is_all_pest_services(self):
        from core.technician_base_services import CANONICAL_BASE_SERVICES, default_base_services

        self.assertEqual(default_base_services(), list(CANONICAL_BASE_SERVICES))
        self.assertNotIn('Hotel / Commercial', default_base_services())


@override_settings(REVENUE_MODEL_V2=True)
class PartnerBaseServicesPoolTests(TestCase):
    def setUp(self):
        self.schedule = timezone.localtime(
            timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)
        )
        self.client_record = Client.objects.create(full_name='Svc Client', mobile='9888822222')
        country, _ = Country.objects.get_or_create(name='India')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra Svc')
        city, _ = City.objects.get_or_create(state=state, name='Mumbai Svc')
        norm = Location.normalize_text('Andheri')
        self.location, _ = Location.objects.get_or_create(
            city=city,
            normalized_name=norm,
            defaults={'name': 'Andheri'},
        )
        self.tech = Technician.objects.create(
            name='Svc Tech',
            mobile='9000022222',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ACTIVE,
            is_active=True,
        )
        self.partner = Partner.objects.create(
            full_name='Svc Tech',
            mobile='9000022222',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
            is_active=True,
        )
        self.partner.set_password('testpass')
        self.partner.save()
        self.tech.service_cities.add(city)
        tokens = generate_partner_tokens(self.partner)
        self.partner_api = APIClient()
        self.partner_api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def _pending(self, service_type: str, **overrides):
        data = {
            'client': self.client_record.id,
            'service_type': service_type,
            'service_category': JobCard.ServiceCategory.ONE_TIME,
            'schedule_datetime': self.schedule,
            'price': '2000',
            'total_amount': Decimal('2000'),
            'status': JobCard.JobStatus.PENDING,
            'master_location': self.location.id,
            'master_city': self.location.city_id,
        }
        data.update(overrides)
        with self.captureOnCommitCallbacks(execute=True):
            return JobCardService.create_jobcard(data, user=None)

    def test_empty_base_services_sees_all(self):
        termite = self._pending('Termite')
        cockroach = self._pending('Cockroach / Ants')
        available = self.partner_api.get('/api/partner/bookings/available/')
        ids = [row['id'] for row in available.data['results']]
        self.assertIn(termite.id, ids)
        self.assertIn(cockroach.id, ids)

    def test_termite_rodent_only_hides_cockroach(self):
        set_technician_base_services(self.tech, ['Termite', 'Rodent'])
        termite = self._pending('Termite')
        rodent = self._pending('Rodent')
        cockroach = self._pending('Cockroach / Ants')
        bed = self._pending('Bed Bugs')

        available = self.partner_api.get('/api/partner/bookings/available/')
        self.assertEqual(available.status_code, 200, available.data)
        ids = [row['id'] for row in available.data['results']]
        self.assertIn(termite.id, ids)
        self.assertIn(rodent.id, ids)
        self.assertNotIn(cockroach.id, ids)
        self.assertNotIn(bed.id, ids)

    def test_multi_service_visible_when_any_overlap(self):
        set_technician_base_services(self.tech, ['Termite'])
        with self.captureOnCommitCallbacks(execute=True):
            shell = JobCardService.create_jobcard(
                {
                    'client': self.client_record.id,
                    'service_type': 'Termite, Cockroach / Ants',
                    'service_items': [
                        {'service': 'Termite', 'plan': 'One-Time', 'area': '2 BHK', 'amount': '2000'},
                        {'service': 'Cockroach / Ants', 'plan': 'One-Time', 'area': '2 BHK', 'amount': '1500'},
                    ],
                    'service_category': JobCard.ServiceCategory.ONE_TIME,
                    'schedule_datetime': self.schedule,
                    'price': '3500',
                    'total_amount': Decimal('3500'),
                    'status': JobCard.JobStatus.PENDING,
                    'master_location': self.location.id,
                },
                user=None,
            )
        self.assertTrue(job_matches_technician_base_services(shell, self.tech))
        available = self.partner_api.get('/api/partner/bookings/available/')
        ids = [row['id'] for row in available.data['results']]
        self.assertIn(shell.id, ids)


@override_settings(REVENUE_MODEL_V2=True)
class TechnicianBaseServicesApiTests(TestCase):
    def setUp(self):
        from django.contrib.auth.models import User

        self.user = User.objects.create_user(
            username='svc_admin', password='pass1234', is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)

    def test_create_and_update_base_services(self):
        create = self.api.post(
            '/api/v1/technicians/',
            {
                'name': 'Base Svc Tech',
                'mobile': '9111133333',
                'is_active': True,
                'base_services': ['Termite', 'Rodent'],
            },
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.data)
        tech_id = create.data['id']
        self.assertEqual(create.data['base_services'], ['Termite', 'Rodent'])

        patch = self.api.patch(
            f'/api/v1/technicians/{tech_id}/',
            {'base_services': ['Bed Bugs', 'Termite']},
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        self.assertEqual(patch.data['base_services'], ['Bed Bugs', 'Termite'])
        tech = Technician.objects.get(pk=tech_id)
        self.assertEqual(tech.skills, ['Bed Bugs', 'Termite'])

    def test_create_defaults_all_base_services_and_drops_hotel(self):
        from core.technician_base_services import CANONICAL_BASE_SERVICES

        create = self.api.post(
            '/api/v1/technicians/',
            {
                'name': 'All Svc Tech',
                'mobile': '9111144444',
                'is_active': True,
            },
            format='json',
        )
        self.assertEqual(create.status_code, 201, create.data)
        self.assertEqual(create.data['base_services'], list(CANONICAL_BASE_SERVICES))

        patch = self.api.patch(
            f"/api/v1/technicians/{create.data['id']}/",
            {'base_services': ['Termite', 'Hotel / Commercial', 'Rodent']},
            format='json',
        )
        self.assertEqual(patch.status_code, 200, patch.data)
        self.assertEqual(patch.data['base_services'], ['Termite', 'Rodent'])
        self.assertNotIn('Hotel / Commercial', patch.data['base_services'])
