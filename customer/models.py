from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.utils import timezone


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
    password = models.CharField(max_length=255, blank=True, default='')
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

    def set_password(self, raw_password: str | None) -> None:
        if raw_password:
            self.password = make_password(raw_password)
        else:
            # Passwordless OTP accounts — password login will always fail.
            self.password = make_password(None)

    def check_password(self, raw_password: str) -> bool:
        if not self.password:
            return False
        return check_password(raw_password, self.password)


class CustomerOTPChallenge(models.Model):
    """Short-lived 4-digit OTP for passwordless login / register."""

    PURPOSE_LOGIN = 'login'
    PURPOSE_REGISTER = 'register'
    PURPOSE_CHOICES = (
        (PURPOSE_LOGIN, 'Login'),
        (PURPOSE_REGISTER, 'Register'),
    )

    mobile = models.CharField(max_length=10, db_index=True)
    purpose = models.CharField(max_length=20, choices=PURPOSE_CHOICES, db_index=True)
    otp_hash = models.CharField(max_length=255)
    full_name = models.CharField(max_length=255, blank=True, default='')
    attempts = models.PositiveSmallIntegerField(default=0)
    expires_at = models.DateTimeField(db_index=True)
    consumed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Customer OTP Challenge'
        verbose_name_plural = 'Customer OTP Challenges'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mobile', 'purpose', '-created_at']),
        ]

    def __str__(self):
        return f'{self.mobile} · {self.purpose}'

    @property
    def is_expired(self) -> bool:
        return timezone.now() >= self.expires_at

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    def set_otp(self, otp: str) -> None:
        self.otp_hash = make_password(otp)

    def check_otp(self, otp: str) -> bool:
        return check_password(otp, self.otp_hash)


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
