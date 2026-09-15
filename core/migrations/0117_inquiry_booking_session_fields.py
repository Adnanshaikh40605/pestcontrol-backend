# Generated manually for website booking silent inquiry capture

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0116_invoice_billed_by_gst_number'),
    ]

    operations = [
        migrations.AddField(
            model_name='inquiry',
            name='booking_session_id',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Browser session UUID from the website booking form (upsert key)',
                max_length=64,
                null=True,
                verbose_name='Booking Session ID',
            ),
        ),
        migrations.AddField(
            model_name='inquiry',
            name='page_url',
            field=models.URLField(
                blank=True,
                help_text='Website page URL where the lead was captured',
                max_length=500,
                null=True,
                verbose_name='Page URL',
            ),
        ),
        migrations.AddField(
            model_name='inquiry',
            name='utm_source',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name='UTM Source',
            ),
        ),
        migrations.AddField(
            model_name='inquiry',
            name='utm_medium',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name='UTM Medium',
            ),
        ),
        migrations.AddField(
            model_name='inquiry',
            name='utm_campaign',
            field=models.CharField(
                blank=True,
                max_length=150,
                null=True,
                verbose_name='UTM Campaign',
            ),
        ),
        migrations.AddField(
            model_name='inquiry',
            name='linked_jobcard',
            field=models.ForeignKey(
                blank=True,
                help_text='JobCard created from Confirm Booking for this website inquiry session',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='source_website_inquiries',
                to='core.jobcard',
                verbose_name='Linked Booking',
            ),
        ),
        migrations.AddIndex(
            model_name='inquiry',
            index=models.Index(
                fields=['booking_session_id', 'mobile'],
                name='core_inquir_booking_4bc28a_idx',
            ),
        ),
    ]
