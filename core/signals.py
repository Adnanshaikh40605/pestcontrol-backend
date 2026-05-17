from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile, CRMRole

User = get_user_model()


@receiver(post_save, sender=User)
def ensure_crm_profile(sender, instance, created, **kwargs):
    """Auto-create profile for new users; sync legacy superuser/staff flags."""
    if created:
        if instance.is_superuser:
            role = CRMRole.SUPER_ADMIN
        elif instance.is_staff:
            role = CRMRole.STAFF
        else:
            role = CRMRole.STAFF
        UserProfile.objects.get_or_create(user=instance, defaults={'role': role})
    elif not hasattr(instance, 'crm_profile'):
        if instance.is_superuser:
            UserProfile.objects.create(user=instance, role=CRMRole.SUPER_ADMIN)
        elif instance.is_staff:
            UserProfile.objects.create(user=instance, role=CRMRole.STAFF)
