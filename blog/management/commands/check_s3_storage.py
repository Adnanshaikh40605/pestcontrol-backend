"""Verify blog media storage configuration (local vs S3)."""

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Check whether blog media storage (S3 or local) is configured and writable."

    def handle(self, *args, **options):
        use_aws = getattr(settings, 'USE_AWS', False)
        backend = settings.STORAGES['default']['BACKEND']

        self.stdout.write(f"USE_AWS: {use_aws}")
        self.stdout.write(f"Storage backend: {backend}")
        self.stdout.write(f"MEDIA_URL: {settings.MEDIA_URL}")

        if use_aws:
            bucket = getattr(settings, 'AWS_STORAGE_BUCKET_NAME', '')
            region = getattr(settings, 'AWS_S3_REGION_NAME', '')
            self.stdout.write(f"Bucket: {bucket}")
            self.stdout.write(f"Region: {region}")
            if not getattr(settings, 'AWS_ACCESS_KEY_ID', None):
                self.stdout.write(self.style.ERROR('AWS_ACCESS_KEY_ID is missing'))
                return
            if not getattr(settings, 'AWS_SECRET_ACCESS_KEY', None):
                self.stdout.write(self.style.ERROR('AWS_SECRET_ACCESS_KEY is missing'))
                return
        else:
            self.stdout.write(self.style.WARNING(
                'S3 is OFF — files save to local MEDIA_ROOT. Set USE_AWS=True in .env to use S3.'
            ))

        from backend.media_storage import get_blog_featured_storage

        storage = get_blog_featured_storage() if use_aws else default_storage
        test_path = '_storage_check.txt'
        try:
            saved = storage.save(test_path, ContentFile(b'blog storage ok'))
            url = storage.url(saved)
            storage.delete(saved)
            self.stdout.write(self.style.SUCCESS(f'Write test OK — sample URL: {url}'))
            acl = getattr(settings, 'AWS_DEFAULT_ACL', None)
            self.stdout.write(f'AWS_DEFAULT_ACL: {acl!r}')
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f'Write test FAILED: {exc}'))
            if 'AccessControlListNotSupported' in str(exc):
                self.stdout.write(self.style.WARNING(
                    'Bucket blocks ACLs — remove AWS_DEFAULT_ACL=public-read from Railway.'
                ))
