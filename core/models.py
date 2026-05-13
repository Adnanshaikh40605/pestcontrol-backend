from django.db import models
import uuid
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
    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="State",
        help_text="State where the client is located"
    )
    city = models.CharField(
        max_length=255, 
        blank=True,
        null=True,
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
            models.Index(fields=['city', 'state', 'is_active']),
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
        
        # Business rule: City requirement removed to support quick reminders
        pass
        
        # Business rule: Email format validation if provided
        if self.email and self.email.strip():
            from django.core.validators import validate_email
            try:
                validate_email(self.email)
            except ValidationError:
                raise ValidationError({'email': 'Please enter a valid email address.'})


class Technician(BaseModel):
    name = models.CharField(
        max_length=255, 
        db_index=True,
        verbose_name="Name",
        help_text="Full name of the technician"
    )
    mobile = models.CharField(
        max_length=10, 
        unique=True, 
        validators=[validate_mobile_number],
        db_index=True,
        verbose_name="Mobile Number",
        help_text="10-digit primary mobile number"
    )
    age = models.IntegerField(
        blank=True, 
        null=True,
        verbose_name="Age",
        help_text="Age of the technician"
    )
    alternative_mobile = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        validators=[validate_mobile_number],
        verbose_name="Alternative Number",
        help_text="Secondary contact number"
    )
    is_active = models.BooleanField(
        default=True, 
        db_index=True,
        verbose_name="Is Active",
        help_text="Whether the technician is currently available"
    )
    service_area = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Service Area",
        help_text="Primary area where the technician operates"
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="City",
        help_text="City where the technician is based"
    )
    last_active = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name="Last Active",
        help_text="Last known timestamp of activity"
    )

    class Meta:
        ordering = ['name']
        verbose_name = 'Technician'
        verbose_name_plural = 'Technicians'

    def __str__(self) -> str:
        return f"{self.name} ({self.mobile})"


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
    state = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="State",
        help_text="State where the service is required"
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
    
    # Tracking fields
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_inquiries',
        verbose_name="Created By"
    )
    converted_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='converted_inquiries',
        verbose_name="Converted By"
    )
    
    # New fields for website quote form
    premise_type = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Premise Type",
        help_text="Categorizes the property type (e.g., residential, commercial)"
    )
    premise_size = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Premise Size",
        help_text="Specific size for residential quotes (e.g., 1bhk, 2bhk)"
    )
    pest_problems = models.TextField(
        blank=True, 
        null=True,
        verbose_name="Pest Problems",
        help_text="List of pests selected by the user"
    )
    estimated_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[validate_non_negative_decimal],
        verbose_name="Estimated Price",
        help_text="The price calculated by the website"
    )
    is_inspection_required = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Is Inspection Required",
        help_text="Flag for cases where price is not fixed"
    )
    service_frequency = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Service Frequency",
        help_text="Whether user wants a one-time treatment or AMC"
    )
    remark = models.TextField(blank=True, null=True, verbose_name="Remark")
    
    # Reminder fields
    reminder_date = models.DateField(null=True, blank=True, db_index=True, verbose_name="Reminder Date")
    reminder_time = models.TimeField(null=True, blank=True, verbose_name="Reminder Time")
    reminder_note = models.TextField(null=True, blank=True, verbose_name="Reminder Note")
    is_reminder_done = models.BooleanField(default=False, db_index=True, verbose_name="Is Reminder Done")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'city', 'state']),
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
        
        # Business rule: City requirement removed
        pass


