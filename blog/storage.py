from django.core.files.storage import default_storage

from backend.media_storage import get_blog_editor_storage, get_blog_featured_storage


def storage_url(path: str, *, editor: bool = False) -> str:
    """Public URL for a stored file path (S3 or local)."""
    storage = get_blog_editor_storage() if editor else get_blog_featured_storage()
    try:
        return storage.url(path)
    except Exception:
        return default_storage.url(path)


def resolve_file_field_url(file_field, request=None) -> str | None:
    if not file_field:
        return None
    try:
        url = file_field.url
    except Exception:
        return None
    if url.startswith(('http://', 'https://')):
        return url
    if request:
        return request.build_absolute_uri(url)
    return url
