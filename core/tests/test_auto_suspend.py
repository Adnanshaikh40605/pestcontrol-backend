"""Tests for auto-suspend inactive technicians command."""
from datetime import timedelta

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from core.models import Technician
from core.revenue_constants import (
    AUTO_SUSPEND_OFFLINE_DAYS,
    COMPANY_SHARE_PERCENT,
    TECHNICIAN_SHARE_PERCENT,
)
from partner.models import Partner


class RevenueConstantsTests(TestCase):
    def test_locked_phase0_constants(self):
        self.assertEqual(TECHNICIAN_SHARE_PERCENT, __import__('decimal').Decimal('40.00'))
        self.assertEqual(COMPANY_SHARE_PERCENT, __import__('decimal').Decimal('60.00'))
        self.assertEqual(AUTO_SUSPEND_OFFLINE_DAYS, 3)


class AutoSuspendCommandTests(TestCase):
    def test_suspends_stale_offline_partner_tech(self):
        tech = Technician.objects.create(
            name='Stale Tech',
            mobile='9777000111',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.OFFLINE,
            last_active=timezone.now() - timedelta(days=AUTO_SUSPEND_OFFLINE_DAYS + 1),
        )
        Partner.objects.create(
            full_name='Stale Tech',
            mobile='9777000111',
            password='x',
            core_technician=tech,
            is_app_approved=True,
        )
        call_command('auto_suspend_inactive_technicians')
        tech.refresh_from_db()
        self.assertEqual(tech.presence_status, Technician.PresenceStatus.SUSPENDED)
        self.assertIsNotNone(tech.suspended_at)

    def test_skips_recently_active(self):
        tech = Technician.objects.create(
            name='Active Tech',
            mobile='9777000222',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ONLINE,
            last_active=timezone.now() - timedelta(hours=1),
        )
        call_command('auto_suspend_inactive_technicians')
        tech.refresh_from_db()
        self.assertEqual(tech.presence_status, Technician.PresenceStatus.ONLINE)
