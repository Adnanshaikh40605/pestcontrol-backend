from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0087_jobcard_society_billing_type'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingReportClient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('name', models.CharField(db_index=True, max_length=255)),
                ('mobile', models.CharField(db_index=True, max_length=20)),
            ],
            options={
                'verbose_name': 'Booking Report Client',
                'verbose_name_plural': 'Booking Report Clients',
                'ordering': ['name', 'id'],
                'indexes': [
                    models.Index(fields=['name'], name='core_bookin_name_4ab019_idx'),
                    models.Index(fields=['mobile'], name='core_bookin_mobile_77cf6b_idx'),
                    models.Index(fields=['name', 'mobile'], name='core_bookin_name_2a2894_idx'),
                ],
            },
        ),
    ]