class JobCard(BaseModel):
    class JobStatus(models.TextChoices):
        PENDING = 'Pending', 'Pending'
        ON_PROCESS = 'On Process', 'On Process'
        DONE = 'Done', 'Done'
        CANCELLED = 'Cancelled', 'Cancelled'

    class PaymentStatus(models.TextChoices):
        UNPAID = 'Unpaid', 'Unpaid'
        PAID = 'Paid', 'Paid'
    
    class PaymentMode(models.TextChoices):
        CASH = 'Cash', 'Cash'
        ONLINE = 'Online', 'Online'
    
    class JobType(models.TextChoices):
        CUSTOMER = 'Customer', 'Customer'
        SOCIETY = 'Society', 'Society'
    
    class ContractDuration(models.TextChoices):
        TWELVE_MONTHS = '12', '12 Months'
        SIX_MONTHS = '6', '6 Months'
        THREE_MONTHS = '3', '3 Months'

    class ServiceCategory(models.TextChoices):
        ONE_TIME = 'One-Time Service', 'One-Time Service'
        AMC = 'AMC', 'AMC (Annual Maintenance Contract)'

    class PropertyType(models.TextChoices):
        HOME_FLAT = 'Home / Flat', 'Home / Flat'
        BUNGALOW = 'Bungalow', 'Bungalow'
        HOTEL = 'Hotel', 'Hotel'
        OFFICE = 'Office', 'Office'
        COMMERCIAL = 'Commercial Space', 'Commercial Space'

    class BHKSize(models.TextChoices):
        RK1 = '1 RK', '1 RK'
        BHK1 = '1 BHK', '1 BHK'
        BHK2 = '2 BHK', '2 BHK'
        BHK3 = '3 BHK', '3 BHK'
        BHK4 = '4 BHK', '4 BHK'

    class CommercialType(models.TextChoices):
        HOME = 'home', 'Home'
        HOTEL = 'hotel', 'Hotel'
        SOCIETY = 'society', 'Society'
        VILLA = 'villa', 'Villa'
        OFFICE = 'office', 'Office'
        OTHER = 'other', 'Other'

    class TimeSlot(models.TextChoices):
        SLOT_8_10 = '8am–10am', '8am–10am'
        SLOT_10_12 = '10am–12pm', '10am–12pm'
        SLOT_12_2 = '12pm–2pm', '12pm–2pm'
        SLOT_2_4 = '2pm–4pm', '2pm–4pm'
        SLOT_4_6 = '4pm–6pm', '4pm–6pm'
        SLOT_6_8 = '6pm–8pm', '6pm–8pm'

    class ComplaintStatus(models.TextChoices):
        OPEN = 'Open', 'Open'
        ASSIGNED = 'Assigned', 'Assigned'
        IN_PROGRESS = 'In Progress', 'In Progress'
        RESOLVED = 'Resolved', 'Resolved'
        CLOSED = 'Closed', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'Low', 'Low'
        MEDIUM = 'Medium', 'Medium'
        HIGH = 'High', 'High'

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
        help_text="Type of job - Customer or Society (Legacy)"
    )
    commercial_type = models.CharField(
        max_length=20,
        choices=CommercialType.choices,
        default=CommercialType.HOME,
        db_index=True,
        verbose_name="Commercial Type",
        help_text="Detailed category of the booking"
    )
    is_price_estimated = models.BooleanField(
        default=False,
        db_index=True,
        verbose_name="Is Price Estimated",
        help_text="Whether the price is a dynamic estimate (for commercial types)"
    )
    service_category = models.CharField(
        max_length=50,
        choices=ServiceCategory.choices,
        default=ServiceCategory.ONE_TIME,
        db_index=True,
        verbose_name="Service Category",
        help_text="One-Time Service or AMC"
    )
    property_type = models.CharField(
        max_length=50,
        choices=PropertyType.choices,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Property Type"
    )
    bhk_size = models.CharField(
        max_length=20,
        choices=BHKSize.choices,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="BHK Size"
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
        default=JobStatus.PENDING,
        db_index=True,
        verbose_name="Status",
        help_text="Current status of the job card"
    )
    service_type = models.CharField(
        max_length=500, 
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Service Type",
        help_text="Type of pest control service to be provided"
    )
    schedule_datetime = models.DateTimeField(
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Schedule DateTime",
        help_text="Date and time when the service is scheduled"
    )
    time_slot = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Time Slot"
    )
    state = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name="State")
    city = models.CharField(max_length=100, blank=True, null=True, db_index=True, verbose_name="City")
    
    client_address = models.TextField(
        blank=True,
        null=True,
        verbose_name="Client Address",
        help_text="Address where the service will be performed"
    )
    price = models.CharField(
        max_length=200,
        default='',
        blank=True,
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
    payment_mode = models.CharField(
        max_length=20,
        choices=PaymentMode.choices,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Payment Mode"
    )
    assigned_to = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        db_index=True,
        verbose_name="Assigned Technician (Legacy)",
        help_text="Technician name string (legacy support)"
    )
    technician = models.ForeignKey(
        Technician,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='jobcards',
        db_index=True,
        verbose_name="Assigned Technician",
        help_text="Registered technician assigned to this job"
    )
    next_service_date = models.DateField(
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Next Service Date",
        help_text="Date for the next scheduled service (optional)"
    )
    service_cycle = models.IntegerField(
        default=1,
        verbose_name="Service Cycle",
        help_text="Current service number in the sequence"
    )
    max_cycle = models.IntegerField(
        default=1,
        verbose_name="Max Cycle",
        help_text="Total number of services in the contract"
    )
    parent_job = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='follow_up_jobs',
        verbose_name="Parent Job",
        help_text="The previous job in the service sequence"
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
        max_length=200,
        default='Other',
        db_index=True,
        verbose_name="Reference",
        help_text="Source of reference for this job card"
    )
    extra_notes = models.TextField(
        blank=True,
        null=True,
        verbose_name="Extra Notes",
        help_text="Additional notes or comments about the job card"
    )
    cancellation_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name="Cancellation Reason",
        help_text="Reason why the booking was cancelled"
    )
    removal_remarks = models.TextField(
        blank=True,
        null=True,
        verbose_name="Removal Remarks",
        help_text="Remarks when a technician is removed from an On Process job"
    )
    
    # Reminder fields
    reminder_date = models.DateField(null=True, blank=True, db_index=True, verbose_name="Reminder Date")
    reminder_time = models.TimeField(null=True, blank=True, verbose_name="Reminder Time")
    reminder_note = models.TextField(null=True, blank=True, verbose_name="Reminder Note")
    is_reminder_done = models.BooleanField(default=False, db_index=True, verbose_name="Is Reminder Done")

    # Partner App Workflow Fields
    is_read = models.BooleanField(default=False, verbose_name="Is Read")
    is_accepted = models.BooleanField(default=False, verbose_name="Is Accepted")
    is_service_call = models.BooleanField(default=False, verbose_name="Is Service Call")
    accepted_at = models.DateTimeField(null=True, blank=True, verbose_name="Accepted At")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="Started At")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")

    # Complaint Call Fields
    is_complaint_call = models.BooleanField(default=False, db_index=True)
    complaint_parent_booking = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='complaints',
        verbose_name="Parent Booking for Complaint"
    )
    complaint_status = models.CharField(
        max_length=50,
        choices=ComplaintStatus.choices,
        default=ComplaintStatus.OPEN,
        db_index=True
    )
    complaint_type = models.CharField(max_length=100, blank=True, null=True)
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True
    )
    complaint_note = models.TextField(blank=True, null=True)

    # Tracking fields
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_bookings',
        verbose_name="Created By"
    )
    on_process_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='on_process_bookings',
        verbose_name="On Process By"
    )
    done_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='done_bookings',
        verbose_name="Done By"
    )

    # AMC and Revenue Flow Fields
    is_amc_main_booking = models.BooleanField(
        default=False, 
        db_index=True, 
        verbose_name="Is AMC Main Booking",
        help_text="True if this is the first/paid booking of an AMC package"
    )
    is_followup_visit = models.BooleanField(
        default=False, 
        db_index=True, 
        verbose_name="Is Follow-up Visit",
        help_text="True if this is a follow-up service (AMC or BedBug)"
    )
    included_in_amc = models.BooleanField(
        default=False, 
        db_index=True, 
        verbose_name="Included in AMC",
        help_text="True if this service is free/included in a previously paid AMC"
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'payment_status']),
            models.Index(fields=['schedule_datetime', 'status']),
            models.Index(fields=['client', 'status']),
            models.Index(fields=['job_type', 'status']),
            models.Index(fields=['commercial_type', 'status']),
            models.Index(fields=['contract_duration', 'commercial_type']),
        ]
        verbose_name = 'Job Card'
        verbose_name_plural = 'Job Cards'

    def __str__(self) -> str:
        return self.code or str(self.pk)

    def clean(self):
        """Custom validation for the model with comprehensive business rules."""
        super().clean()
        
        # Business rule: Service type requirement removed
        pass
        
        # Business rule: Schedule date validation (allow past dates with warning)
        if self.schedule_datetime and self.schedule_datetime.date() < timezone.now().date() and not self.pk:
            # Allow past dates but log a warning for audit purposes
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Job card created with past schedule date: {self.schedule_datetime} (today: {timezone.now().date()})")
            # Note: We allow past dates for cases like recording completed services, backdating, etc.
        
        # Business rule: Price requirement removed
        pass
        
        # Business rule: Contract duration validation for Society jobs
        if self.job_type == self.JobType.SOCIETY and not self.contract_duration:
            raise ValidationError({'contract_duration': 'Contract duration is required for Society jobs.'})
        
        # Business rule: Next service date validation
        if self.next_service_date and self.schedule_datetime and self.next_service_date <= self.schedule_datetime.date():
            raise ValidationError({'next_service_date': 'Next service date must be after schedule date.'})

        # Business rule: Cancellation reason validation
        if self.status == self.JobStatus.CANCELLED:
            if not self.cancellation_reason or not self.cancellation_reason.strip():
                raise ValidationError({'cancellation_reason': 'Cancellation reason is required when status is Cancelled.'})
            
            # Min 4 characters
            if len(self.cancellation_reason.strip()) < 4:
                raise ValidationError({'cancellation_reason': 'Reason must be at least 4 characters.'})
            
            # No special characters (alphabets, numbers, spaces only)
            import re
            if not re.match(r'^[a-zA-Z0-9\s]*$', self.cancellation_reason):
                raise ValidationError({'cancellation_reason': 'Special characters are not allowed in the cancellation reason.'})

    def save(self, *args, **kwargs):
        creating = self.pk is None
        
        # Auto-set is_service_call if it's a follow-up cycle
        if self.service_cycle > 1:
            self.is_service_call = True
            
        super().save(*args, **kwargs)

        # Generate code after initial save when PK is available
        if creating and not self.code:
            self.code = str(self.pk)
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
    due_date = models.DateField(
        db_index=True,
        verbose_name="Due Date",
        help_text="Date when the renewal is due"
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
    
    # Tracking field
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='created_renewals',
        verbose_name="Created By"
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
        return f"Renewal for {self.jobcard.code if self.jobcard_id else self.jobcard_id} on {self.due_date}"
    
    def update_urgency_level(self):
        """Update urgency level based on due date."""
        from datetime import timedelta
        now = timezone.now().date()  # Convert to date for comparison
        
        if self.due_date <= now:
            self.urgency_level = self.UrgencyLevel.HIGH
        elif self.due_date <= now + timedelta(days=3):
            self.urgency_level = self.UrgencyLevel.MEDIUM
        else:
            self.urgency_level = self.UrgencyLevel.NORMAL
    
    def clean(self):
        """Custom validation for the model with comprehensive business rules."""
        super().clean()
        
        # Business rule: Prevent duplicate renewals for the same job card and due date
        if self.jobcard_id and self.due_date:
            existing = Renewal.objects.filter(
                jobcard=self.jobcard,
                due_date=self.due_date,
                renewal_type=self.renewal_type
            ).exclude(pk=self.pk if self.pk else None)
            
            if existing.exists():
                raise ValidationError({
                    'due_date': f'A renewal of type {self.renewal_type} already exists for this job card on {self.due_date}.'
                })
        
        # Business rule: Due date must be in the future for new renewals
        if self.pk is None and self.due_date:
            if self.due_date < timezone.now().date():
                # Allow past dates but log a warning
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"Renewal created with past due date: {self.due_date} (today: {timezone.now().date()})")
    
    def save(self, *args, **kwargs):
        """Override save to automatically update urgency level and trigger related updates."""
        self.update_urgency_level()
        super().save(*args, **kwargs)
        
        # Trigger urgency level updates for related renewals if this is a jobcard update
        if hasattr(self, 'jobcard') and self.jobcard:
            # Update all related renewals for this jobcard
            from .services import RenewalService
            RenewalService.update_urgency_levels_for_jobcard(self.jobcard.id)


