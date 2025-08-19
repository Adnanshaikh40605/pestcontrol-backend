from django.db import models
from django.utils import timezone


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Client(TimestampedModel):
    full_name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=10)
    email = models.EmailField(blank=True, null=True)
    city = models.CharField(max_length=100)
    address = models.TextField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.full_name} ({self.mobile})"


class Inquiry(TimestampedModel):
    class InquiryStatus(models.TextChoices):
        NEW = 'New', 'New'
        CONTACTED = 'Contacted', 'Contacted'
        CONVERTED = 'Converted', 'Converted'
        CLOSED = 'Closed', 'Closed'

    name = models.CharField(max_length=255)
    mobile = models.CharField(max_length=10)
    email = models.EmailField(blank=True, null=True)
    message = models.TextField()
    service_interest = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    status = models.CharField(
        max_length=20,
        choices=InquiryStatus.choices,
        default=InquiryStatus.NEW,
    )

    def __str__(self) -> str:
        return f"Inquiry: {self.name} ({self.mobile})"


class JobCard(TimestampedModel):
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

    code = models.CharField(max_length=20, unique=True, blank=True)
    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name='jobcards')
    status = models.CharField(max_length=20, choices=JobStatus.choices, default=JobStatus.ENQUIRY)
    service_type = models.CharField(max_length=255)
    schedule_date = models.DateField()
    technician_name = models.CharField(max_length=255)
    price_subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_percent = models.PositiveIntegerField(default=18)
    grand_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.UNPAID)
    next_service_date = models.DateField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return self.code or f"JobCard {self.pk}"

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


class Renewal(TimestampedModel):
    class RenewalStatus(models.TextChoices):
        DUE = 'Due', 'Due'
        COMPLETED = 'Completed', 'Completed'

    jobcard = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='renewals')
    due_date = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=RenewalStatus.choices, default=RenewalStatus.DUE)
    remarks = models.TextField(blank=True, null=True)

    def __str__(self) -> str:
        return f"Renewal for {self.jobcard.code if self.jobcard_id else self.jobcard_id} on {self.due_date.date()}"


