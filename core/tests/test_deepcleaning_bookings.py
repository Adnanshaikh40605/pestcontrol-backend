"""Deep Cleaning bookings and technicians stay off the pest job card."""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from core.models import (
    DeepCleaningBooking,
    DeepCleaningInquiry,
    DeepCleaningTechnician,
    JobCard,
    Technician,
)


class DeepCleaningBookingWorkflowTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username='dcdesk',
            email='dcdesk@example.com',
            password='pass12345',
        )
        self.client.force_authenticate(user=self.user)
        self.tech = DeepCleaningTechnician.objects.create(
            name='Ravi Clean',
            mobile='9876500101',
            cities=['Mumbai', 'Thane'],
            services=['Full Home Deep Cleaning', 'Kitchen Deep Cleaning'],
        )

    def _booking(self, **overrides):
        payload = {
            'name': 'Meera Shah',
            'mobile': '9876500102',
            'city': 'Mumbai',
            'address': '12 Sea View, Andheri',
            'service': 'Full Home Deep Cleaning',
            'property_size': '1BHK',
            'property_type': 'Furnished',
            'preferred_date': '2026-10-22',
            'preferred_time': '9 AM – 12 PM',
            'price': '2449.30',
        }
        payload.update(overrides)
        res = self.client.post('/api/deepcleaning-bookings/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        return res.data

    def test_pending_assign_done_and_pest_tables_stay_empty(self):
        booking = self._booking()
        self.assertEqual(booking['status'], 'Pending')
        self.assertTrue(booking['code'].startswith('DC-'))
        self.assertEqual(JobCard.objects.count(), 0)
        self.assertEqual(Technician.objects.count(), 0)

        assigned = self.client.post(
            f"/api/deepcleaning-bookings/{booking['id']}/assign/",
            {'technician_id': self.tech.id},
            format='json',
        )
        self.assertEqual(assigned.status_code, status.HTTP_200_OK, assigned.data)
        self.assertEqual(assigned.data['status'], 'On Process')
        self.assertEqual(assigned.data['technician_name'], 'Ravi Clean')

        removed = self.client.post(f"/api/deepcleaning-bookings/{booking['id']}/unassign/")
        self.assertEqual(removed.status_code, status.HTTP_200_OK, removed.data)
        self.assertEqual(removed.data['status'], 'Pending')
        self.assertIsNone(removed.data['technician'])

        self.client.post(
            f"/api/deepcleaning-bookings/{booking['id']}/assign/",
            {'technician_id': self.tech.id},
            format='json',
        )
        done = self.client.post(f"/api/deepcleaning-bookings/{booking['id']}/complete/")
        self.assertEqual(done.status_code, status.HTTP_200_OK, done.data)
        self.assertEqual(done.data['status'], 'Done')
        self.assertEqual(JobCard.objects.count(), 0)

    def test_on_leave_and_wrong_service_cannot_be_assigned(self):
        booking = self._booking(service='Sofa Cleaning', mobile='9876500103')
        sofa_tech = DeepCleaningTechnician.objects.create(
            name='On Leave Sofa',
            mobile='9876500104',
            cities=['Mumbai'],
            services=['Sofa Cleaning'],
            presence_status=DeepCleaningTechnician.PresenceStatus.ON_LEAVE,
        )
        refused = self.client.post(
            f"/api/deepcleaning-bookings/{booking['id']}/assign/",
            {'technician_id': sofa_tech.id},
            format='json',
        )
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)
        mismatch = self.client.post(
            f"/api/deepcleaning-bookings/{booking['id']}/assign/",
            {'technician_id': self.tech.id},
            format='json',
        )
        self.assertEqual(mismatch.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(DeepCleaningBooking.objects.get(pk=booking['id']).status, 'Pending')

    def test_confirm_inquiry_once(self):
        inquiry = DeepCleaningInquiry.objects.create(
            name='Website Guest',
            mobile='9876500105',
            city='Pune',
            address='Baner road',
            service='Kitchen Deep Cleaning',
            property_size='2BHK',
            estimated_price='1499',
            status='New',
        )
        DeepCleaningTechnician.objects.create(
            name='Pune Crew',
            mobile='9876500106',
            cities=['Pune'],
            services=['Kitchen Deep Cleaning'],
        )
        first = self.client.post(f'/api/deepcleaning-inquiries/{inquiry.id}/confirm-booking/')
        self.assertEqual(first.status_code, status.HTTP_201_CREATED, first.data)
        second = self.client.post(f'/api/deepcleaning-inquiries/{inquiry.id}/confirm-booking/')
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(first.data['id'], second.data['id'])
        inquiry.refresh_from_db()
        self.assertEqual(inquiry.status, 'Converted')
        self.assertEqual(DeepCleaningBooking.objects.filter(inquiry=inquiry).count(), 1)
        self.assertEqual(InquiryCount(), 0)

    def test_anonymous_cannot_list_bookings(self):
        self.client.force_authenticate(user=None)
        res = self.client.get('/api/deepcleaning-bookings/')
        self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))


