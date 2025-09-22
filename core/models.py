from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError
from .validators import (
    validate_mobile_number, 
    validate_positive_decimal, 
    validate_non_negative_decimal,
    validate_job_code
)


class BaseModel(models.Model):
    """
    Abstract base model with timestamp fields and common functionality.
    """
    created_at = models.DateTimeField(
        auto_now_add=True, 
        db_index=True,
        verbose_name="Created At",
        help_text="Date and time when the record was created"
    )
    updated_at = models.DateTimeField(
        auto_now=True, 
        db_index=True,
        verbose_name="Updated At",
        help_text="Date and time when the record was last updated"
    )

    class Meta:
        abstract = True
        ordering = ['-created_at']


class Client(BaseModel):
    full_name = models.CharField(
        max_length=255, 
        db_index=True,
        verbose_name="Full Name",
        help_text="Complete name of the client"
    )
    mobile = models.CharField(
        max_length=10, 
        unique=True, 
        validators=[validate_mobile_number],
        db_index=True,
        verbose_name="Mobile Number",
        help_text="10-digit mobile number (must be unique)"
    )
    email = models.EmailField(
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Email Address",
        help_text="Client's email address (optional)"
    )
    city = models.CharField(
        max_length=100, 
        db_index=True,
        verbose_name="City",
        help_text="City where the client is located"
    )
    address = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Address",
        help_text="Complete address of the client (optional)"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Notes",
        help_text="Additional notes about the client (optional)"
    )
    is_active = models.BooleanField(
        default=True, 
        db_index=True,
        verbose_name="Is Active",
        help_text="Whether the client is currently active"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['full_name', 'mobile']),
            models.Index(fields=['city', 'is_active']),
        ]
        verbose_name = 'Client'
        verbose_name_plural = 'Clients'

    def __str__(self) -> str:
        return f"{self.full_name} ({self.mobile})"

    def clean(self):
        """Custom validation for the model with comprehensive business rules."""
        super().clean()
        if self.mobile:
            validate_mobile_number(self.mobile)
        
        # Business rule: Full name must be at least 2 characters
        if self.full_name and len(self.full_name.strip()) < 2:
            raise ValidationError({'full_name': 'Full name must be at least 2 characters long.'})
        
        # Business rule: City must be provided and not empty
        if not self.city or not self.city.strip():
            raise ValidationError({'city': 'City is required and cannot be empty.'})
        
        # Business rule: Email format validation if provided
        if self.email and self.email.strip():
            from django.core.validators import validate_email
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError({'email': 'Please enter a valid email address.'})


class Inquiry(BaseModel):
    class InquiryStatus(models.TextChoices):
        NEW = 'New', 'New'
        CONTACTED = 'Contacted', 'Contacted'
        CONVERTED = 'Converted', 'Converted'
        CLOSED = 'Closed', 'Closed'

    name = models.CharField(
        max_length=255, 
        db_index=True,
        verbose_name="Name",
        help_text="Name of the person making the inquiry"
    )
    mobile = models.CharField(
        max_length=10, 
        validators=[validate_mobile_number],
        db_index=True,
        verbose_name="Mobile Number",
        help_text="10-digit mobile number of the inquirer"
    )
    email = models.EmailField(
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Email Address",
        help_text="Email address of the inquirer (optional)"
    )
    message = models.TextField(
        verbose_name="Message",
        help_text="Detailed message or inquiry from the customer"
    )
    service_interest = models.CharField(
        max_length=255, 
        db_index=True,
        verbose_name="Service Interest",
        help_text="Type of pest control service the customer is interested in"
    )
    city = models.CharField(
        max_length=100, 
        db_index=True,
        verbose_name="City",
        help_text="City where the service is required"
    )
    status = models.CharField(
        max_length=20,
        choices=InquiryStatus.choices,
        default=InquiryStatus.NEW,
        db_index=True,
        verbose_name="Status",
        help_text="Current status of the inquiry"
    )
    is_read = models.BooleanField(
        default=False, 
        db_index=True,
        verbose_name="Is Read",
        help_text="Whether the inquiry has been read by staff"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'city']),
            models.Index(fields=['mobile', 'email']),
            models.Index(fields=['is_read', 'status']),
        ]
        verbose_name = 'Inquiry'
        verbose_name_plural = 'Inquiries'

    def __str__(self) -> str:
        return f"Inquiry: {self.name} ({self.mobile})"

    def clean(self):
        """Custom validation for the model with comprehensive business rules."""
        super().clean()
        if self.mobile:
            validate_mobile_number(self.mobile)
        
        # Business rule: Name must be at least 2 characters
        if self.name and len(self.name.strip()) < 2:
            raise ValidationError({'name': 'Name must be at least 2 characters long.'})
        
        # Business rule: Message must be provided and meaningful
        if not self.message or len(self.message.strip()) < 10:
            raise ValidationError({'message': 'Message must be at least 10 characters long.'})
        
        # Business rule: Service interest must be provided
        if not self.service_interest or not self.service_interest.strip():
            raise ValidationError({'service_interest': 'Service interest is required.'})
        
        # Business rule: City must be provided
        if not self.city or not self.city.strip():
            raise ValidationError({'city': 'City is required.'})


