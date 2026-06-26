from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0085_jobcard_visit_scheduling_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='quotation',
            name='property_type',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
        migrations.AddField(
            model_name='quotation',
            name='template_service_type',
            field=models.CharField(blank=True, default='', max_length=100),
        ),
    ]
