from django.test import TestCase

from core.reference_sources import (
    BOOKING_REFERENCE_OPTIONS,
    build_reference_report_rows,
    reference_counts_by_canonical_name,
)


class ReferenceSourcesTests(TestCase):
    def test_calling_data_in_canonical_list(self):
        self.assertIn('Calling Data', BOOKING_REFERENCE_OPTIONS)

    def test_case_insensitive_merge(self):
        merged = reference_counts_by_canonical_name({
            'website': 10,
            'Website': 5,
            'Calling Data': 3,
            'other': 2,
            'Other': 1,
        })
        self.assertEqual(merged['Website'], 15)
        self.assertEqual(merged['Calling Data'], 3)
        self.assertEqual(merged['Other'], 3)

    def test_report_includes_all_canonical_sources(self):
        rows = build_reference_report_rows({'Google': 4})
        names = [row['reference_name'] for row in rows]
        self.assertIn('Calling Data', names)
        self.assertEqual(
            next(r for r in rows if r['reference_name'] == 'Calling Data')['reference_count'],
            0,
        )