class JobCard(BaseModel):
    class JobStatus(models.TextChoices):
        ENQUIRY = 'Enquiry', 'Enquiry'
        WIP = 'WIP', 'WIP'
        DONE = 'Done', 'Done'
        HOLD = 'Hold', 'Hold'
        CANCEL = 'Cancel', 'Cancel'
        INACTIVE = 'Inactive', 'Inactive'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'Unpaid', 'Unpaid'
        PAID = 'Paid', 'Paid'
    
    class JobType(models.TextChoices):
        CUSTOMER = 'Customer', 'Customer'
        SOCIETY = 'Society', 'Society'
    
    class ContractDuration(models.TextChoices):
        TWELVE_MONTHS = '12', '12 Months'
        SIX_MONTHS = '6', '6 Months'
        THREE_MONTHS = '3', '3 Months'

    code = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True,
        validators=[validate_job_code],
        db_index=True,
        verbose_name="Job Code",
        help_text="Unique identifier for the job card (auto-generated)"
    )
    client = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        related_name='jobcards',
        db_index=True,
        verbose_name="Client",
        help_text="Client for whom this job card is created"
    )
    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
        default=JobType.CUSTOMER,
        db_index=True,
        verbose_name="Job Type",
        help_text="Type of job - Customer or Society"
    )
    contract_duration = models.CharField(
        max_length=2,
        choices=ContractDuration.choices,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Contract Duration",
        help_text="Duration of the service contract in months"
    )
    status = models.CharField(
        max_length=20, 
        choices=JobStatus.choices, 
        default=JobStatus.ENQUIRY,
        db_index=True,
        verbose_name="Status",
        help_text="Current status of the job card"
    )
    service_type = models.CharField(
        max_length=255, 
        db_index=True,
        verbose_name="Service Type",
        help_text="Type of pest control service to be provided"
    )
    schedule_date = models.DateField(
        db_index=True,
        verbose_name="Schedule Date",
        help_text="Date when the service is scheduled"
    )
    technician_name = models.CharField(
        max_length=255, 
        db_index=True,
        verbose_name="Technician Name",
        help_text="Name of the technician assigned to this job"
    )
    price = models.CharField(
        max_length=50,
        default='',
        verbose_name="Service Price",
        help_text="Service price as entered by user"
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PaymentStatus.choices, 
        default=PaymentStatus.UNPAID,
        db_index=True,
        verbose_name="Payment Status",
        help_text="Current payment status of the job"
    )
    next_service_date = models.DateField(
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Next Service Date",
        help_text="Date for the next scheduled service (optional)"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Notes",
        help_text="Additional notes about the job (optional)"
    )
    is_paused = models.BooleanField(
        default=False, 
        db_index=True,
        verbose_name="Is Paused",
        help_text="Whether the job is currently paused"
    )
    reference = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Reference",
        help_text="Source of reference for this job card"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'payment_status']),
            models.Index(fields=['schedule_date', 'status']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['technician_name', 'schedule_date']),
            models.Index(fields=['job_type', 'status']),
            models.Index(fields=['contract_duration', 'job_type']),
        ]
        verbose_name = 'Job Card'
        verbose_name_plural = 'Job Cards'

    def __str__(self) -> str:
        return self.code or f"JobCard {self.pk}"

    def clean(self):
        """Custom validation for the model with comprehensive business rules."""
        super().clean()
        
        # Business rule: Service type must be provided
        if not self.service_type or not self.service_type.strip():
            raise ValidationError({'service_type': 'Service type is required.'})
        
        # Business rule: Schedule date validation (allow past dates with warning)
        if self.schedule_date and self.schedule_date < timezone.now().date() and not self.pk:
            # Allow past dates but log a warning for audit purposes
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Job card created with past schedule date: {self.schedule_date} (today: {timezone.now().date()})")
            # Note: We allow past dates for cases like recording completed services, backdating, etc.
        
        # Business rule: Technician name must be provided
        if not self.technician_name or not self.technician_name.strip():
            raise ValidationError({'technician_name': 'Technician name is required.'})
        
        # Business rule: Price must be provided
        if not self.price or not self.price.strip():
            raise ValidationError({'price': 'Price is required.'})
        
        # Business rule: Contract duration validation for Society jobs
        if self.job_type == self.JobType.SOCIETY and not self.contract_duration:
            raise ValidationError({'contract_duration': 'Contract duration is required for Society jobs.'})
        
        # Business rule: Next service date validation
        if self.next_service_date and self.schedule_date and self.next_service_date <= self.schedule_date:
            raise ValidationError({'next_service_date': 'Next service date must be after schedule date.'})

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)

        # Generate code after initial save when PK is available
        if creating and not self.code:
            self.code = f"JC-{self.pk:04d}"
            super().save(update_fields=['code'])