class CRMInquiry(BaseModel):
    class InquiryStatus(models.TextChoices):
        NEW = 'New', 'New'
        CONTACTED = 'Contacted', 'Contacted'
        CONVERTED = 'Converted', 'Converted'
        CLOSED = 'Closed', 'Closed'
    
    class PestType(models.TextChoices):
        COCKROACH = 'Cockroach', 'Cockroach'
        ANTS = 'Ants', 'Ants'
        BED_BUGS = 'Bed Bugs', 'Bed Bugs'
        TERMITE = 'Termite', 'Termite'
        RODENT = 'Rodent', 'Rodent'
        MOSQUITO = 'Mosquito', 'Mosquito'
        OTHER = 'Other', 'Other'

    name = models.CharField(max_length=255, db_index=True)
    mobile = models.CharField(max_length=10, validators=[validate_mobile_number], db_index=True)
    location = models.CharField(max_length=500, blank=True, null=True)
    pest_type = models.CharField(max_length=255, default='Other')
    remark = models.TextField(blank=True, null=True, verbose_name="Remark")
    service_frequency = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        db_index=True,
        verbose_name="Service Frequency"
    )
    
    # Reminder fields
    reminder_date = models.DateField(null=True, blank=True, db_index=True, verbose_name="Reminder Date")
    reminder_time = models.TimeField(null=True, blank=True, verbose_name="Reminder Time")
    reminder_note = models.TextField(null=True, blank=True, verbose_name="Reminder Note")
    is_reminder_done = models.BooleanField(default=False, db_index=True, verbose_name="Is Reminder Done")
    inquiry_date = models.DateField(default=timezone.now)
    inquiry_time = models.TimeField(default=timezone.now)
    status = models.CharField(max_length=20, choices=InquiryStatus.choices, default=InquiryStatus.NEW)
    
    # Store user who created it
    created_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='crm_inquiries'
    )
    converted_by = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='converted_crm_inquiries',
        verbose_name="Converted By"
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'CRM Inquiry'
        verbose_name_plural = 'CRM Inquiries'

    def __str__(self) -> str:
        return f"{self.name} - {self.mobile}"


class Reminder(BaseModel):
    class InquiryType(models.TextChoices):
        CRM = 'crm', 'CRM Inquiry'
        WEBSITE = 'website', 'Website Inquiry'

    class ReminderStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        COMPLETED = 'completed', 'Completed'

    inquiry_type = models.CharField(
        max_length=20,
        choices=InquiryType.choices,
        db_index=True,
        verbose_name="Inquiry Type"
    )
    inquiry_id = models.IntegerField(db_index=True, verbose_name="Inquiry ID")
    customer_name = models.CharField(max_length=255, verbose_name="Customer Name")
    mobile_number = models.CharField(max_length=10, validators=[validate_mobile_number], verbose_name="Mobile Number")
    reminder_date = models.DateField(db_index=True, verbose_name="Reminder Date")
    reminder_time = models.TimeField(null=True, blank=True, verbose_name="Reminder Time")
    note = models.TextField(verbose_name="Note")
    created_by = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_reminders',
        verbose_name="Created By"
    )
    status = models.CharField(
        max_length=20,
        choices=ReminderStatus.choices,
        default=ReminderStatus.PENDING,
        db_index=True,
        verbose_name="Status"
    )

    class Meta:
        ordering = ['reminder_date', 'reminder_time']
        verbose_name = 'Reminder'
        verbose_name_plural = 'Reminders'

    def __str__(self) -> str:
        return f"Reminder for {self.customer_name} on {self.reminder_date}"


