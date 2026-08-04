from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import CRMRole, UserProfile


class StaffPaginationTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='9000000000',
            email='admin@example.com',
            password='pass1234',
            first_name='Admin',
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

        roles = [
            ('9100000001', 'Super Admin', True, True),
            ('9100000002', 'Staff', True, False),
            ('9100000003', 'Technician', True, False),
            ('9100000004', 'Blog User', False, False),
            ('9100000005', 'Technician', False, False),
        ]

        role_to_profile = {
            'Super Admin': CRMRole.SUPER_ADMIN,
            'Admin': CRMRole.ADMIN,
            'Staff': CRMRole.STAFF,
            'Technician': CRMRole.TECHNICIAN,
            'Blog User': CRMRole.BLOG_USER,
        }

        for mobile, role, is_active, is_superuser in roles:
            user = User.objects.create_user(
                username=mobile,
                password='pass1234',
                first_name=f'{role} User',
                is_active=is_active,
                is_staff=role != 'Blog User',
                is_superuser=is_superuser,
            )
            UserProfile.objects.update_or_create(
                user=user,
                defaults={'role': role_to_profile[role]},
            )

    def test_staff_list_returns_paginated_summary(self):
        res = self.api.get('/api/v1/staff/', {'page': 1, 'page_size': 2}, format='json')

        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['count'], 6)
        self.assertEqual(len(res.data['results']), 2)
        self.assertIn('summary', res.data)
        self.assertEqual(
            res.data['summary'],
            {
                'total': 6,
                'active': 4,
                'super_admins': 2,
                'technicians': 2,
                'blog_users': 1,
            },
        )

    def test_staff_list_can_filter_by_role(self):
        res = self.api.get('/api/v1/staff/', {'role': 'Technician', 'page_size': 10}, format='json')

        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data['count'], 2)
        self.assertEqual(res.data['summary']['technicians'], 2)
        self.assertTrue(all(row['role_display'] == 'Technician' for row in res.data['results']))