def InquiryCount():
    from core.models import Inquiry
    return Inquiry.objects.count()


class DeepCleaningScenarioTests(APITestCase):
    """Every desk path: create, assign, reassign, finish, cancel, and the rejects."""

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='dcscenarios',
            email='dcscenarios@example.com',
            password='pass12345',
        )
        self.client.force_authenticate(user=self.user)

    def _tech(self, mobile, **overrides):
        payload = {
            'name': 'Crew Member',
            'mobile': mobile,
            'cities': ['Mumbai'],
            'services': ['Full Home Deep Cleaning'],
        }
        payload.update(overrides)
        return DeepCleaningTechnician.objects.create(**payload)

    def _book(self, mobile='9876511001', **overrides):
        payload = {
            'name': 'Anita Desai',
            'mobile': mobile,
            'city': 'Mumbai',
            'address': '44 Linking Road, Bandra',
            'service': 'Full Home Deep Cleaning',
            'price': '2500',
        }
        payload.update(overrides)
        res = self.client.post('/api/deepcleaning-bookings/', payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_201_CREATED, res.data)
        return res.data

    def test_technician_profile_rules(self):
        created = self.client.post('/api/deepcleaning-technicians/', {
            'name': 'Sanjay More',
            'mobile': '+91 98765 12001',
            'age': 32,
            'cities': ['Mumbai', 'Thane'],
            'services': ['Kitchen Deep Cleaning', 'Bathroom Deep Cleaning'],
            'presence_status': 'active',
        }, format='json')
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(created.data['mobile'], '9876512001')

        duplicate = self.client.post('/api/deepcleaning-technicians/', {
            'name': 'Copy',
            'mobile': '9876512001',
            'cities': ['Mumbai'],
            'services': ['Kitchen Deep Cleaning'],
        }, format='json')
        self.assertEqual(duplicate.status_code, status.HTTP_400_BAD_REQUEST)

        missing = self.client.post('/api/deepcleaning-technicians/', {
            'name': 'No Skills',
            'mobile': '9876512002',
            'cities': [],
            'services': [],
        }, format='json')
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)

        young = self.client.post('/api/deepcleaning-technicians/', {
            'name': 'Too Young',
            'mobile': '9876512003',
            'age': 12,
            'cities': ['Pune'],
            'services': ['Sofa Cleaning'],
        }, format='json')
        self.assertEqual(young.status_code, status.HTTP_400_BAD_REQUEST)

        same_alt = self.client.post('/api/deepcleaning-technicians/', {
            'name': 'Same Number',
            'mobile': '9876512004',
            'alternative_mobile': '9876512004',
            'cities': ['Pune'],
            'services': ['Sofa Cleaning'],
        }, format='json')
        self.assertEqual(same_alt.status_code, status.HTTP_400_BAD_REQUEST)

        leave = self.client.patch(
            f"/api/deepcleaning-technicians/{created.data['id']}/",
            {'presence_status': 'on_leave'},
            format='json',
        )
        self.assertEqual(leave.status_code, status.HTTP_200_OK, leave.data)
        self.assertEqual(leave.data['presence_label'], 'On Leave')
        self.assertFalse(leave.data['is_available_for_work'])

    def test_booking_rejects_bad_details_and_ignores_forced_status(self):
        bad_service = self.client.post('/api/deepcleaning-bookings/', {
            'name': 'Bad Service',
            'mobile': '9876513001',
            'city': 'Mumbai',
            'address': '1 Test Lane',
            'service': 'Pest Control',
        }, format='json')
        self.assertEqual(bad_service.status_code, status.HTTP_400_BAD_REQUEST)

        bad_city = self.client.post('/api/deepcleaning-bookings/', {
            'name': 'Bad City',
            'mobile': '9876513002',
            'city': 'Delhi',
            'address': '1 Test Lane',
            'service': 'Sofa Cleaning',
        }, format='json')
        self.assertEqual(bad_city.status_code, status.HTTP_400_BAD_REQUEST)

        short_address = self.client.post('/api/deepcleaning-bookings/', {
            'name': 'Short',
            'mobile': '12345',
            'city': 'Mumbai',
            'address': 'x',
            'service': 'Sofa Cleaning',
        }, format='json')
        self.assertEqual(short_address.status_code, status.HTTP_400_BAD_REQUEST)

        negative = self.client.post('/api/deepcleaning-bookings/', {
            'name': 'Negative',
            'mobile': '9876513003',
            'city': 'Mumbai',
            'address': '9 Hill Road',
            'service': 'Carpet Cleaning',
            'price': '-10',
        }, format='json')
        self.assertEqual(negative.status_code, status.HTTP_400_BAD_REQUEST)

        forced = self._book(mobile='9876513004', status='Done')
        self.assertEqual(forced['status'], 'Pending')
        self.assertTrue(forced['code'].startswith('DC-'))

    def test_assign_reassign_city_leave_suspended_and_inactive(self):
        mumbai = self._tech('9876514001', name='Mumbai Crew', cities=['Mumbai', 'Thane'])
        pune = self._tech('9876514002', name='Pune Crew', cities=['Pune'], services=['Full Home Deep Cleaning'])
        suspended = self._tech(
            '9876514003',
            name='Suspended Crew',
            presence_status=DeepCleaningTechnician.PresenceStatus.SUSPENDED,
        )
        inactive = self._tech('9876514004', name='Inactive Crew', is_active=False)
        booking = self._book(mobile='9876514005', city='Mumbai')

        wrong_city = self.client.post(
            f"/api/deepcleaning-bookings/{booking['id']}/assign/",
            {'technician_id': pune.id},
            format='json',
        )
        self.assertEqual(wrong_city.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Pune', wrong_city.data['error'])

        for tech in (suspended, inactive):
            refused = self.client.post(
                f"/api/deepcleaning-bookings/{booking['id']}/assign/",
                {'technician_id': tech.id},
                format='json',
            )
            self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST, refused.data)

        missing = self.client.post(f"/api/deepcleaning-bookings/{booking['id']}/assign/", {}, format='json')
        self.assertEqual(missing.status_code, status.HTTP_400_BAD_REQUEST)
        unknown = self.client.post(
            f"/api/deepcleaning-bookings/{booking['id']}/assign/",
            {'technician_id': 999999},
            format='json',
        )
        self.assertEqual(unknown.status_code, status.HTTP_404_NOT_FOUND)

        available = self.client.get('/api/deepcleaning-technicians/', {
            'available': 1,
            'service': 'Full Home Deep Cleaning',
            'city': 'Mumbai',
        })
        self.assertEqual(available.status_code, status.HTTP_200_OK)
        self.assertIsInstance(available.data, list)
        ids = {row['id'] for row in available.data}
        self.assertIn(mumbai.id, ids)
        self.assertNotIn(pune.id, ids)
        self.assertNotIn(suspended.id, ids)
        self.assertNotIn(inactive.id, ids)

        first = self.client.post(
            f"/api/deepcleaning-bookings/{booking['id']}/assign/",
            {'technician_id': mumbai.id},
            format='json',
        )
        self.assertEqual(first.status_code, status.HTTP_200_OK, first.data)
        thane = self._tech('9876514006', name='Thane Crew', cities=['Mumbai', 'Thane'])
        second = self.client.post(
            f"/api/deepcleaning-bookings/{booking['id']}/assign/",
            {'technician_id': thane.id},
            format='json',
        )
        self.assertEqual(second.status_code, status.HTTP_200_OK, second.data)
        self.assertEqual(second.data['technician'], thane.id)
        self.assertEqual(second.data['status'], 'On Process')

        blocked_edit = self.client.patch(
            f"/api/deepcleaning-bookings/{booking['id']}/",
            {'city': 'Lonavala'},
            format='json',
        )
        self.assertEqual(blocked_edit.status_code, status.HTTP_400_BAD_REQUEST)

        allowed_edit = self.client.patch(
            f"/api/deepcleaning-bookings/{booking['id']}/",
            {'city': 'Thane', 'address': 'Updated society, Thane west'},
            format='json',
        )
        self.assertEqual(allowed_edit.status_code, status.HTTP_200_OK, allowed_edit.data)
        self.assertEqual(allowed_edit.data['city'], 'Thane')
        self.assertEqual(allowed_edit.data['code'], booking['code'])
        self.assertEqual(allowed_edit.data['status'], 'On Process')

    def test_complete_cancel_and_tab_counts(self):
        tech = self._tech('9876515001')
        pending = self._book(mobile='9876515002', name='Pending Person')
        working = self._book(mobile='9876515003', name='Working Person')
        self.client.post(
            f"/api/deepcleaning-bookings/{working['id']}/assign/",
            {'technician_id': tech.id},
            format='json',
        )

        too_early = self.client.post(f"/api/deepcleaning-bookings/{pending['id']}/complete/")
        self.assertEqual(too_early.status_code, status.HTTP_400_BAD_REQUEST)
        unassign_pending = self.client.post(f"/api/deepcleaning-bookings/{pending['id']}/unassign/")
        self.assertEqual(unassign_pending.status_code, status.HTTP_400_BAD_REQUEST)

        done = self.client.post(f"/api/deepcleaning-bookings/{working['id']}/complete/")
        self.assertEqual(done.status_code, status.HTTP_200_OK, done.data)
        self.assertEqual(done.data['status'], 'Done')
        self.assertTrue(done.data['completed_at'])

        again = self.client.post(f"/api/deepcleaning-bookings/{working['id']}/complete/")
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)
        assign_done = self.client.post(
            f"/api/deepcleaning-bookings/{working['id']}/assign/",
            {'technician_id': tech.id},
            format='json',
        )
        self.assertEqual(assign_done.status_code, status.HTTP_400_BAD_REQUEST)
        edit_done = self.client.patch(
            f"/api/deepcleaning-bookings/{working['id']}/",
            {'notes': 'changed'},
            format='json',
        )
        self.assertEqual(edit_done.status_code, status.HTTP_400_BAD_REQUEST)
        cancel_done = self.client.post(f"/api/deepcleaning-bookings/{working['id']}/cancel/")
        self.assertEqual(cancel_done.status_code, status.HTTP_400_BAD_REQUEST)

        other = self._book(mobile='9876515004', name='Cancel Person')
        self.client.post(
            f"/api/deepcleaning-bookings/{other['id']}/assign/",
            {'technician_id': tech.id},
            format='json',
        )
        cancelled = self.client.post(f"/api/deepcleaning-bookings/{other['id']}/cancel/")
        self.assertEqual(cancelled.status_code, status.HTTP_200_OK, cancelled.data)
        self.assertEqual(cancelled.data['status'], 'Cancelled')
        self.assertIsNone(cancelled.data['technician'])
        self.client.post(f"/api/deepcleaning-bookings/{other['id']}/cancel/")
        edit_cancelled = self.client.patch(
            f"/api/deepcleaning-bookings/{other['id']}/",
            {'notes': 'nope'},
            format='json',
        )
        self.assertEqual(edit_cancelled.status_code, status.HTTP_400_BAD_REQUEST)

        pending_tab = self.client.get('/api/deepcleaning-bookings/', {'status': 'Pending', 'search': 'Pending Person'})
        self.assertEqual(pending_tab.status_code, status.HTTP_200_OK)
        self.assertEqual([row['id'] for row in pending_tab.data['results']], [pending['id']])
        counted = self.client.get('/api/deepcleaning-bookings/', {'status': 'Pending'})
        counts = counted.data['status_counts']
        self.assertGreaterEqual(counts['Pending'], 1)
        self.assertGreaterEqual(counts['Done'], 1)
        self.assertGreaterEqual(counts['Cancelled'], 1)
        self.assertEqual(counts['all'], counts['Pending'] + counts['On Process'] + counts['Done'] + counts['Cancelled'])

        done_tab = self.client.get('/api/deepcleaning-bookings/', {'status': 'Done'})
        self.assertTrue(all(row['status'] == 'Done' for row in done_tab.data['results']))
        self.assertEqual(JobCard.objects.count(), 0)
        self.assertEqual(Technician.objects.count(), 0)

    def test_inquiry_confirm_copies_details_and_closed_is_refused(self):
        inquiry = DeepCleaningInquiry.objects.create(
            name='Website Guest',
            mobile='9876516001',
            city='Navi Mumbai',
            address='Sector 12, Vashi',
            service='Bathroom Deep Cleaning',
            property_size='1BHK',
            property_type='Empty',
            preferred_time='12 PM – 4 PM',
            estimated_price='699',
            status='Contacted',
        )
        created = self.client.post(f'/api/deepcleaning-inquiries/{inquiry.id}/confirm-booking/')
        self.assertEqual(created.status_code, status.HTTP_201_CREATED, created.data)
        self.assertEqual(created.data['status'], 'Pending')
        self.assertEqual(created.data['city'], 'Navi Mumbai')
        self.assertEqual(created.data['service'], 'Bathroom Deep Cleaning')
        self.assertEqual(created.data['price'], '699.00')
        self.assertIsNone(created.data['technician'])

        listed = self.client.get(f'/api/deepcleaning-inquiries/{inquiry.id}/')
        self.assertEqual(listed.status_code, status.HTTP_200_OK, listed.data)
        self.assertEqual(listed.data['booking_id'], created.data['id'])
        self.assertEqual(listed.data['booking_code'], created.data['code'])
        self.assertEqual(listed.data['status'], 'Converted')

        closed = DeepCleaningInquiry.objects.create(
            name='Closed Lead',
            mobile='9876516002',
            city='Lonavala',
            service='Office Deep Cleaning',
            status='Closed',
        )
        refused = self.client.post(f'/api/deepcleaning-inquiries/{closed.id}/confirm-booking/')
        self.assertEqual(refused.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(DeepCleaningBooking.objects.filter(inquiry=closed).exists())

    def test_staff_can_run_the_desk_and_anonymous_cannot(self):
        staff = User.objects.create_user(username='dcstaff', password='pass12345')
        staff.is_staff = True
        staff.save()
        self.client.force_authenticate(user=staff)
        booking = self._book(mobile='9876517001')
        self.assertEqual(booking['status'], 'Pending')

        self.client.force_authenticate(user=None)
        for path in (
            '/api/deepcleaning-bookings/',
            '/api/deepcleaning-technicians/',
        ):
            res = self.client.get(path)
            self.assertIn(res.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
        confirm = self.client.post('/api/deepcleaning-inquiries/1/confirm-booking/')
        self.assertIn(confirm.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
