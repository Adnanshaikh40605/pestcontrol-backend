from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customeraccount',
            name='password',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.CreateModel(
            name='CustomerOTPChallenge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('mobile', models.CharField(db_index=True, max_length=10)),
                ('purpose', models.CharField(choices=[('login', 'Login'), ('register', 'Register')], db_index=True, max_length=20)),
                ('otp_hash', models.CharField(max_length=255)),
                ('full_name', models.CharField(blank=True, default='', max_length=255)),
                ('attempts', models.PositiveSmallIntegerField(default=0)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('consumed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Customer OTP Challenge',
                'verbose_name_plural': 'Customer OTP Challenges',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='customerotpchallenge',
            index=models.Index(fields=['mobile', 'purpose', '-created_at'], name='customer_cu_mobile_9f3c1a_idx'),
        ),
    ]
