# Generated manually for blog_user role

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def forwards_create_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('core', 'UserProfile')
    for user in User.objects.all():
        if UserProfile.objects.filter(user_id=user.id).exists():
            continue
        if user.is_superuser:
            role = 'super_admin'
        elif user.is_staff:
            role = 'staff'
        else:
            role = 'staff'
        UserProfile.objects.create(user_id=user.id, role=role)


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0069_jobcard_booking_category_upcoming_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, help_text='Date and time when the record was created', verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True, help_text='Date and time when the record was last updated', verbose_name='Updated At')),
                ('role', models.CharField(
                    choices=[
                        ('super_admin', 'Super Admin'),
                        ('admin', 'Admin'),
                        ('staff', 'Staff'),
                        ('blog_user', 'Blog User'),
                    ],
                    db_index=True,
                    default='staff',
                    max_length=20,
                )),
                ('user', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='crm_profile',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'User Profile',
                'verbose_name_plural': 'User Profiles',
            },
        ),
        migrations.RunPython(forwards_create_profiles, migrations.RunPython.noop),
    ]
