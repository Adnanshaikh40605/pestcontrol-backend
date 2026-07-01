from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0086_quotation_property_service_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='jobcard',
            name='society_billing_type',
            field=models.CharField(
                blank=True,
                choices=[('Free', 'Free'), ('Paid', 'Paid')],
                db_index=True,
                help_text='Free or Paid — applies to society bookings only',
                max_length=10,
                null=True,
                verbose_name='Society Billing Type',
            ),
        ),
    ]
