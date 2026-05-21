"""Stream uploaded media for CRM <img> tags when /media/ is not mounted on the API host."""

import mimetypes

from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from .media_urls import is_safe_media_path


class MediaFileView(APIView):
    """
    GET /api/v1/media-file/?path=job_selfies/2026/05/file.jpg
    Public read for whitelisted prefixes (job selfies shown in CRM).
    """

    permission_classes = [AllowAny]

    def get(self, request):
        path = (request.query_params.get('path') or '').strip()
        if not is_safe_media_path(path):
            raise Http404('Invalid path')

        if not default_storage.exists(path):
            raise Http404('File not found')

        try:
            file_handle = default_storage.open(path, 'rb')
        except Exception as exc:
            raise Http404('File not found') from exc

        content_type = mimetypes.guess_type(path)[0] or 'application/octet-stream'
        response = FileResponse(file_handle, content_type=content_type)
        response['Cache-Control'] = 'public, max-age=86400'
        return response
