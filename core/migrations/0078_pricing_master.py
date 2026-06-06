import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def seed_pricing_master(apps, schema_editor):
    from core.pricing.seed import seed_pricing_master as run_seed

    run_seed()


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0077_lonavala_city_and_locations'),
    ]

    operations = [
        migrations.CreateModel(
            name='PricingRegion',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('slug', models.SlugField(db_index=True, max_length=50, unique=True)),
                ('name', models.CharField(max_length=100)),
                ('is_default', models.BooleanField(db_index=True, default=False)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('city', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pricing_regions', to='core.city')),
            ],
            options={
                'verbose_name': 'Pricing Region',
                'verbose_name_plural': 'Pricing Regions',
                'ordering': ['name'],
            },
        ),
        migrations.CreateModel(
            name='PricingRate',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('service_package', models.CharField(db_index=True, max_length=100)),
                ('plan_type', models.CharField(db_index=True, max_length=50)),
                ('area_key', models.CharField(db_index=True, max_length=100)),
                ('property_category', models.CharField(choices=[('residential', 'Residential (BHK/RK)'), ('villa', 'Villa / Bungalow (Sq.Ft.)'), ('fogging', 'Fogging (Sq.Ft.)'), ('rodent', 'Rodent / Reptile'), ('commercial', 'Commercial')], db_index=True, default='residential', max_length=20)),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('notes', models.TextField(blank=True)),
                ('region', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rates', to='core.pricingregion')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pricing_rate_updates', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Pricing Rate',
                'verbose_name_plural': 'Pricing Rates',
                'ordering': ['region', 'service_package', 'plan_type', 'area_key'],
                'unique_together': {('region', 'service_package', 'plan_type', 'area_key')},
            },
        ),
        migrations.CreateModel(
            name='PricingRateAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('region_slug', models.CharField(db_index=True, max_length=50)),
                ('service_package', models.CharField(max_length=100)),
                ('plan_type', models.CharField(max_length=50)),
                ('area_key', models.CharField(max_length=100)),
                ('property_category', models.CharField(blank=True, max_length=20)),
                ('old_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('new_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ('action', models.CharField(choices=[('create', 'Create'), ('update', 'Update'), ('activate', 'Activate'), ('deactivate', 'Deactivate'), ('delete', 'Delete')], db_index=True, max_length=20)),
                ('change_note', models.TextField(blank=True)),
                ('changed_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='pricing_audit_entries', to=settings.AUTH_USER_MODEL)),
                ('rate', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='audit_logs', to='core.pricingrate')),
            ],
            options={
                'verbose_name': 'Pricing Rate Audit Log',
                'verbose_name_plural': 'Pricing Rate Audit Logs',
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunPython(seed_pricing_master, migrations.RunPython.noop),
    ]
