from django.core.files.storage import default_storage


def storage_url(path: str) -> str:
    """Public URL for a stored file path (S3 or local)."""
    return default_storage.url(path)


def resolve_file_field_url(file_field, request=None) -> str | None:
    if not file_field:
        return None
    try:
        url = file_field.url
    except Exception:
        return None
    if url.startswith(("http://", "https://")):
        return url
    if request:
        return request.build_absolute_uri(url)
    return url
