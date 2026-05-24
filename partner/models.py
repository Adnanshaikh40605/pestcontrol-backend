from django.db import models
from django.contrib.auth.hashers import make_password, check_password

from backend.media_storage import get_profile_storage, profile_upload_path


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
        upload_to=profile_upload_path,
        storage=get_profile_storage,
        blank=True,
        null=True,
        verbose_name="Profile Image",
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
    is_app_approved = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Partner App Approved",
        help_text="CRM admin must approve before technician can use the mobile app",
    )
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


class PartnerRevokedJti(models.Model):
    """Blacklisted refresh-token JTIs after rotation or logout."""

    jti = models.CharField(max_length=64, unique=True, db_index=True)
    revoked_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(db_index=True)

    class Meta:
        verbose_name = 'Partner Revoked Token JTI'
        verbose_name_plural = 'Partner Revoked Token JTIs'

    def __str__(self):
        return self.jti


class PartnerNotification(models.Model):
    """In-app notification history for partner app."""

    class NotificationType(models.TextChoices):
        NEW_BOOKING = 'new_booking', 'New Booking'
        BOOKING_ASSIGNED = 'booking_assigned', 'Booking Assigned'
        BOOKING_ACCEPTED = 'booking_accepted', 'Booking Accepted'
        BOOKING_CANCELLED = 'booking_cancelled', 'Booking Cancelled'
        COMPLAINT_CALL = 'complaint_call', 'Complaint Call'
        SERVICE_REMINDER = 'service_reminder', 'Service Reminder'
        AMC_FOLLOWUP = 'amc_followup', 'AMC Follow-up'
        PAYMENT_PENDING = 'payment_pending', 'Payment Pending'
        JOB_COMPLETED = 'job_completed', 'Job Completed'
        GENERAL = 'general', 'General'

    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='notifications',
    )
    notification_type = models.CharField(
        max_length=40,
        choices=NotificationType.choices,
        default=NotificationType.GENERAL,
        db_index=True,
    )
    title = models.CharField(max_length=255)
    body = models.TextField()
    booking = models.ForeignKey(
        'core.JobCard',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partner_notifications',
    )
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Partner Notification'
        verbose_name_plural = 'Partner Notifications'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.partner_id}: {self.title}'


class CrmPartnerEvent(models.Model):
    """Events from partner app for CRM dashboard / future web push."""

    class EventType(models.TextChoices):
        BOOKING_SENT_TO_APP = 'booking_sent_to_app', 'Sent To App'
        BOOKING_ACCEPTED = 'booking_accepted', 'Booking Accepted'
        SERVICE_STARTED = 'service_started', 'Service Started'
        JOB_COMPLETED = 'job_completed', 'Job Completed'
        BOOKING_REJECTED = 'booking_rejected', 'Booking Rejected'

    job = models.ForeignKey(
        'core.JobCard',
        on_delete=models.CASCADE,
        related_name='crm_partner_events',
    )
    event_type = models.CharField(max_length=40, choices=EventType.choices, db_index=True)
    message = models.TextField()
    data = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'CRM Partner Event'
        verbose_name_plural = 'CRM Partner Events'
        ordering = ['-created_at']

    def __str__(self):
        return f'Job #{self.job_id}: {self.event_type}'


class PartnerDeviceToken(models.Model):
    """FCM registration token for partner mobile devices."""

    class DeviceType(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'

    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='device_tokens',
    )
    fcm_token = models.CharField(max_length=512, unique=True, db_index=True)
    device_type = models.CharField(
        max_length=20,
        choices=DeviceType.choices,
        default=DeviceType.ANDROID,
    )
    is_active = models.BooleanField(default=True, db_index=True)
    last_used_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Partner Device Token'
        verbose_name_plural = 'Partner Device Tokens'
        indexes = [
            models.Index(fields=['partner', 'is_active']),
        ]

    def __str__(self):
        return f'{self.partner_id}: {self.fcm_token[:20]}…'


class PartnerReferral(models.Model):
    """
    Client referral submitted from the partner mobile app.
    Linked 1:1 to a CRM inquiry for staff workflow and status updates.
    """

    partner = models.ForeignKey(
        Partner,
        on_delete=models.CASCADE,
        related_name='referrals',
        verbose_name='Referred By (Partner)',
    )
    client_name = models.CharField(max_length=255, db_index=True)
    mobile = models.CharField(max_length=10, db_index=True)
    area = models.CharField(max_length=500, blank=True, default='')
    crm_inquiry = models.OneToOneField(
        'core.CRMInquiry',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='partner_referral',
        verbose_name='CRM Inquiry',
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Partner Referral'
        verbose_name_plural = 'Partner Referrals'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['partner', '-created_at']),
        ]

    def __str__(self):
        return f'{self.client_name} ({self.mobile}) via {self.partner.full_name}'
