"""
Management command to create default users for the pest control application.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create default users for the pest control application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='pest99',
            help='Username for the default user (default: pest99)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='pest99',
            help='Password for the default user (default: pest99)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@pestcontrol99.com',
            help='Email for the default user'
        )

    def handle(self, *args, **options):
        username = options['username']
        password = options['password']
        email = options['email']

        # Check if user already exists
        if User.objects.filter(username=username).exists():
            self.stdout.write(
                self.style.WARNING(f'User "{username}" already exists.')
            )
            return

        # Create the user
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            is_staff=True,
            is_superuser=True,
            first_name='Admin',
            last_name='User'
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created user "{username}" with email "{email}"'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Login credentials: Username: {username}, Password: {password}'
            )
        )
