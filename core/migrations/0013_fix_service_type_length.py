# Generated manually to fix service_type field length mismatch
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_remove_jobcard_grand_total_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="jobcard",
            name="service_type",
            field=models.CharField(
                db_index=True,
                help_text="Type of pest control service to be provided",
                max_length=255,
                verbose_name="Service Type",
            ),
        ),
        migrations.AlterField(
            model_name="jobcard",
            name="technician_name",
            field=models.CharField(
                db_index=True,
                help_text="Name of the technician assigned to this job",
                max_length=255,
                verbose_name="Technician Name",
            ),
        ),
    ]
