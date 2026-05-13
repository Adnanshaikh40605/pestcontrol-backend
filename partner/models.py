from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Partner(models.Model):
    """
    Partner model for Technicians who use the mobile Partner App.
    This is SEPARATE from core.Technician (CRM staff list).
    Each Partner gets JWT login credentials for the mobile app.
    """

    class Role(models.TextChoices):
        TECHNICIAN = 'technician', 'Technician'
        TECHNICIAN_ADMIN = 'technician_admin', 'Technician Admin'

    full_name = models.CharField(max_length=255, verbose_name="Full Name")
    mobile = models.CharField(max_length=15, unique=True, verbose_name="Mobile Number")
    password = models.CharField(max_length=255, verbose_name="Password (hashed)")
    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.TECHNICIAN,
        verbose_name="Role"
    )

    # Profile
    profile_image = models.ImageField(
        upload_to='partner_profiles/',
        blank=True,
        null=True,
        verbose_name="Profile Image"
    )
    fcm_token = models.TextField(
        blank=True,
        null=True,
        verbose_name="FCM Push Token",
        help_text="Firebase Cloud Messaging token for push notifications"
    )

    # Bank details
    bank_name = models.CharField(max_length=200, blank=True, null=True)
    account_number = models.CharField(max_length=30, blank=True, null=True)
    ifsc_code = models.CharField(max_length=20, blank=True, null=True)
    account_holder_name = models.CharField(max_length=255, blank=True, null=True)

    # Link to core Technician record (optional — for CRM assignment)
    core_technician = models.OneToOneField(
        'core.Technician',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partner_account',
        verbose_name="CRM Technician Record",
        help_text="Links this partner account to the CRM technician record"
    )

    is_active = models.BooleanField(default=True, verbose_name="Is Active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Partner"
        verbose_name_plural = "Partners"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} ({self.mobile}) - {self.role}"

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)


class PartnerEarning(models.Model):
    """
    Tracks earnings for each partner per completed job.
    """
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='earnings',
        verbose_name="Partner"
    )
    job = models.ForeignKey(
        'core.JobCard',
        on_delete=models.CASCADE,
        related_name='partner_earnings',
        verbose_name="Job"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name="Earning Amount"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Partner Earning"
        verbose_name_plural = "Partner Earnings"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.partner.full_name} - ₹{self.amount} for Job #{self.job_id}"


class PartnerRating(models.Model):
    """
    Customer ratings for partner (technician) after job completion.
    """
    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='ratings',
        verbose_name="Partner"
    )
    job = models.ForeignKey(
        'core.JobCard',
        on_delete=models.CASCADE,
        related_name='partner_ratings',
        verbose_name="Job"
    )
    rating = models.IntegerField(
        default=5,
        verbose_name="Rating (1-5)"
    )
    feedback = models.TextField(blank=True, null=True, verbose_name="Customer Feedback")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Partner Rating"
        verbose_name_plural = "Partner Ratings"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.partner.full_name} - {self.rating}★ for Job #{self.job_id}"
