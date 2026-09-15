from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('customer', '0002_customerotpchallenge_and_passwordless'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customerotpchallenge',
            name='purpose',
            field=models.CharField(
                choices=[
                    ('login', 'Login'),
                    ('register', 'Register'),
                    ('website_booking', 'Website booking'),
                ],
                db_index=True,
                max_length=20,
            ),
        ),
    ]
