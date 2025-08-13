from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.management import call_command

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superuser for testing APIs'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='admin',
            help='Username for superuser (default: admin)'
        )
        parser.add_argument(
            '--email',
            type=str,
            default='admin@pestcontrol.com',
            help='Email for superuser (default: admin@pestcontrol.com)'
        )
        parser.add_argument(
            '--password',
            type=str,
            default='admin123',
            help='Password for superuser (default: admin123)'
        )

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']

        try:
            # Check if user already exists
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'User "{username}" already exists')
                )
                return

            # Create superuser
            user = User.objects.create_superuser(
                username=username,
                email=email,
                password=password
            )

            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully created superuser:\n'
                    f'Username: {username}\n'
                    f'Email: {email}\n'
                    f'Password: {password}'
                )
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error creating superuser: {str(e)}')
            ) 