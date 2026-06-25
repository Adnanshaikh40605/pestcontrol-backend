# Generated manually for booking schedule enhancement

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0084_backfill_jobcard_completed_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcard',
            name='is_auto_generated',
            field=models.BooleanField(db_index=True, default=False, help_text='True when this visit was created by the scheduling engine', verbose_name='Auto Generated'),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='source_service',
            field=models.CharField(blank=True, db_index=True, help_text='Service line this visit belongs to (multi-service bookings)', max_length=255, null=True, verbose_name='Source Service'),
        ),
        migrations.AddField(
            model_name='jobcard',
            name='visit_type',
            field=models.CharField(blank=True, db_index=True, help_text='Badge label for technicians (e.g. RODENT AMC, TERMITE CHECK-UP)', max_length=64, null=True, verbose_name='Visit Type'),
        ),
        migrations.RemoveConstraint(
            model_name='jobcard',
            name='unique_amc_cycle_per_parent',
        ),
        migrations.AddConstraint(
            model_name='jobcard',
            constraint=models.UniqueConstraint(
                condition=models.Q(('parent_job__isnull', False)),
                fields=('parent_job', 'source_service', 'service_cycle'),
                name='unique_service_visit_per_parent',
            ),
        ),
        migrations.AlterField(
            model_name='jobcard',
            name='property_type',
            field=models.CharField(
                blank=True,
                choices=[
                    ('Society', 'Society'),
                    ('Hotel', 'Hotel'),
                    ('Office', 'Office'),
                    ('Bungalow', 'Bungalow'),
                    ('Villa', 'Villa'),
                    ('School', 'School'),
                    ('Warehouse', 'Warehouse'),
                    ('Factory', 'Factory'),
                    ('Shop', 'Shop'),
                    ('Restaurant', 'Restaurant'),
                    ('Home / Flat', 'Home / Flat'),
                    ('Commercial Space', 'Commercial Space'),
                ],
                db_index=True,
                max_length=50,
                null=True,
                verbose_name='Property Type',
            ),
        ),
    ]
