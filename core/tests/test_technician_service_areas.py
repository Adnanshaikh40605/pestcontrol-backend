"""Tests for technician multi-city service areas and assign filtering."""
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import City, Country, JobCard, Location, State, Technician, Client
from core.technician_service_areas import (
    eligible_technicians_queryset,
    migrate_legacy_service_areas_for_technician,
    set_technician_service_cities,
    technician_serves_city,
)
from django.contrib.auth import get_user_model


User = get_user_model()


class TechnicianServiceAreaTests(TestCase):
    def setUp(self):
        self.country, _ = Country.objects.get_or_create(name='India')
        self.state, _ = State.objects.get_or_create(country=self.country, name='Maharashtra')
        self.mumbai, _ = City.objects.get_or_create(state=self.state, name='Mumbai')
        self.pune, _ = City.objects.get_or_create(state=self.state, name='Pune')
        self.thane, _ = City.objects.get_or_create(state=self.state, name='Thane')

        self.admin = User.objects.create_user(
            username='admin_sa', password='pass12345', is_staff=True, is_superuser=True
        )
        self.client_api = APIClient()
        self.client_api.force_authenticate(user=self.admin)

        self.tech_mumbai = Technician.objects.create(
            name='Mustakim', mobile='8850925068', is_active=True
        )
        set_technician_service_cities(self.tech_mumbai, [self.mumbai.id, self.thane.id])

        self.tech_pune = Technician.objects.create(
            name='Pune Only', mobile='9850925068', is_active=True
        )
        set_technician_service_cities(self.tech_pune, [self.pune.id])

        self.tech_unscoped = Technician.objects.create(
            name='Legacy All', mobile='7750925068', is_active=True
        )

        self.customer = Client.objects.create(full_name='Cust', mobile='9000000001')
        self.job_mumbai = JobCard.objects.create(
            client=self.customer,
            service_type='Cockroach',
            status=JobCard.JobStatus.PENDING,
            master_city=self.mumbai,
            city='Mumbai',
        )

    def test_serializer_returns_service_cities(self):
        res = self.client_api.get(f'/api/v1/technicians/{self.tech_mumbai.id}/')
        self.assertEqual(res.status_code, 200)
        names = sorted(c['name'] for c in res.data['service_cities'])
        self.assertEqual(names, ['Mumbai', 'Thane'])

    def test_active_filters_by_job_city(self):
        res = self.client_api.get(
            '/api/v1/technicians/active/',
            {'job_id': self.job_mumbai.id},
        )
        self.assertEqual(res.status_code, 200)
        ids = {row['id'] for row in res.data}
        self.assertIn(self.tech_mumbai.id, ids)
        self.assertIn(self.tech_unscoped.id, ids)
        self.assertNotIn(self.tech_pune.id, ids)

    def test_active_filters_by_city_id(self):
        res = self.client_api.get(
            '/api/v1/technicians/active/',
            {'city_id': self.pune.id},
        )
        ids = {row['id'] for row in res.data}
        self.assertIn(self.tech_pune.id, ids)
        self.assertIn(self.tech_unscoped.id, ids)
        self.assertNotIn(self.tech_mumbai.id, ids)

    def test_unscoped_included_when_city_known(self):
        self.assertTrue(technician_serves_city(self.tech_unscoped, self.mumbai))
        qs = eligible_technicians_queryset(city=self.mumbai)
        self.assertIn(self.tech_unscoped.id, set(qs.values_list('id', flat=True)))

    def test_unscoped_allowed_when_booking_has_no_city(self):
        job = JobCard.objects.create(
            client=self.customer,
            service_type='Cockroach',
            status=JobCard.JobStatus.PENDING,
            city='',
        )
        res = self.client_api.get(
            '/api/v1/technicians/active/',
            {'job_id': job.id},
        )
        ids = {row['id'] for row in res.data}
        self.assertIn(self.tech_unscoped.id, ids)
        self.assertIn(self.tech_mumbai.id, ids)
        self.assertIn(self.tech_pune.id, ids)

    def test_assign_rejects_wrong_city(self):
        res = self.client_api.post(
            f'/api/v1/jobcards/{self.job_mumbai.id}/assign/',
            {'technician_id': self.tech_pune.id},
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data.get('code'), 'technician_outside_service_area')

    def test_assign_allows_matching_city(self):
        res = self.client_api.post(
            f'/api/v1/jobcards/{self.job_mumbai.id}/assign/',
            {'technician_id': self.tech_mumbai.id},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.job_mumbai.refresh_from_db()
        self.assertEqual(self.job_mumbai.technician_id, self.tech_mumbai.id)

    def test_assign_allows_unscoped_technician(self):
        res = self.client_api.post(
            f'/api/v1/jobcards/{self.job_mumbai.id}/assign/',
            {'technician_id': self.tech_unscoped.id},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        self.job_mumbai.refresh_from_db()
        self.assertEqual(self.job_mumbai.technician_id, self.tech_unscoped.id)

    def test_assign_rejects_inactive(self):
        self.tech_mumbai.is_active = False
        self.tech_mumbai.save(update_fields=['is_active'])
        res = self.client_api.post(
            f'/api/v1/jobcards/{self.job_mumbai.id}/assign/',
            {'technician_id': self.tech_mumbai.id},
            format='json',
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.data.get('code'), 'technician_inactive')

    def test_legacy_text_migration(self):
        tech = Technician.objects.create(
            name='Old Text',
            mobile='6650925068',
            city='mumbai',
            service_area='thane',
            is_active=True,
        )
        n = migrate_legacy_service_areas_for_technician(tech)
        self.assertEqual(n, 2)
        self.assertTrue(technician_serves_city(tech, self.mumbai))
        self.assertTrue(technician_serves_city(tech, self.thane))

    def test_update_service_city_ids(self):
        res = self.client_api.patch(
            f'/api/v1/technicians/{self.tech_pune.id}/',
            {'service_city_ids': [self.mumbai.id, self.pune.id]},
            format='json',
        )
        self.assertEqual(res.status_code, 200)
        ids = {c['id'] for c in res.data['service_cities']}
        self.assertEqual(ids, {self.mumbai.id, self.pune.id})

    def test_eligible_queryset_helper(self):
        qs = eligible_technicians_queryset(city=self.mumbai)
        ids = set(qs.values_list('id', flat=True))
        self.assertIn(self.tech_mumbai.id, ids)
        self.assertNotIn(self.tech_pune.id, ids)

    def test_duplicate_city_rows_still_match(self):
        """Tech linked to duplicate 'mumbai' row must match booking on canonical 'Mumbai'."""
        dup_mumbai = City.objects.create(state=self.state, name='mumbai')
        tech = Technician.objects.create(name='Dup Row Tech', mobile='6650925077', is_active=True)
        set_technician_service_cities(tech, [dup_mumbai.id])

        self.assertTrue(technician_serves_city(tech, self.mumbai))

        res = self.client_api.get(
            '/api/v1/technicians/active/',
            {'job_id': self.job_mumbai.id},
        )
        self.assertEqual(res.status_code, 200)
        ids = {row['id'] for row in res.data}
        self.assertIn(tech.id, ids)

        res = self.client_api.post(
            f'/api/v1/jobcards/{self.job_mumbai.id}/assign/',
            {'technician_id': tech.id},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.job_mumbai.refresh_from_db()
        self.assertEqual(self.job_mumbai.technician_id, tech.id)

    def test_job_uses_master_location_city_when_master_city_missing(self):
        location = Location.objects.create(city=self.mumbai, name='Andheri West')
        job = JobCard.objects.create(
            client=self.customer,
            service_type='Cockroach',
            status=JobCard.JobStatus.PENDING,
            master_location=location,
            city='Andheri West',
        )
        res = self.client_api.get(
            '/api/v1/technicians/active/',
            {'job_id': job.id},
        )
        ids = {row['id'] for row in res.data}
        self.assertIn(self.tech_mumbai.id, ids)
        self.assertNotIn(self.tech_pune.id, ids)
