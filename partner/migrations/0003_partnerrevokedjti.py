from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('partner', '0002_partner_is_app_approved'),
    ]

    operations = [
        migrations.CreateModel(
            name='PartnerRevokedJti',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('jti', models.CharField(db_index=True, max_length=64, unique=True)),
                ('revoked_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField(db_index=True)),
            ],
            options={
                'verbose_name': 'Partner Revoked Token JTI',
                'verbose_name_plural': 'Partner Revoked Token JTIs',
            },
        ),
    ]
