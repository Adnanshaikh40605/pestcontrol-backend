"""
AWS S3 (and local) storage backends for PestControl99 media.

Folder layout in bucket:
  featured_images/    — blog featured + variants
  quill_uploads/      — rich-text editor inline images
  technician_selfies/ — partner app start-job selfies
  profiles/           — partner profile photos
  quotations/         — future quotation attachments
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils import timezone

try:
    from storages.backends.s3boto3 import S3Boto3Storage
except ImportError:  # pragma: no cover
    S3Boto3Storage = None  # type: ignore


def _use_s3() -> bool:
    return bool(getattr(settings, 'USE_AWS', False))


def _s3_kwargs():
    return {
        'file_overwrite': False,
        'default_acl': getattr(settings, 'AWS_DEFAULT_ACL', None),
        'querystring_auth': False,
        'object_parameters': getattr(settings, 'AWS_S3_OBJECT_PARAMETERS', {}),
    }


if S3Boto3Storage is not None:

    class _S3Base(S3Boto3Storage):
        def __init__(self, *args, **kwargs):
            opts = _s3_kwargs()
            opts.update(kwargs)
            super().__init__(*args, **opts)

    class BlogFeaturedS3Storage(_S3Base):
        location = 'featured_images'

    class BlogEditorS3Storage(_S3Base):
        location = 'quill_uploads'

    class SelfieS3Storage(_S3Base):
        location = 'technician_selfies'

    class ProfileS3Storage(_S3Base):
        location = 'profiles'

    class QuotationS3Storage(_S3Base):
        location = 'quotations'


def _local_storage(subdir: str) -> FileSystemStorage:
    root = Path(settings.MEDIA_ROOT) / subdir
    root.mkdir(parents=True, exist_ok=True)
    base = settings.MEDIA_URL.rstrip('/') + f'/{subdir}/'
    return FileSystemStorage(location=str(root), base_url=base)


@lru_cache(maxsize=8)
def get_blog_featured_storage():
    if _use_s3() and S3Boto3Storage is not None:
        return BlogFeaturedS3Storage()
    return _local_storage('featured_images')


@lru_cache(maxsize=8)
def get_blog_editor_storage():
    if _use_s3() and S3Boto3Storage is not None:
        return BlogEditorS3Storage()
    return _local_storage('quill_uploads')


@lru_cache(maxsize=8)
def get_selfie_storage():
    if _use_s3() and S3Boto3Storage is not None:
        return SelfieS3Storage()
    return _local_storage('technician_selfies')


@lru_cache(maxsize=8)
def get_profile_storage():
    if _use_s3() and S3Boto3Storage is not None:
        return ProfileS3Storage()
    return _local_storage('profiles')


@lru_cache(maxsize=8)
def get_quotation_storage():
    if _use_s3() and S3Boto3Storage is not None:
        return QuotationS3Storage()
    return _local_storage('quotations')


def dated_upload_path(prefix: str = '') -> str:
    """YYYY/MM/uuid.webp under the storage location."""
    name = f'{uuid.uuid4().hex}.webp'
    dated = f'{timezone.now().year}/{timezone.now().month:02d}/{name}'
    return f'{prefix}{dated}' if prefix else dated


def blog_featured_upload_path(instance, filename):
    return dated_upload_path()


def blog_thumbnail_upload_path(instance, filename):
    return dated_upload_path(f'{uuid.uuid4().hex}_thumb_')


def blog_medium_upload_path(instance, filename):
    return dated_upload_path(f'{uuid.uuid4().hex}_medium_')


def selfie_upload_path(instance, filename):
    return f'{timezone.now().year}/{timezone.now().month:02d}/{uuid.uuid4().hex}.webp'


def profile_upload_path(instance, filename):
    return f'{timezone.now().year}/{uuid.uuid4().hex}.webp'


def editor_upload_path() -> str:
    return dated_upload_path()
