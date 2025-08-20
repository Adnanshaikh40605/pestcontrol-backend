"""
Django management command to create a superuser for Railway deployment
Usage: python manage.py create_admin
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.management import CommandError
from decouple import config


class Command(BaseCommand):
    help = 'Create a superuser for Railway deployment'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Superuser username',
            default='admin'
        )
        parser.add_argument(
            '--email',
            type=str,
            help='Superuser email',
            default='admin@pestcontrol.com'
        )
        parser.add_argument(
            '--password',
            type=str,
            help='Superuser password (use environment variable for security)'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force create even if user exists (will update password)'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        force = options['force']

        # Try to get password from environment variable if not provided
        if not password:
            password = config('DJANGO_SUPERUSER_PASSWORD', default=None)
        
        if not password:
            self.stdout.write(
                self.style.ERROR('Password is required. Use --password or set DJANGO_SUPERUSER_PASSWORD environment variable')
            )
            return

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            if not force:
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists. Use --force to update password.')
                )
                return
            else:
                # Update existing user
                user = User.objects.get(username=username)
                user.set_password(password)
                user.email = email
                user.is_staff = True
                user.is_superuser = True
                user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully updated superuser "{username}"')
                )
        else:
            # Create new superuser
            try:
                user = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password
                )
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully created superuser "{username}"')
                )
            except Exception as e:
                raise CommandError(f'Failed to create superuser: {e}')

        # Display access information
        self.stdout.write('\n' + '='*50)
        self.stdout.write(self.style.SUCCESS('🎉 Superuser created successfully!'))
        self.stdout.write('='*50)
        self.stdout.write(f'Username: {username}')
        self.stdout.write(f'Email: {email}')
        self.stdout.write('Password: [hidden for security]')
        self.stdout.write('\n📱 Access your admin panel at:')
        self.stdout.write('🏠 Local: http://localhost:8000/admin/')
        self.stdout.write('🚀 Railway: https://pestcontrol-backend-production.up.railway.app/admin/')
        self.stdout.write('='*50)

