import uuid
import logging
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.core.files.base import ContentFile

from .models import Blog
from .utils import generate_responsive_images

logger = logging.getLogger(__name__)


def _delete_image_file(image_field):
    """Safely delete a stored image file."""
    if image_field and image_field.name:
        try:
            if image_field.storage.exists(image_field.name):
                image_field.storage.delete(image_field.name)
        except Exception as exc:
            logger.warning("Could not delete image %s: %s", image_field.name, exc)


# Track the original featured_image path before save
_original_image_paths: dict = {}


def _tracking_key(instance):
    """New rows have no pk until insert; use object id so we never use None as dict key."""
    if instance.pk is not None:
        return instance.pk
    return id(instance)


@receiver(pre_save, sender=Blog)
def capture_original_image(sender, instance, **kwargs):
    """
    Before saving, record the current featured_image path so we can
    detect a new upload after saving.
    """
    key = _tracking_key(instance)
    if instance.pk:
        try:
            original = Blog.objects.only("featured_image").get(pk=instance.pk)
            _original_image_paths[key] = original.featured_image.name if original.featured_image else None
        except Blog.DoesNotExist:
            _original_image_paths[key] = None
    else:
        _original_image_paths[key] = None


@receiver(post_save, sender=Blog)
def process_blog_images(sender, instance, created, **kwargs):
    """
    After save: if a new featured_image was uploaded, generate WebP variants.
    Skips processing if the image hasn't changed.
    """
    # Match the key used in pre_save (pk for updates, id(instance) for creates)
    track_key = id(instance) if created else instance.pk

    if not instance.featured_image:
        _original_image_paths.pop(track_key, None)
        return

    original_path = _original_image_paths.pop(track_key, None)
    current_path = instance.featured_image.name

    # Skip if image hasn't changed (e.g. just a text edit)
    if not created and original_path and original_path == current_path:
        return

    try:
        instance.featured_image.seek(0)
        variants = generate_responsive_images(instance.featured_image)

        def _save_variant(field_name: str, buffer, suffix: str):
            filename = f"{uuid.uuid4().hex}_{suffix}.webp"
            content = ContentFile(buffer.read(), name=filename)
            field = getattr(instance, field_name)
            # Clean up old file if it exists
            if field and field.name:
                _delete_image_file(field)
            field.save(filename, content, save=False)

        _save_variant("image_thumbnail", variants["thumbnail"], "thumb")
        _save_variant("image_medium", variants["medium"], "medium")

        # Re-encode the original as a compressed full-size WebP
        instance.featured_image.seek(0)
        full_buffer = variants["full"]
        full_filename = f"{uuid.uuid4().hex}_full.webp"
        full_content = ContentFile(full_buffer.read(), name=full_filename)
        old_name = instance.featured_image.name
        instance.featured_image.save(full_filename, full_content, save=False)

        # Remove the original upload file if path changed
        if old_name and old_name != instance.featured_image.name:
            try:
                instance.featured_image.storage.delete(old_name)
            except Exception:
                pass

        # Persist the new image paths using a direct DB update (avoids re-triggering signal)
        Blog.objects.filter(pk=instance.pk).update(
            featured_image=instance.featured_image.name,
            image_thumbnail=instance.image_thumbnail.name,
            image_medium=instance.image_medium.name,
        )

    except Exception as exc:
        logger.error("Image processing failed for Blog pk=%s: %s", instance.pk, exc)


@receiver(pre_delete, sender=Blog)
def delete_blog_images(sender, instance, **kwargs):
    """Clean up all image files when a Blog is deleted."""
    for field_name in ("featured_image", "image_thumbnail", "image_medium"):
        _delete_image_file(getattr(instance, field_name))
