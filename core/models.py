from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from .validators import (
    validate_mobile_number, 
    validate_positive_decimal, 
    validate_tax_percent,
    validate_job_code
)


class BaseModel(models.Model):
    """
    Abstract base model with timestamp fields and common functionality.
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True
        ordering = ['-created_at']


class Client(BaseModel):
    full_name = models.CharField(max_length=255, db_index=True)
    mobile = models.CharField(
        max_length=10, 
        unique=True, 
        validators=[validate_mobile_number],
        db_index=True
    )
    email = models.EmailField(blank=True, null=True, db_index=True)
    city = models.CharField(max_length=100, db_index=True)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)

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
        """Custom validation for the model."""
        super().clean()
        if self.mobile:
            validate_mobile_number(self.mobile)


class Inquiry(BaseModel):
    class InquiryStatus(models.TextChoices):
        NEW = 'New', 'New'
        CONTACTED = 'Contacted', 'Contacted'
        CONVERTED = 'Converted', 'Converted'
        CLOSED = 'Closed', 'Closed'

    name = models.CharField(max_length=255, db_index=True)
    mobile = models.CharField(
        max_length=10, 
        validators=[validate_mobile_number],
        db_index=True
    )
    email = models.EmailField(blank=True, null=True, db_index=True)
    message = models.TextField()
    service_interest = models.CharField(max_length=255, db_index=True)
    city = models.CharField(max_length=100, db_index=True)
    status = models.CharField(
        max_length=20,
        choices=InquiryStatus.choices,
        default=InquiryStatus.NEW,
        db_index=True
    )
    is_read = models.BooleanField(default=False, db_index=True)

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
        """Custom validation for the model."""
        super().clean()
        if self.mobile:
            validate_mobile_number(self.mobile)


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

    code = models.CharField(
        max_length=20, 
        unique=True, 
        blank=True,
        validators=[validate_job_code],
        db_index=True
    )
    client = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        related_name='jobcards',
        db_index=True
    )
    status = models.CharField(
        max_length=20, 
        choices=JobStatus.choices, 
        default=JobStatus.ENQUIRY,
        db_index=True
    )
    service_type = models.CharField(max_length=255, db_index=True)
    schedule_date = models.DateField(db_index=True)
    technician_name = models.CharField(max_length=255, db_index=True)
    price_subtotal = models.DecimalField(
        max_digits=15, 
        decimal_places=2,
        validators=[validate_positive_decimal]
    )
    tax_percent = models.PositiveIntegerField(
        default=18,
        validators=[validate_tax_percent]
    )
    grand_total = models.DecimalField(
        max_digits=15, 
        decimal_places=2, 
        default=0,
        validators=[validate_positive_decimal]
    )
    payment_status = models.CharField(
        max_length=20, 
        choices=PaymentStatus.choices, 
        default=PaymentStatus.UNPAID,
        db_index=True
    )
    next_service_date = models.DateField(blank=True, null=True, db_index=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'payment_status']),
            models.Index(fields=['schedule_date', 'status']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['technician_name', 'schedule_date']),
        ]
        verbose_name = 'Job Card'
        verbose_name_plural = 'Job Cards'

    def __str__(self) -> str:
        return self.code or f"JobCard {self.pk}"

    def clean(self):
        """Custom validation for the model."""
        super().clean()
        if self.price_subtotal is not None:
            validate_positive_decimal(self.price_subtotal)
        if self.tax_percent is not None:
            validate_tax_percent(self.tax_percent)

    def save(self, *args, **kwargs):
        # Calculate grand total
        if self.price_subtotal is not None and self.tax_percent is not None:
            # grand_total = subtotal + (subtotal * tax_percent / 100)
            self.grand_total = self.price_subtotal + (
                self.price_subtotal * self.tax_percent / 100
            )

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

    jobcard = models.ForeignKey(
        JobCard, 
        on_delete=models.CASCADE, 
        related_name='renewals',
        db_index=True
    )
    due_date = models.DateTimeField(default=timezone.now, db_index=True)
    status = models.CharField(
        max_length=20, 
        choices=RenewalStatus.choices, 
        default=RenewalStatus.DUE,
        db_index=True
    )
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['jobcard', 'status']),
        ]
        verbose_name = 'Renewal'
        verbose_name_plural = 'Renewals'

    def __str__(self) -> str:
        return f"Renewal for {self.jobcard.code if self.jobcard_id else self.jobcard_id} on {self.due_date.date()}"


