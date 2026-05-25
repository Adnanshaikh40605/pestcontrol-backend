"""Partner mobile app version policy (APK distribution, force update)."""

from django.db import models


class PartnerAppVersionConfig(models.Model):
    """
    Singleton configuration for partner app version checks.
    Manage via Django Admin — only one row (pk=1) is used.
    """

    latest_version = models.CharField(
        max_length=20,
        default='2.0.0',
        help_text='Latest APK version released by the company (e.g. 2.0.0)',
    )
    minimum_supported_version = models.CharField(
        max_length=20,
        default='0.1.0',
        help_text='Oldest app version allowed to run when force update is enabled',
    )
    force_update = models.BooleanField(
        default=False,
        help_text='When enabled, apps below minimum_supported_version are blocked',
    )
    update_title = models.CharField(
        max_length=120,
        default='New Update Available',
    )
    update_message = models.TextField(
        default=(
            'A new version of the Partner App is available. '
            'Please uninstall the old app and install the latest APK shared by the company.'
        ),
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
