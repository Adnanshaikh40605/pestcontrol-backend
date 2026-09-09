# Generated manually for permanent technician delete cascade safety.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0112_reminder_booking_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='techniciansettlement',
            name='technician',
            field=models.ForeignKey(
                blank=True,
                help_text=(
                    'Owning technician. Null when the technician was permanently deleted; '
                    'settlement financial history is retained.'
                ),
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='settlements',
                to='core.technician',
                verbose_name='Technician',
            ),
        ),
    ]
