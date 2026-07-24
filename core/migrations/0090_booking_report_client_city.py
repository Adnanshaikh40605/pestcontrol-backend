from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0089_booking_report_client_remark'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookingreportclient',
            name='city',
            field=models.CharField(blank=True, db_index=True, default='', max_length=50),
        ),
        migrations.AddIndex(
            model_name='bookingreportclient',
            index=models.Index(fields=['city'], name='core_bookin_city_idx'),
        ),
        migrations.AddIndex(
            model_name='bookingreportclient',
            index=models.Index(fields=['city', 'name'], name='core_bookin_city_name_idx'),
        ),
    ]