class Feedback(BaseModel):
    booking = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='feedbacks')
    rating = models.IntegerField()
    remark = models.TextField(blank=True, null=True)
    technician_behavior = models.CharField(
        max_length=50,
        choices=[
            ('excellent', 'Excellent'),
            ('good', 'Good'),
            ('average', 'Average'),
            ('poor', 'Poor'),
        ]
    )
    feedback_type = models.CharField(max_length=20)  # 'Manual' or 'WhatsApp Link'
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_read = models.BooleanField(default=False, db_index=True, verbose_name="Is Read")

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Feedback'
        verbose_name_plural = 'Feedbacks'

    def __str__(self) -> str:
        return f"Feedback for Booking {self.booking.code} - Rating: {self.rating}"


class ActivityLog(BaseModel):
    user = models.ForeignKey(
        'auth.User', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='activity_logs'
    )
    action = models.CharField(max_length=255)
    booking_id = models.CharField(max_length=100, blank=True, null=True)
    details = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Activity Log'
        verbose_name_plural = 'Activity Logs'

    def __str__(self) -> str:
        staff_name = f"{self.user.first_name} {self.user.last_name}" if self.user else "System"
        return f"{staff_name} - {self.action} - {self.created_at.strftime('%d-%m-%Y %H:%M')}"
