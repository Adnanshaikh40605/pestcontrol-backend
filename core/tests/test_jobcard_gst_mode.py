from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from core.models import City, Country, JobCard, Location, PricingRate, PricingRegion, State
from core.payment_utils import effective_service_total, parse_jobcard_price
from core.pricing.gst import quote_entered_price


class GstPricingModeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='gstdesk', password='pass1234')
        self.schedule = datetime(2026, 6, 15, 10, 0, tzinfo=dt_timezone.utc)
        self.api = APIClient()
        self.api.force_authenticate(user=self.user)
        country, _ = Country.objects.get_or_create(name='India')
        state, _ = State.objects.get_or_create(country=country, name='Maharashtra GST')
        city, _ = City.objects.get_or_create(state=state, name='Mumbai GST')
        norm = Location.normalize_text('GST Test Area')
        self.location, _ = Location.objects.get_or_create(
            city=city,
            normalized_name=norm,
            defaults={'name': 'GST Test Area'},
        )

    def _create(self, *, price, mode=None, base=None):
        payload = {
            'client_data': {'full_name': 'GST Client', 'mobile': '9000001050'},
            'service_type': 'Cockroach Standard',
            'service_category': 'One-Time Service',
            'schedule_datetime': self.schedule.isoformat(),
            'price': price,
            'reference': 'Poster',
            'status': 'Pending',
            'master_location': self.location.id,
            'service_items': [
                {
                    'service': 'Cockroach Standard',
                    'plan': 'One Time Service',
                    'area': '1 BHK',
                    'base_amount': base if base is not None else price,
                    'discount': 0,
                    'amount': price,
                },
            ],
        }
        if mode is not None:
            payload['gst_mode'] = mode
            payload['gst_rate'] = '18.00'
        return self.api.post('/api/v1/jobcards/', payload, format='json')

    def test_inclusive_keeps_entered_price_as_the_customer_total(self):
        quote = quote_entered_price('1050', gst_mode='GST_INCLUSIVE', gst_percent='18')
        self.assertEqual(quote['taxable_amount'], Decimal('889.83'))
        self.assertEqual(quote['gst_amount'], Decimal('160.17'))
        self.assertEqual(quote['final_payable_amount'], Decimal('1050.00'))

        response = self._create(price='1050', mode='GST_INCLUSIVE')
        self.assertEqual(response.status_code, 201, response.data)
        job = JobCard.objects.get(pk=response.data['id'])
        self.assertEqual(job.gst_mode, JobCard.GstPricingMode.INCLUSIVE)
        self.assertEqual(job.taxable_amount, Decimal('889.83'))
        self.assertEqual(job.gst_amount, Decimal('160.17'))
        self.assertEqual(job.final_payable_amount, Decimal('1050.00'))
        self.assertEqual(job.price, '1050.00')
        self.assertEqual(job.total_amount, Decimal('1050.00'))
        self.assertEqual(effective_service_total(job), Decimal('1050.00'))
        self.assertEqual(parse_jobcard_price(job.service_items[0]['amount']), Decimal('1050.00'))

    def test_exclusive_adds_gst_on_top_of_the_entered_price(self):
        quote = quote_entered_price('1050', gst_mode='GST_EXCLUSIVE', gst_percent='18')
        self.assertEqual(quote['taxable_amount'], Decimal('1050.00'))
        self.assertEqual(quote['gst_amount'], Decimal('189.00'))
        self.assertEqual(quote['final_payable_amount'], Decimal('1239.00'))

        response = self._create(price='1050', mode='GST_EXCLUSIVE')
        self.assertEqual(response.status_code, 201, response.data)
        job = JobCard.objects.get(pk=response.data['id'])
        self.assertEqual(job.gst_mode, JobCard.GstPricingMode.EXCLUSIVE)
        self.assertEqual(job.taxable_amount, Decimal('1050.00'))
        self.assertEqual(job.gst_amount, Decimal('189.00'))
        self.assertEqual(job.final_payable_amount, Decimal('1239.00'))
        self.assertEqual(job.price, '1239.00')
        self.assertEqual(job.total_amount, Decimal('1239.00'))
        self.assertEqual(effective_service_total(job), Decimal('1239.00'))

    def test_new_booking_defaults_to_gst_inclusive(self):
        response = self._create(price='1050')
        self.assertEqual(response.status_code, 201, response.data)
        job = JobCard.objects.get(pk=response.data['id'])
        self.assertEqual(job.gst_mode, JobCard.GstPricingMode.INCLUSIVE)
        # No mode was sent, so the stored customer price is left as entered.
        self.assertEqual(job.price, '1050')
        self.assertIsNone(job.final_payable_amount)

    def test_third_gst_mode_is_rejected(self):
        response = self._create(price='1050', mode='GST_NOT_APPLICABLE')
        self.assertEqual(response.status_code, 400, response.data)

    def test_saved_booking_price_does_not_follow_a_later_service_price_edit(self):
        response = self._create(price='1050', mode='GST_INCLUSIVE')
        self.assertEqual(response.status_code, 201, response.data)
        job = JobCard.objects.get(pk=response.data['id'])
        saved_price = job.price
        saved_final = job.final_payable_amount
        region = PricingRegion.objects.create(slug='gst-mode-test', name='GST Mode Test')
        rate = PricingRate.objects.create(
            region=region,
            service_package='Cockroach Standard',
            plan_type='One Time Service',
            area_key='1 BHK',
            amount=Decimal('1250.00'),
            gst_percent=Decimal('18.00'),
            price_includes_gst=False,
        )
        rate.amount = Decimal('1.00')
        rate.save(update_fields=['amount'])
        job.refresh_from_db()
        self.assertEqual(job.price, saved_price)
        self.assertEqual(job.final_payable_amount, saved_final)

    def test_two_services_each_keep_their_own_gst_and_one_booking_total(self):
        response = self.api.post(
            '/api/v1/jobcards/',
            {
                'client_data': {'full_name': 'Two Services', 'mobile': '9000001051'},
                'service_type': 'Cockroach Standard, Termite Spot Treatment',
                'service_category': 'One-Time Service',
                'schedule_datetime': self.schedule.isoformat(),
                'price': '2100',
                'gst_mode': 'GST_EXCLUSIVE',
                'gst_rate': '18.00',
                'reference': 'Poster',
                'status': 'Pending',
                'master_location': self.location.id,
                'service_items': [
                    {
                        'service': 'Cockroach Standard',
                        'plan': 'One Time Service',
                        'area': '1 BHK',
                        'base_amount': 1050,
                        'discount': 0,
                        'amount': 1050,
                    },
                    {
                        'service': 'Termite Spot Treatment',
                        'plan': 'One Time Service',
                        'area': '1 BHK',
                        'base_amount': 1050,
                        'discount': 0,
                        'amount': 1050,
                    },
                ],
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        job = JobCard.objects.get(pk=response.data['id'])
        self.assertEqual(job.taxable_amount, Decimal('2100.00'))
        self.assertEqual(job.gst_amount, Decimal('378.00'))
        self.assertEqual(job.final_payable_amount, Decimal('2478.00'))
        self.assertEqual(job.price, '2478.00')
        self.assertEqual(job.total_amount, job.final_payable_amount)
        line_finals = [Decimal(str(item['final_amount'])) for item in job.service_items]
        self.assertEqual(line_finals, [Decimal('1239.00'), Decimal('1239.00')])
