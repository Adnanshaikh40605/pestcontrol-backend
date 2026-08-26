"""Customer mobile app version policy (Play Store force update)."""

from django.db import models


class CustomerAppVersionConfig(models.Model):
    """
    Singleton configuration for customer app version checks.
    Manage via Django Admin — only one row (pk=1) is used.
    """

    latest_version = models.CharField(
        max_length=20,
        default='1.0.4',
        help_text='Latest Play Store version (e.g. 1.0.4)',
    )
    minimum_supported_version = models.CharField(
        max_length=20,
        default='1.0.4',
        help_text='Oldest app version allowed when force update is enabled',
    )
    force_update = models.BooleanField(
        default=False,
        help_text='When enabled, apps below minimum_supported_version (and latest) are blocked',
    )
    update_title = models.CharField(
        max_length=120,
        default='Update required',
    )
    update_message = models.TextField(
        default='A new version of Pest Control 99 is available. Please update to continue.',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer App Version'
        verbose_name_plural = 'Customer App Version'

    def __str__(self) -> str:
        return f'Customer App v{self.latest_version} (min {self.minimum_supported_version})'

    @classmethod
    def get_solo(cls) -> 'CustomerAppVersionConfig':
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        pass
