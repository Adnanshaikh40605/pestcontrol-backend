"""Stream uploaded media for CRM <img> tags when /media/ is not mounted on the API host."""

import mimetypes

from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .media_urls import is_safe_media_path


def _storage_for_path(path: str):
    """Return (storage, relative_key) for a whitelisted media path."""
    from backend.media_storage import (
        get_blog_editor_storage,
        get_blog_featured_storage,
        get_profile_storage,
        get_selfie_storage,
    )

    scoped = (
        ('technician_selfies/', get_selfie_storage),
        ('job_selfies/', get_selfie_storage),
        ('featured_images/', get_blog_featured_storage),
        ('quill_uploads/', get_blog_editor_storage),
        ('profiles/', get_profile_storage),
    )
    for prefix, factory in scoped:
        if path.startswith(prefix):
            storage = factory()
            return storage, path[len(prefix):]
    return default_storage, path


def open_media_file(path: str):
    """Open a media file from S3 or local storage."""
    storage, key = _storage_for_path(path)
    if storage.exists(key):
        return storage.open(key, 'rb')
    if storage is not default_storage and default_storage.exists(path):
        return default_storage.open(path, 'rb')
    if default_storage.exists(key):
        return default_storage.open(key, 'rb')
    return None


class MediaFileView(APIView):
    """
    GET /api/v1/media-file/?path=technician_selfies/2026/05/file.webp
    Public read for whitelisted prefixes (selfies shown in CRM).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        path = (request.query_params.get('path') or '').strip()
        if not is_safe_media_path(path):
            raise Http404('Invalid path')

        try:
            file_handle = open_media_file(path)
            if file_handle is None:
                raise Http404('File not found')
        except Http404:
            raise
        except Exception as exc:
            raise Http404('File not found') from exc

        content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        response = FileResponse(file_handle, content_type=content_type)
        response['Cache-Control'] = 'public, max-age=86400'
        return response
