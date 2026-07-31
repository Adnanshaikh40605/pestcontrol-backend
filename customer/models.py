from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class CustomerAccount(models.Model):
    """
    Mobile-app login identity for end customers.
    Linked 1:1 to core.Client (CRM customer record keyed by mobile).
    """

    client = models.OneToOneField(
        'core.Client',
        on_delete=models.CASCADE,
        related_name='customer_account',
        verbose_name='CRM Client',
    )
    mobile = models.CharField(max_length=10, unique=True, db_index=True)
    password = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, default='')
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Customer Account'
        verbose_name_plural = 'Customer Accounts'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.full_name} ({self.mobile})'

    def set_password(self, raw_password: str) -> None:
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.password)


class CustomerRevokedJti(models.Model):
    """Revoked customer refresh-token JTIs (rotation / logout)."""

    jti = models.CharField(max_length=64, unique=True, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Customer Revoked JTI'
        verbose_name_plural = 'Customer Revoked JTIs'

    def __str__(self):
        return self.jti
