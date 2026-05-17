# Generated manually

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('blog', '0003_alter_tag_name_alter_tag_slug'),
    ]

    operations = [
        migrations.CreateModel(
            name='BlogAuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True, db_index=True)),
                ('action', models.CharField(
                    choices=[
                        ('login', 'Login'),
                        ('blog_created', 'Blog Created'),
                        ('blog_edited', 'Blog Edited'),
                        ('blog_published', 'Blog Published'),
                        ('blog_unpublished', 'Blog Unpublished'),
                        ('blog_deleted', 'Blog Deleted'),
                        ('image_uploaded', 'Image Uploaded'),
                    ],
                    db_index=True,
                    max_length=32,
                )),
                ('details', models.TextField(blank=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.CharField(blank=True, max_length=512)),
                ('blog', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='audit_logs',
                    to='blog.blog',
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='blog_audit_logs',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'verbose_name': 'Blog Audit Log',
                'verbose_name_plural': 'Blog Audit Logs',
                'ordering': ['-created_at'],
            },
        ),
    ]
