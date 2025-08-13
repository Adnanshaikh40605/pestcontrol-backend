from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.exceptions import ValidationError


class Client(models.Model):
    """
    Client model representing customers of the pest control service.
    
    Stores client information including contact details and service history.
    """
    full_name = models.CharField(
        max_length=100,
        help_text="Full name of the client"
    )
    mobile = models.CharField(
        max_length=10,
        unique=True,
        validators=[
            RegexValidator(
                r'^\d{10}$', 
                'Enter a valid 10-digit mobile number.'
            )
        ],
        help_text="10-digit mobile number"
    )
    email = models.EmailField(
        blank=True, 
        null=True,
        help_text="Email address (optional)"
    )
    city = models.CharField(
        max_length=50,
        help_text="City where the client is located"
    )
    address = models.TextField(
        blank=True, 
        null=True,
        help_text="Detailed address (optional)"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        help_text="Additional notes about the client"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the client is currently active"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['mobile']),
            models.Index(fields=['city']),
            models.Index(fields=['is_active']),
        ]
    
    def __str__(self):
        return f"{self.full_name} ({self.mobile})"
    
    def clean(self):
        """Custom validation for the model."""
        if self.email and Client.objects.filter(email=self.email).exclude(id=self.id).exists():
            raise ValidationError('A client with this email already exists.')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class Inquiry(models.Model):
    """
    Inquiry model representing potential customer inquiries.
    
    Tracks inquiries from website or other sources before conversion to job cards.
    """
    STATUS_CHOICES = [
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Converted', 'Converted'),
        ('Closed', 'Closed'),
    ]
    
    name = models.CharField(
        max_length=100,
        help_text="Name of the person making the inquiry"
    )
    mobile = models.CharField(
        max_length=10,
        validators=[
            RegexValidator(
                r'^\d{10}$', 
                'Enter a valid 10-digit mobile number.'
            )
        ],
        help_text="10-digit mobile number"
    )
    email = models.EmailField(
        blank=True, 
        null=True,
        help_text="Email address (optional)"
    )
    message = models.TextField(
        help_text="Inquiry message or description"
    )
    service_interest = models.CharField(
        max_length=100,
        help_text="Type of service the customer is interested in"
    )
    city = models.CharField(
        max_length=50,
        help_text="City where the service is needed"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='New',
        help_text="Current status of the inquiry"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Inquiries"
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['city']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.service_interest} ({self.status})"
    
    def clean(self):
        """Custom validation for the model."""
        if self.email and Inquiry.objects.filter(email=self.email).exclude(id=self.id).exists():
            raise ValidationError('An inquiry with this email already exists.')


class JobCard(models.Model):
    """
    JobCard model representing pest control service jobs.
    
    Tracks individual service jobs including scheduling, pricing, and status.
    """
    STATUS_CHOICES = [
        ('Enquiry', 'Enquiry'),
        ('WIP', 'Work in Progress'),
        ('Done', 'Completed'),
        ('Hold', 'On Hold'),
        ('Cancel', 'Cancelled'),
        ('Inactive', 'Inactive'),
    ]
    
    PAYMENT_STATUS_CHOICES = [
        ('Unpaid', 'Unpaid'),
        ('Paid', 'Paid'),
    ]
    
    code = models.CharField(
        max_length=10, 
        unique=True, 
        editable=False,
        help_text="Auto-generated job card code"
    )
    client = models.ForeignKey(
        Client, 
        on_delete=models.CASCADE, 
        related_name='job_cards',
        help_text="Client for this job"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='Enquiry',
        help_text="Current status of the job"
    )
    service_type = models.CharField(
        max_length=100,
        help_text="Type of pest control service"
    )
    schedule_date = models.DateField(
        help_text="Scheduled date for the service"
    )
    technician_name = models.CharField(
        max_length=100,
        help_text="Name of the technician assigned"
    )
    price_subtotal = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Service price before tax"
    )
    tax_percent = models.IntegerField(
        default=18,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Tax percentage applied"
    )
    grand_total = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        editable=False,
        help_text="Total price including tax"
    )
    payment_status = models.CharField(
        max_length=10, 
        choices=PAYMENT_STATUS_CHOICES, 
        default='Unpaid',
        help_text="Payment status of the job"
    )
    next_service_date = models.DateField(
        blank=True, 
        null=True,
        help_text="Date for next scheduled service (optional)"
    )
    notes = models.TextField(
        blank=True, 
        null=True,
        help_text="Additional notes about the job"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['schedule_date']),
            models.Index(fields=['client']),
            models.Index(fields=['payment_status']),
        ]
    
    def save(self, *args, **kwargs):
        """Override save method to auto-generate code and calculate totals."""
        # Generate job card code if it's a new record
        if not self.code:
            last_job = JobCard.objects.order_by('-id').first()
            if last_job:
                last_id = last_job.id
            else:
                last_id = 0
            self.code = f'JC-{str(last_id + 1).zfill(4)}'
            
        # Calculate grand total
        tax_amount = (self.price_subtotal * self.tax_percent) / 100
        self.grand_total = self.price_subtotal + tax_amount
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.code} - {self.client.full_name} ({self.status})"
    
    def clean(self):
        """Custom validation for the model."""
        # Removed past date validation to support historical data
        
        if self.next_service_date and self.next_service_date <= self.schedule_date:
            raise ValidationError('Next service date must be after the current schedule date.')


class Renewal(models.Model):
    """
    Renewal model representing service renewals.
    
    Tracks when services need to be renewed and their status.
    """
    STATUS_CHOICES = [
        ('Due', 'Due'),
        ('Completed', 'Completed'),
    ]
    
    jobcard = models.ForeignKey(
        JobCard, 
        on_delete=models.CASCADE, 
        related_name='renewals',
        help_text="Associated job card"
    )
    due_date = models.DateField(
        help_text="Date when renewal is due"
    )
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='Due',
        help_text="Current status of the renewal"
    )
    remarks = models.TextField(
        blank=True, 
        null=True,
        help_text="Additional remarks about the renewal"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['due_date']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['due_date']),
            models.Index(fields=['jobcard']),
        ]
    
    def __str__(self):
        return f"Renewal for {self.jobcard.code} - {self.status}"
    
    def clean(self):
        """Custom validation for the model."""
        # Removed past date validation to support historical data
        pass
