from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0106_merge_0104_0105'),
    ]

    operations = [
        migrations.AddField(
            model_name='inquiry',
            name='staff_whatsapp_status',
            field=models.CharField(
                blank=True,
                db_index=True,
                default='',
                help_text='Status of internal staff WhatsApp alert for this website lead',
                max_length=20,
                verbose_name='Staff WhatsApp Status',
            ),
        ),
        migrations.AddField(
            model_name='inquiry',
            name='staff_whatsapp_message_id',
            field=models.CharField(
                blank=True,
                default='',
                max_length=128,
                verbose_name='Staff WhatsApp Message ID',
            ),
        ),
        migrations.AddField(
            model_name='inquiry',
            name='staff_whatsapp_sent_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Staff WhatsApp Sent At',
            ),
        ),
        migrations.AddField(
            model_name='inquiry',
            name='staff_whatsapp_error',
            field=models.TextField(
                blank=True,
                default='',
                verbose_name='Staff WhatsApp Error',
            ),
        ),
    ]
