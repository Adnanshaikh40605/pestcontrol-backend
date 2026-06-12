"""User theme preference API."""

import logging

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ThemePreference, UserPreference

logger = logging.getLogger(__name__)


class _DefaultThemePreference:
    theme = ThemePreference.LIGHT


class UserThemeView(APIView):
    """
    GET  /api/v1/users/theme/  → { "theme": "DARK" }
    PATCH /api/v1/users/theme/ → body { "theme": "LIGHT" | "DARK" | "SYSTEM" }
    """

    permission_classes = [IsAuthenticated]

    def _preference(self, user):
        try:
            pref, _ = UserPreference.objects.get_or_create(
                user=user,
                defaults={'theme': ThemePreference.LIGHT},
            )
            return pref
        except Exception as exc:
            logger.warning('UserPreference unavailable for %s: %s', user.id, exc)
            return _DefaultThemePreference()

    def get(self, request):
        pref = self._preference(request.user)
        return Response({'theme': pref.theme})

    def patch(self, request):
        raw = request.data.get('theme')
        if not raw:
            return Response(
                {'theme': ['This field is required.']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        value = str(raw).strip().upper()
        valid = {c.value for c in ThemePreference}
        if value not in valid:
            return Response(
                {'theme': [f'Must be one of: {", ".join(sorted(valid))}']},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pref = self._preference(request.user)
        if isinstance(pref, _DefaultThemePreference):
            return Response(
                {'theme': ['Theme preferences are not available until database migrations are applied.']},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        pref.theme = value
        pref.save(update_fields=['theme', 'updated_at'])
        return Response({'theme': pref.theme})
