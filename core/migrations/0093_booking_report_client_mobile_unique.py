from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0092_dedupe_booking_report_client_mobile'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='bookingreportclient',
            name='core_bookin_mobile_77cf6b_idx',
        ),
        migrations.AlterField(
            model_name='bookingreportclient',
            name='mobile',
            field=models.CharField(db_index=True, max_length=20, unique=True),
        ),
    ]
