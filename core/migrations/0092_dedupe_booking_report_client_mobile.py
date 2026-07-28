from django.db import migrations


def forwards_dedupe(apps, schema_editor):
    from core.booking_report_dedupe import dedupe_booking_report_clients

    result = dedupe_booking_report_clients(dry_run=False)
    if result['remaining_duplicate_groups']:
        raise RuntimeError(
            f"BookingReportClient dedupe left {result['remaining_duplicate_groups']} duplicate groups"
        )


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    """
    Must run in its own migration/transaction before adding UNIQUE(mobile).
    Postgres rejects ALTER … UNIQUE in the same transaction as bulk deletes
    (“pending trigger events”).
    """

    dependencies = [
        ('core', '0091_ecard_visit'),
    ]

    operations = [
        migrations.RunPython(forwards_dedupe, backwards_noop),
    ]
