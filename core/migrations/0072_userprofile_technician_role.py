from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0071_jobcard_partner_workflow_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='role',
            field=models.CharField(
                choices=[
                    ('super_admin', 'Super Admin'),
                    ('admin', 'Admin'),
                    ('staff', 'Staff'),
                    ('technician', 'Technician'),
                    ('blog_user', 'Blog User'),
                ],
                db_index=True,
                default='staff',
                max_length=20,
            ),
        ),
    ]
