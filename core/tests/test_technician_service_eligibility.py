"""Technician One-Time/AMC and Standard/Premium eligibility."""
from decimal import Decimal
from types import SimpleNamespace

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from core.models import City, Client, Country, JobCard, Location, State, Technician
from core.services import JobCardService
from core.technician_service_eligibility import (
    job_service_requirements,
    technician_eligible_for_job,
)
from partner.models import Partner
from partner.utils import generate_partner_tokens


def _tech(**flags):
    base = dict(
        id=1,
        name='Vikas Narwade',
        accepts_one_time_jobs=False,
        accepts_amc_jobs=False,
        accepts_standard_service=False,
        accepts_premium_service=False,
    )
    base.update(flags)
    return SimpleNamespace(**base)


def _job(**fields):
    base = dict(
        service_category=JobCard.ServiceCategory.ONE_TIME,
        service_type='',
        service_items=[],
        package_tier='',
        booking_type=JobCard.BookingType.NEW_BOOKING,
        source_service='',
        included_in_amc=False,
        is_amc_main_booking=False,
        is_followup_visit=False,
        visit_type='',
    )
    base.update(fields)
    return SimpleNamespace(**base)


class MatchingRuleTests(SimpleTestCase):
    def test_one_time_standard_only_sees_one_time_standard(self):
        tech = _tech(accepts_one_time_jobs=True, accepts_standard_service=True)
        standard = _job(
            service_type='Cockroach Standard',
            service_items=[{
                'service': 'Cockroach Standard',
                'plan': 'One Time Service',
            }],
        )
        premium = _job(
            service_type='Cockroach Premium',
            service_items=[{
                'service': 'Cockroach Premium',
                'plan': 'One Time Service',
            }],
        )
        amc = _job(
            service_category=JobCard.ServiceCategory.AMC,
            service_type='Cockroach Standard',
            service_items=[{
                'service': 'Cockroach Standard',
                'plan': 'AMC 4 Services',
            }],
        )
        self.assertTrue(technician_eligible_for_job(tech, standard))
        self.assertFalse(technician_eligible_for_job(tech, premium))
        self.assertFalse(technician_eligible_for_job(tech, amc))

    def test_amc_premium_only_sees_amc_premium(self):
        tech = _tech(accepts_amc_jobs=True, accepts_premium_service=True)
        amc_premium = _job(
            service_category=JobCard.ServiceCategory.AMC,
            service_type='Cockroach Premium',
            booking_type=JobCard.BookingType.AMC_MAIN,
            service_items=[{
                'service': 'Cockroach Premium',
                'plan': 'AMC 12 Services',
            }],
        )
        one_time_premium = _job(
            service_type='Cockroach Premium',
            service_items=[{
                'service': 'Cockroach Premium',
                'plan': 'One Time Service',
            }],
        )
        amc_standard = _job(
            service_category=JobCard.ServiceCategory.AMC,
            service_type='Cockroach Standard',
            service_items=[{
                'service': 'Cockroach Standard',
                'plan': 'AMC 3 Services',
            }],
        )
        self.assertTrue(technician_eligible_for_job(tech, amc_premium))
        self.assertFalse(technician_eligible_for_job(tech, one_time_premium))
        self.assertFalse(technician_eligible_for_job(tech, amc_standard))

    def test_unscoped_services_follow_category_only(self):
        """IPM, bed bugs, and rodent systems are not a Standard/Premium product."""
        one_time_only = _tech(accepts_one_time_jobs=True)
        amc_only = _tech(accepts_amc_jobs=True)
        for name in (
            'Integrated IPM',
            'Bed Bugs',
            'Kill-Rodent System',
            'Regular Rodent',
        ):
            job = _job(
                service_type=name,
                package_tier='standard',
                service_items=[{'service': name, 'plan': 'One Time Service'}],
            )
            self.assertTrue(
                technician_eligible_for_job(one_time_only, job),
                name,
            )
            self.assertFalse(technician_eligible_for_job(amc_only, job), name)
            self.assertEqual(job_service_requirements(job).tiers, frozenset())

    def test_explicit_line_flag_limits_an_otherwise_unscoped_service(self):
        tech = _tech(accepts_one_time_jobs=True, accepts_premium_service=True)
        standard_only = _tech(accepts_one_time_jobs=True, accepts_standard_service=True)
        job = _job(
            service_type='Bed Bugs',
            service_items=[{
                'service': 'Bed Bugs',
                'plan': 'One Time Service',
                'treatment_quality': 'premium',
            }],
        )
        self.assertTrue(technician_eligible_for_job(tech, job))
        self.assertFalse(technician_eligible_for_job(standard_only, job))

    def test_legacy_cockroach_label_uses_booking_package_tier(self):
        premium_tech = _tech(accepts_one_time_jobs=True, accepts_premium_service=True)
        standard_tech = _tech(accepts_one_time_jobs=True, accepts_standard_service=True)
        job = _job(
            service_type='Cockroach / Ants',
            package_tier='premium',
            service_items=[{
                'service': 'Cockroach / Ants',
                'plan': 'One Time Service',
            }],
        )
        self.assertTrue(technician_eligible_for_job(premium_tech, job))
        self.assertFalse(technician_eligible_for_job(standard_tech, job))

    def test_mixed_booking_requires_every_line(self):
        tech = _tech(
            accepts_one_time_jobs=True,
            accepts_amc_jobs=True,
            accepts_standard_service=True,
        )
        missing_amc = _tech(
            accepts_one_time_jobs=True,
            accepts_standard_service=True,
        )
        job = _job(
            service_category=JobCard.ServiceCategory.AMC,
            service_type='Cockroach Standard, Mosquito',
            service_items=[
                {'service': 'Cockroach Standard', 'plan': 'One Time Service'},
                {'service': 'Mosquito Cold Fogging', 'plan': 'AMC 4 Services'},
            ],
        )
        req = job_service_requirements(job)
        self.assertEqual(req.categories, frozenset({'one_time', 'amc'}))
        self.assertEqual(req.tiers, frozenset({'standard'}))
        self.assertTrue(technician_eligible_for_job(tech, job))
        self.assertFalse(technician_eligible_for_job(missing_amc, job))

    def test_model_default_enables_all_four_for_new_rows(self):
        tech = Technician(name='Default', mobile='9000000099')
        self.assertTrue(tech.accepts_one_time_jobs)
        self.assertTrue(tech.accepts_amc_jobs)
        self.assertTrue(tech.accepts_standard_service)
        self.assertTrue(tech.accepts_premium_service)


class EligibilityApiTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            username='elig_admin', password='pass1234', is_staff=True,
        )
        self.api = APIClient()
        self.api.force_authenticate(user=self.admin)

        self.client_record = Client.objects.create(
            full_name='Eligibility Client', mobile='9888800060',
        )
        country, _ = Country.objects.get_or_create(name='India')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra Elig')
        self.city, _ = City.objects.get_or_create(state=state, name='Mumbai Elig')
        self.location, _ = Location.objects.get_or_create(
            city=self.city,
            normalized_name=Location.normalize_text('Andheri'),
            defaults={'name': 'Andheri'},
        )
        self.schedule = timezone.now()

        self.tech = Technician.objects.create(
            name='Standard One Time',
            mobile='9670000060',
            technician_type=Technician.TechnicianType.PARTNER,
            presence_status=Technician.PresenceStatus.ACTIVE,
            is_active=True,
            accepts_one_time_jobs=True,
            accepts_amc_jobs=False,
            accepts_standard_service=True,
            accepts_premium_service=False,
        )
        self.tech.service_cities.add(self.city)
        self.partner = Partner.objects.create(
            full_name='Standard One Time',
            mobile='9670000060',
            password='x',
            core_technician=self.tech,
            is_app_approved=True,
            is_active=True,
        )
        self.partner.set_password('testpass')
        self.partner.save()
        tokens = generate_partner_tokens(self.partner)
        self.partner_api = APIClient()
        self.partner_api.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")

    def _job(self, service, plan='One Time Service', category=None):
        job = JobCardService.create_jobcard(
            {
                'client': self.client_record.id,
                'service_type': service,
                'service_category': category or JobCard.ServiceCategory.ONE_TIME,
                'service_items': [{
                    'service': service,
                    'plan': plan,
                    'area': '1 BHK',
                    'amount': '1500',
                }],
                'schedule_datetime': self.schedule,
                'price': '1500',
                'total_amount': Decimal('1500'),
                'status': JobCard.JobStatus.PENDING,
                'master_location': self.location.id,
                'master_city': self.city.id,
            },
            user=None,
        )
        job.sent_to_app_at = timezone.now()
        job.partner = None
        job.partner_status = JobCard.PartnerStatus.PENDING
        job.status = JobCard.JobStatus.PENDING
        job.save(update_fields=['sent_to_app_at', 'partner', 'partner_status', 'status'])
        return job

    def test_crm_assign_rejects_ineligible_technician(self):
        job = self._job('Cockroach Premium')
        res = self.api.post(
            f'/api/v1/jobcards/{job.id}/assign/',
            {'technician_id': self.tech.id},
            format='json',
        )
        self.assertEqual(res.status_code, 400, res.data)
        self.assertEqual(res.data['code'], 'technician_service_ineligible')
        self.assertIn('Premium', res.data['error'])
        self.assertIn(self.tech.name, res.data['error'])
        job.refresh_from_db()
        self.assertIsNone(job.technician_id)

    def test_crm_assign_allows_matching_technician(self):
        job = self._job('Cockroach Standard')
        res = self.api.post(
            f'/api/v1/jobcards/{job.id}/assign/',
            {'technician_id': self.tech.id},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)
        job.refresh_from_db()
        self.assertEqual(job.technician_id, self.tech.id)

    def test_active_list_keeps_ineligible_technicians_visible_but_marked(self):
        job = self._job('Cockroach Premium')
        res = self.api.get('/api/v1/technicians/active/', {'job_id': job.id})
        self.assertEqual(res.status_code, 200, res.data)
        row = next(item for item in res.data if item['id'] == self.tech.id)
        self.assertFalse(row['service_eligible'])
        self.assertIn('Premium', row['service_ineligibility_reason'])

    def test_partner_accept_rejects_ineligible_offer(self):
        job = self._job('Cockroach Premium')
        res = self.partner_api.post(f'/api/partner/bookings/{job.id}/accept/')
        self.assertEqual(res.status_code, 400, res.data)
        self.assertEqual(res.data['code'], 'technician_service_ineligible')
        job.refresh_from_db()
        self.assertIsNone(job.partner_id)
        self.assertEqual(job.status, JobCard.JobStatus.PENDING)

    def test_partner_can_reject_an_ineligible_offer(self):
        job = self._job('Cockroach Premium')
        res = self.partner_api.post(
            f'/api/partner/bookings/{job.id}/reject/',
            {'reason': 'Not my service'},
            format='json',
        )
        self.assertEqual(res.status_code, 200, res.data)

    def test_partner_available_list_hides_ineligible_jobs(self):
        standard = self._job('Cockroach Standard')
        premium = self._job('Cockroach Premium')
        bed_bugs = self._job('Bed Bugs')
        bed_bugs.package_tier = 'standard'
        bed_bugs.save(update_fields=['package_tier'])

        res = self.partner_api.get('/api/partner/bookings/available/')
        self.assertEqual(res.status_code, 200, res.data)
        ids = {row['id'] for row in res.data['results']}
        self.assertIn(standard.id, ids)
        self.assertIn(bed_bugs.id, ids)
        self.assertNotIn(premium.id, ids)

    def test_reassign_via_booking_update_is_rejected(self):
        job = self._job('Cockroach Standard')
        other = Technician.objects.create(
            name='Premium Only',
            mobile='9670000061',
            accepts_one_time_jobs=True,
            accepts_amc_jobs=False,
            accepts_standard_service=False,
            accepts_premium_service=True,
        )
        res = self.api.patch(
            f'/api/v1/jobcards/{job.id}/',
            {'technician': other.id},
            format='json',
        )
        self.assertEqual(res.status_code, 400, res.data)
        self.assertIn('Standard', str(res.data))
        job.refresh_from_db()
        self.assertIsNone(job.technician_id)
