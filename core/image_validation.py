"""Shared image upload validation (blog, selfies, profiles)."""

from __future__ import annotations

from django.conf import settings

ALLOWED_IMAGE_EXTENSIONS = frozenset({'.jpg', '.jpeg', '.png', '.webp'})
ALLOWED_IMAGE_CONTENT_TYPES = frozenset({
    'image/jpeg',
    'image/png',
    'image/webp',
})

BLOCKED_EXTENSIONS = frozenset({
    '.svg', '.exe', '.pdf', '.zip', '.gif', '.bmp', '.tif', '.tiff', '.ico', '.html', '.js',
})


def max_upload_bytes() -> int:
    mb = int(getattr(settings, 'IMAGE_MAX_MB', 10))
    return mb * 1024 * 1024


def validate_image_upload(image_file, *, max_mb: int | None = None) -> None:
    """
    Raise ValueError if file is not an allowed image or exceeds size limit.
    Blocks SVG, PDF, ZIP, executables, etc.
    """
    limit = (max_mb or int(getattr(settings, 'IMAGE_MAX_MB', 10))) * 1024 * 1024
    size = getattr(image_file, 'size', 0) or 0
    if size > limit:
        mb = limit / (1024 * 1024)
        raise ValueError(f'Image must be under {mb:.0f} MB.')

    name = (getattr(image_file, 'name', '') or '').lower()
    if name:
        for blocked in BLOCKED_EXTENSIONS:
            if name.endswith(blocked):
                raise ValueError(f'File type not allowed: {blocked}')
        if not any(name.endswith(ext) for ext in ALLOWED_IMAGE_EXTENSIONS):
            raise ValueError('Only JPG, PNG, and WebP images are allowed.')

    content_type = (getattr(image_file, 'content_type', '') or '').lower()
    if content_type and content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise ValueError(f'Invalid file type: {content_type}. Only JPEG, PNG, and WebP are allowed.')
