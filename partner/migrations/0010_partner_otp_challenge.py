from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partner', '0009_partner_leave_request'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnerOTPChallenge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mobile', models.CharField(db_index=True, max_length=10)),
                ('purpose', models.CharField(db_index=True, default='password_reset', max_length=32)),
                ('otp_hash', models.CharField(max_length=255)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('consumed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Partner OTP Challenge',
                'verbose_name_plural': 'Partner OTP Challenges',
                'ordering': ['-created_at'],
                'indexes': [
                    models.Index(fields=['mobile', 'purpose', '-created_at'], name='partner_par_mobile_otp_idx'),
                ],
            },
        ),
    ]
