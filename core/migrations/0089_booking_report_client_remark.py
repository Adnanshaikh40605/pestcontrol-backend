from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0088_booking_report_client'),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingReportClientRemark',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('remark', models.TextField()),
                ('remark_type', models.CharField(choices=[('CALL', 'Call'), ('FOLLOWUP', 'Follow-up'), ('NOTE', 'Note'), ('CONVERT', 'Convert'), ('SYSTEM', 'System')], db_index=True, default='NOTE', max_length=20)),
                ('client', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='remarks', to='core.bookingreportclient')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='booking_report_client_remarks', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Booking Report Client Remark',
                'verbose_name_plural': 'Booking Report Client Remarks',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='bookingreportclientremark',
            index=models.Index(fields=['client', '-created_at'], name='core_bookin_client__idx'),
        ),
    ]