class Renewal(BaseModel):
    class RenewalStatus(models.TextChoices):
        DUE = 'Due', 'Due'
        COMPLETED = 'Completed', 'Completed'
    
    class RenewalType(models.TextChoices):
        CONTRACT_RENEWAL = 'Contract', 'Contract Renewal'
        MONTHLY_REMINDER = 'Monthly', 'Monthly Reminder'
    
    class UrgencyLevel(models.TextChoices):
        HIGH = 'High', 'High'  # Red - Overdue or due today
        MEDIUM = 'Medium', 'Medium'  # Yellow - Due within 3 days
        NORMAL = 'Normal', 'Normal'  # Green - Due in more than 3 days

    jobcard = models.ForeignKey(
        JobCard, 
        on_delete=models.CASCADE, 
        related_name='renewals',
        db_index=True,
        verbose_name="Job Card",
        help_text="Job card associated with this renewal"
    )
    due_date = models.DateTimeField(
        default=timezone.now, 
        db_index=True,
        verbose_name="Due Date",
        help_text="Date and time when the renewal is due"
    )
    status = models.CharField(
        max_length=20, 
        choices=RenewalStatus.choices, 
        default=RenewalStatus.DUE,
        db_index=True,
        verbose_name="Status",
        help_text="Current status of the renewal"
    )
    renewal_type = models.CharField(
        max_length=20,
        choices=RenewalType.choices,
        default=RenewalType.CONTRACT_RENEWAL,
        db_index=True,
        verbose_name="Renewal Type",
        help_text="Type of renewal - Contract or Monthly reminder"
    )
    urgency_level = models.CharField(
        max_length=10,
        choices=UrgencyLevel.choices,
        default=UrgencyLevel.NORMAL,
        db_index=True,
        verbose_name="Urgency Level",
        help_text="Priority level based on due date proximity"
    )
    remarks = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Remarks",
        help_text="Additional remarks about the renewal (optional)"
    )

    class Meta:
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['jobcard', 'status']),
            models.Index(fields=['renewal_type', 'status']),
            models.Index(fields=['urgency_level', 'due_date']),
        ]
        verbose_name = 'Renewal'
        verbose_name_plural = 'Renewals'

    def __str__(self) -> str:
        return f"Renewal for {self.jobcard.code if self.jobcard_id else self.jobcard_id} on {self.due_date.date()}"
    
    def update_urgency_level(self):
        """Update urgency level based on due date."""
        from datetime import timedelta
        now = timezone.now()
        
        if self.due_date <= now:
            self.urgency_level = self.UrgencyLevel.HIGH
        elif self.due_date <= now + timedelta(days=3):
            self.urgency_level = self.UrgencyLevel.MEDIUM
        else:
            self.urgency_level = self.UrgencyLevel.NORMAL
    
    def save(self, *args, **kwargs):
        """Override save to automatically update urgency level and trigger related updates."""
        self.update_urgency_level()
        super().save(*args, **kwargs)
        
        # Trigger urgency level updates for related renewals if this is a jobcard update
        if hasattr(self, 'jobcard') and self.jobcard:
            # Update all related renewals for this jobcard
            from .services import RenewalService
            RenewalService.update_urgency_levels_for_jobcard(self.jobcard.id)


class DeviceToken(BaseModel):
    """
    Model to store device tokens for push notifications.
    """
    class DeviceType(models.TextChoices):
        ANDROID = 'android', 'Android'
        IOS = 'ios', 'iOS'
        WEB = 'web', 'Web'
    
    token = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        verbose_name="Device Token",
        help_text="Firebase device token for push notifications"
    )
    device_type = models.CharField(
        max_length=10,
        choices=DeviceType.choices,
        default=DeviceType.ANDROID,
        db_index=True,
        verbose_name="Device Type",
        help_text="Type of device (Android, iOS, Web)"
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name="User Agent",
        help_text="User agent string for web devices"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Is Active",
        help_text="Whether the device token is active"
    )
    last_used = models.DateTimeField(
        auto_now=True,
        db_index=True,
        verbose_name="Last Used",
        help_text="Last time this token was used"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['device_type', 'is_active']),
            models.Index(fields=['is_active', 'last_used']),
        ]
        verbose_name = 'Device Token'
        verbose_name_plural = 'Device Tokens'
    
    def __str__(self) -> str:
        return f"{self.device_type} - {self.token[:20]}..."
    
    def clean(self):
        """Custom validation for device token."""
        super().clean()
        
        # Business rule: Token must be provided and not empty
        if not self.token or not self.token.strip():
            raise ValidationError({'token': 'Device token is required and cannot be empty.'})
        
        # Business rule: Token should be reasonably long (Firebase tokens are typically 140+ characters)
        if len(self.token.strip()) < 50:
            raise ValidationError({'token': 'Device token appears to be too short.'})


