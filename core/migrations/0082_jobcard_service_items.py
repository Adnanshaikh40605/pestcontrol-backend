from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0081_jobcard_payment_amounts_bookingpayment'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcard',
            name='service_items',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='Per-service plan, area, and amount breakdown for multi-service bookings',
                verbose_name='Service Items',
            ),
        ),
    ]
