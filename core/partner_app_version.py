"""Partner mobile app version policy (Play Store force update)."""

from django.db import models


class PartnerAppVersionConfig(models.Model):
    """
    Singleton configuration for partner app version checks.
    Manage via Django Admin — only one row (pk=1) is used.
    """

    latest_version = models.CharField(
        max_length=20,
        default='2.0.8',
        help_text='Latest Play Store version (e.g. 2.0.8)',
    )
    minimum_supported_version = models.CharField(
        max_length=20,
        default='2.0.8',
        help_text='Oldest app version allowed when force update is enabled',
    )
    force_update = models.BooleanField(
        default=False,
        help_text='When enabled, apps below minimum_supported_version are blocked',
    )
    update_title = models.CharField(
        max_length=120,
        default='Please update the app.',
    )
    update_message = models.TextField(
        default='Please update the app.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Partner App Version'
        verbose_name_plural = 'Partner App Version'

    def __str__(self) -> str:
        return f'Partner App v{self.latest_version} (min {self.minimum_supported_version})'

    @classmethod
    def get_solo(cls) -> 'PartnerAppVersionConfig':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass
