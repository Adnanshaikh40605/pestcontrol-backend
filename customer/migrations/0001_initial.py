# Generated manually for Phase 5 customer app

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('core', '0095_technician_settlements'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerAccount',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mobile', models.CharField(db_index=True, max_length=10, unique=True)),
                ('password', models.CharField(max_length=255)),
                ('full_name', models.CharField(max_length=255)),
                ('email', models.EmailField(blank=True, default='', max_length=254)),
                ('is_active', models.BooleanField(db_index=True, default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('client', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='customer_account', to='core.client', verbose_name='CRM Client')),
            ],
            options={
                'verbose_name': 'Customer Account',
                'verbose_name_plural': 'Customer Accounts',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='CustomerRevokedJti',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jti', models.CharField(db_index=True, max_length=64, unique=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Customer Revoked JTI',
                'verbose_name_plural': 'Customer Revoked JTIs',
            },
        ),
    ]