class NotificationLog(BaseModel):
    """
    Model to log sent notifications for tracking and debugging.
    """
    class NotificationType(models.TextChoices):
        PUSH = 'push', 'Push Notification'
        TOPIC = 'topic', 'Topic Notification'
        BULK = 'bulk', 'Bulk Notification'
    
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        PARTIAL = 'partial', 'Partially Sent'
    
    title = models.CharField(
        max_length=255,
        verbose_name="Title",
        help_text="Notification title"
    )
    body = models.TextField(
        verbose_name="Body",
        help_text="Notification body/message"
    )
    notification_type = models.CharField(
        max_length=10,
        choices=NotificationType.choices,
        default=NotificationType.PUSH,
        db_index=True,
        verbose_name="Notification Type",
        help_text="Type of notification sent"
    )
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
        verbose_name="Status",
        help_text="Current status of the notification"
    )
    target_tokens = models.JSONField(
        default=list,
        verbose_name="Target Tokens",
        help_text="List of device tokens targeted"
    )
    topic = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Topic",
        help_text="Topic name for topic notifications"
    )
    data_payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="Data Payload",
        help_text="Additional data sent with notification"
    )
    success_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Success Count",
        help_text="Number of successful deliveries"
    )
    failure_count = models.PositiveIntegerField(
        default=0,
        verbose_name="Failure Count",
        help_text="Number of failed deliveries"
    )
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name="Error Message",
        help_text="Error message if notification failed"
    )
    firebase_message_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Firebase Message ID",
        help_text="Firebase message ID for tracking"
    )
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'notification_type']),
            models.Index(fields=['topic', 'status']),
            models.Index(fields=['created_at', 'status']),
        ]
        verbose_name = 'Notification Log'
        verbose_name_plural = 'Notification Logs'
    
    def __str__(self) -> str:
        return f"{self.title} - {self.status}"
    
    def clean(self):
        """Custom validation for notification log."""
        super().clean()
        
        # Business rule: Title must be provided
        if not self.title or not self.title.strip():
            raise ValidationError({'title': 'Notification title is required.'})
        
        # Business rule: Body must be provided
        if not self.body or not self.body.strip():
            raise ValidationError({'body': 'Notification body is required.'})
        
        # Business rule: For topic notifications, topic must be provided
        if self.notification_type == self.NotificationType.TOPIC and not self.topic:
            raise ValidationError({'topic': 'Topic is required for topic notifications.'})
        
        # Business rule: For push notifications, target tokens must be provided
        if self.notification_type == self.NotificationType.PUSH and not self.target_tokens:
            raise ValidationError({'target_tokens': 'Target tokens are required for push notifications.'})


class NotificationSubscription(BaseModel):
    """
    Model to track user subscriptions to notification topics.
    """
    device_token = models.ForeignKey(
        DeviceToken,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        db_index=True,
        verbose_name="Device Token",
        help_text="Device token for this subscription"
    )
    topic = models.CharField(
        max_length=100,
        db_index=True,
        verbose_name="Topic",
        help_text="Topic name to subscribe to"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        verbose_name="Is Active",
        help_text="Whether the subscription is active"
    )
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['device_token', 'topic']
        indexes = [
            models.Index(fields=['topic', 'is_active']),
            models.Index(fields=['device_token', 'is_active']),
        ]
        verbose_name = 'Notification Subscription'
        verbose_name_plural = 'Notification Subscriptions'
    
    def __str__(self) -> str:
        return f"{self.device_token} -> {self.topic}"
    
    def clean(self):
        """Custom validation for notification subscription."""
        super().clean()
        
        # Business rule: Topic must be provided and not empty
        if not self.topic or not self.topic.strip():
            raise ValidationError({'topic': 'Topic name is required and cannot be empty.'})
        
        # Business rule: Topic should be lowercase and contain only valid characters
        import re
        if not re.match(r'^[a-z0-9_-]+$', self.topic.lower()):
            raise ValidationError({'topic': 'Topic name can only contain lowercase letters, numbers, hyphens, and underscores.'})


