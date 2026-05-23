import io
import logging
from PIL import Image
from django.conf import settings

from core.image_validation import validate_image_upload

logger = logging.getLogger(__name__)


def _image_sizes():
    quality = int(getattr(settings, 'IMAGE_WEBP_QUALITY', 82))
    max_w = int(getattr(settings, 'IMAGE_MAX_WIDTH', 1920))
    return {
        'thumbnail': (400, 250, quality),
        'medium': (800, 500, min(quality + 3, 95)),
        'full': (max_w, int(max_w * 0.625), quality),
    }


def validate_image_size(image_file):
    """Raise ValueError if image exceeds size limit or disallowed type."""
    validate_image_upload(image_file)


def read_image_field_bytes(image_field) -> bytes:
    """Read bytes from an ImageField (works for local disk and S3-backed files)."""
    image_field.open('rb')
    try:
        return image_field.read()
    finally:
        image_field.close()


def _open_image_safe(image_file):
    """Open an image from a Django UploadedFile, BytesIO, or ImageFieldFile safely."""
    try:
        from django.db.models.fields.files import FieldFile

        if isinstance(image_file, FieldFile):
            data = read_image_field_bytes(image_file)
            image_file = io.BytesIO(data)
        elif hasattr(image_file, 'seek'):
            image_file.seek(0)
        img = Image.open(image_file)
        img.load()
        return img
    except Exception as exc:
        logger.error("Failed to open image: %s", exc)
        raise ValueError(f"Invalid or corrupt image file: {exc}") from exc


def convert_to_webp(image_file, quality: int = 88) -> io.BytesIO:
    """
    Convert any uploaded image to WebP format.
    Returns a BytesIO buffer containing the WebP data.
    """
    img = _open_image_safe(image_file)

    # Preserve transparency for images that have it
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    buffer = io.BytesIO()
    img.save(buffer, format="WEBP", quality=quality, method=6)
    buffer.seek(0)
    return buffer


def generate_responsive_images(image_file) -> dict:
    """
    Generate thumbnail, medium, and full WebP variants.

    Returns:
        dict with keys 'thumbnail', 'medium', 'full',
        each being a BytesIO buffer.
    """
    img = _open_image_safe(image_file)

    # Normalize color mode
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
    else:
        img = img.convert("RGB")

    result = {}
    for size_name, (max_w, max_h, quality) in _image_sizes().items():
        resized = _resize_keep_aspect(img.copy(), max_w, max_h)
        buffer = io.BytesIO()
        resized.save(buffer, format="WEBP", quality=quality, method=6)
        buffer.seek(0)
        result[size_name] = buffer

    return result


def _resize_keep_aspect(img: Image.Image, max_w: int, max_h: int) -> Image.Image:
    """Resize image to fit within max_w x max_h while preserving aspect ratio."""
    orig_w, orig_h = img.size
    ratio = min(max_w / orig_w, max_h / orig_h, 1.0)  # Never upscale
    new_w = int(orig_w * ratio)
    new_h = int(orig_h * ratio)
    return img.resize((new_w, new_h), Image.LANCZOS)


def sanitize_html(html_content: str) -> str:
    """
    Sanitize HTML content to allow only safe tags.
    Falls back to basic stripping if bleach is not installed.
    """
    ALLOWED_TAGS = [
        "p", "br", "strong", "em", "b", "i", "u", "s",
        "h1", "h2", "h3", "h4", "h5", "h6",
        "ul", "ol", "li",
        "a", "img",
        "blockquote", "pre", "code",
        "table", "thead", "tbody", "tr", "th", "td",
        "figure", "figcaption",
        "div", "span",
        "hr",
        "iframe",
    ]
    ALLOWED_ATTRIBUTES = {
        "a": ["href", "title", "target", "rel"],
        "img": ["src", "alt", "title", "width", "height", "loading"],
        "iframe": ["src", "width", "height", "frameborder", "allowfullscreen", "allow"],
        "td": ["colspan", "rowspan"],
        "th": ["colspan", "rowspan", "scope"],
        "code": ["class"],
        "pre": ["class"],
        "div": ["class", "id", "data-type"],
        "span": ["class"],
        "p": ["class"],
        "h1": ["id"], "h2": ["id"], "h3": ["id"], "h4": ["id"],
        "h5": ["id"], "h6": ["id"],
    }
    try:
        import bleach
        return bleach.clean(
            html_content,
            tags=ALLOWED_TAGS,
            attributes=ALLOWED_ATTRIBUTES,
            strip=True,
        )
    except ImportError:
        logger.warning("bleach not installed; HTML content stored without sanitization.")
        return html_content


def calculate_reading_time(html_content: str) -> int:
    """Calculate estimated reading time in minutes (~200 wpm)."""
    import re
    text = re.sub(r"<[^>]+>", " ", html_content)
    word_count = len(text.split())
    return max(1, round(word_count / 200))


def build_webp_filename(prefix: str = "") -> str:
    """Generate a unique WebP filename."""
    import uuid
    suffix = f"_{prefix}" if prefix else ""
    return f"{uuid.uuid4().hex}{suffix}.webp"
