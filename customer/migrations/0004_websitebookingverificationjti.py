from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0003_otp_purpose_website_booking'),
    ]

    operations = [
        migrations.CreateModel(
            name='WebsiteBookingVerificationJti',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jti', models.CharField(db_index=True, max_length=64, unique=True)),
                ('mobile', models.CharField(db_index=True, max_length=10)),
                ('expires_at', models.DateTimeField(db_index=True)),
                ('consumed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Website Booking Verification JTI',
                'verbose_name_plural': 'Website Booking Verification JTIs',
            },
        ),
    ]
