"""Assign-popup lineup: service cities, same-day jobs, and who is already on the booking."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import (
    City,
    Client,
    Country,
    JobCard,
    JobCardTechnicianParticipation,
    Location,
    State,
    Technician,
)
from core.technician_service_areas import set_technician_service_cities

User = get_user_model()


class AssignTechnicianLineupTests(TestCase):
    def setUp(self):
        self.country, _ = Country.objects.get_or_create(name='India')
        self.state, _ = State.objects.get_or_create(country=self.country, name='Maharashtra')
        self.mumbai, _ = City.objects.get_or_create(state=self.state, name='Mumbai')
        self.thane, _ = City.objects.get_or_create(state=self.state, name='Thane')
        self.andheri, _ = Location.objects.get_or_create(
            city=self.mumbai,
            normalized_name=Location.normalize_text('Andheri'),
            defaults={'name': 'Andheri'},
        )
        self.admin = User.objects.create_user(
            username='lineup_admin', password='pass12345', is_staff=True, is_superuser=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)
        self.customer = Client.objects.create(full_name='Jithu', mobile='9000003311')

        self.priority = Technician.objects.create(
            name='Adnan Shaikh',
            mobile='8828936896',
            is_active=True,
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ACTIVE,
        )
        set_technician_service_cities(self.priority, [self.mumbai.id, self.thane.id])

        self.secondary = Technician.objects.create(
            name='Akshay Kumar',
            mobile='9876543210',
            is_active=True,
            technician_type=Technician.TechnicianType.SECONDARY,
            presence_status=Technician.PresenceStatus.ACTIVE,
        )
        set_technician_service_cities(self.secondary, [self.mumbai.id])

        self.on_leave = Technician.objects.create(
            name='On Leave Tech',
            mobile='9811111111',
            is_active=True,
            presence_status=Technician.PresenceStatus.ON_LEAVE,
        )

        self.when = timezone.localtime().replace(hour=10, minute=0, second=0, microsecond=0)
        self.parent = JobCard.objects.create(
            client=self.customer,
            service_type='Cockroach Standard, Termite',
            status=JobCard.JobStatus.PENDING,
            master_city=self.mumbai,
            master_location=self.andheri,
            city='Mumbai',
            schedule_datetime=self.when,
            time_slot='10:00 AM - 12:00 PM',
        )
        self.termite_line = JobCard.objects.create(
            client=self.customer,
            service_type='Termite',
            source_service='Termite',
            status=JobCard.JobStatus.PENDING,
            parent_job=self.parent,
            technician=self.secondary,
            master_city=self.mumbai,
            master_location=self.andheri,
            city='Mumbai',
            schedule_datetime=self.when,
            time_slot='10:00 AM - 12:00 PM',
        )
        self.other_today = JobCard.objects.create(
            client=self.customer,
            service_type='Bed Bugs',
            status=JobCard.JobStatus.ON_PROCESS,
            technician=self.priority,
            master_city=self.thane,
            city='Thane',
            schedule_datetime=self.when + timedelta(hours=4),
            time_slot='02:00 PM - 04:00 PM',
        )
        JobCard.objects.create(
            client=self.customer,
            service_type='Rodent',
            status=JobCard.JobStatus.DONE,
            technician=self.priority,
            schedule_datetime=self.when + timedelta(hours=6),
            time_slot='06:00 PM',
        )

    def _rows(self):
        res = self.api.get('/api/v1/technicians/active/', {'job_id': self.parent.id})
        self.assertEqual(res.status_code, 200, res.data)
        return {row['id']: row for row in res.data}

    def test_active_payload_has_areas_priority_and_same_day_jobs(self):
        rows = self._rows()
        self.assertNotIn(self.on_leave.id, rows)

        priority = rows[self.priority.id]
        names = [city['name'] for city in priority['service_cities']]
        self.assertEqual(names, ['Mumbai', 'Thane'])
        self.assertEqual(priority['technician_type'], 'partner')
        self.assertEqual(priority['assigned_service_lines'], [])
        other = [row for row in priority['lineup_bookings'] if row['id'] == self.other_today.id]
        self.assertEqual(len(other), 1)
        self.assertEqual(other[0]['time_slot'], '02:00 PM - 04:00 PM')
        self.assertEqual(other[0]['city'], 'Thane')
        self.assertFalse(other[0]['this_booking'])
        self.assertFalse(any(row['service_type'] == 'Rodent' for row in priority['lineup_bookings']))

        secondary = rows[self.secondary.id]
        self.assertEqual(secondary['technician_type'], 'secondary')
        lines = secondary['assigned_service_lines']
        self.assertEqual([row['id'] for row in lines], [self.termite_line.id])
        self.assertEqual(lines[0]['service_type'], 'Termite')
        self.assertEqual(lines[0]['location'], 'Andheri')
        same = [row for row in secondary['lineup_bookings'] if row['id'] == self.termite_line.id]
        self.assertEqual(len(same), 1)
        self.assertTrue(same[0]['this_booking'])

    def test_crew_participation_counts_as_assigned_to_the_booking(self):
        crew = Technician.objects.create(
            name='Crew Hand',
            mobile='9800002222',
            is_active=True,
            technician_type=Technician.TechnicianType.SALARIED,
        )
        JobCardTechnicianParticipation.objects.create(
            jobcard=self.parent,
            technician=crew,
            role=JobCardTechnicianParticipation.Role.CREW,
            attendance_status=JobCardTechnicianParticipation.AttendanceStatus.ASSIGNED,
        )
        rows = self._rows()
        lines = rows[crew.id]['assigned_service_lines']
        self.assertTrue(any(row['id'] == self.parent.id and row['role'] == 'crew' for row in lines))
