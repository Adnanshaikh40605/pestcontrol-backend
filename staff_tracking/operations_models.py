"""FieldPulse-style operations models — visits, tasks, leave, expenses, geo-attendance."""

from decimal import Decimal

from django.conf import settings
from django.db import models

from core.models import BaseModel, JobCard


# ---------------------------------------------------------------------------
# Geo-Attendance extensions
# ---------------------------------------------------------------------------


class Shift(BaseModel):
    """Configurable shift for attendance rules."""

    name = models.CharField(max_length=80)
    start_time = models.TimeField()
    end_time = models.TimeField()
    grace_minutes = models.PositiveIntegerField(default=15)
    is_default = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Shift'
        verbose_name_plural = 'Shifts'
        ordering = ['start_time']

    def __str__(self):
        return self.name


class AttendanceBreak(BaseModel):
    """Break period during an attendance session."""

    session = models.ForeignKey(
        'AttendanceSession',
        on_delete=models.CASCADE,
        related_name='breaks',
    )
    started_at = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)

    class Meta:
        verbose_name = 'Attendance Break'
        verbose_name_plural = 'Attendance Breaks'
        ordering = ['-started_at']

    @property
    def is_active(self) -> bool:
        return self.ended_at is None


class GeofenceZone(BaseModel):
    """Office or site geo-fence (center + radius)."""

    class ZoneType(models.TextChoices):
        OFFICE = 'office', 'Office'
        CLIENT = 'client', 'Client Site'
        CUSTOM = 'custom', 'Custom'

    name = models.CharField(max_length=120)
    zone_type = models.CharField(max_length=20, choices=ZoneType.choices, default=ZoneType.OFFICE)
    latitude = models.DecimalField(max_digits=10, decimal_places=7)
    longitude = models.DecimalField(max_digits=10, decimal_places=7)
    radius_m = models.PositiveIntegerField(default=200)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Geofence Zone'
        verbose_name_plural = 'Geofence Zones'

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# Visit Management
# ---------------------------------------------------------------------------


class FieldVisit(BaseModel):
    """Client/site visit — linked to JobCard when scheduled from CRM bookings."""

    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        IN_PROGRESS = 'in_progress', 'In Progress'
        COMPLETED = 'completed', 'Completed'
        MISSED = 'missed', 'Missed'
        CANCELLED = 'cancelled', 'Cancelled'

    profile = models.ForeignKey(
        'TrackingProfile',
        on_delete=models.CASCADE,
        related_name='field_visits',
    )
    jobcard = models.ForeignKey(
        JobCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='field_visits',
    )
    title = models.CharField(max_length=200)
    client_name = models.CharField(max_length=200, blank=True)
    address = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    scheduled_at = models.DateTimeField(db_index=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True,
    )
    check_in_at = models.DateTimeField(null=True, blank=True)
    check_in_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_in_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_in_accuracy_m = models.FloatField(null=True, blank=True)
    check_out_at = models.DateTimeField(null=True, blank=True)
    check_out_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    check_out_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    notes = models.TextField(blank=True)
    missed_reason = models.CharField(max_length=255, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_field_visits',
    )

    class Meta:
        verbose_name = 'Field Visit'
        verbose_name_plural = 'Field Visits'
        ordering = ['-scheduled_at']
        indexes = [
            models.Index(fields=['profile', 'scheduled_at']),
            models.Index(fields=['status', 'scheduled_at']),
        ]

    def __str__(self):
        return f'{self.title} — {self.profile.display_name}'


class VisitPhoto(BaseModel):
    """Photo captured at visit check-in or check-out."""

    class PhotoType(models.TextChoices):
        CHECK_IN = 'check_in', 'Check-in'
        CHECK_OUT = 'check_out', 'Check-out'
        SITE = 'site', 'Site'

    visit = models.ForeignKey(FieldVisit, on_delete=models.CASCADE, related_name='photos')
    photo_type = models.CharField(max_length=20, choices=PhotoType.choices, default=PhotoType.SITE)
    image = models.ImageField(upload_to='staff_tracking/visit_photos/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Visit Photo'
        verbose_name_plural = 'Visit Photos'


# ---------------------------------------------------------------------------
# Task Management
# ---------------------------------------------------------------------------


class StaffTask(BaseModel):
    """Task assigned to field staff by CRM manager."""

    class Priority(models.TextChoices):
        CRITICAL = 'critical', 'Critical'
        HIGH = 'high', 'High'
        MEDIUM = 'medium', 'Medium'
        LOW = 'low', 'Low'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        IN_PROGRESS = 'in_progress', 'In Progress'
        NEEDS_CLARIFICATION = 'needs_clarification', 'Needs Clarification'
        COMPLETED = 'completed', 'Completed'
        VERIFIED = 'verified', 'Verified'
        OVERDUE = 'overdue', 'Overdue'
        CANCELLED = 'cancelled', 'Cancelled'

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    assigned_to = models.ForeignKey(
        'TrackingProfile',
        on_delete=models.CASCADE,
        related_name='tasks',
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_staff_tasks',
    )
    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
        db_index=True,
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    due_at = models.DateTimeField(null=True, blank=True, db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    jobcard = models.ForeignKey(
        JobCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='staff_tasks',
    )
    field_visit = models.ForeignKey(
        FieldVisit,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tasks',
    )
    completion_latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    completion_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    requires_gps_proof = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Staff Task'
        verbose_name_plural = 'Staff Tasks'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_at', 'status']),
        ]

    def __str__(self):
        return self.title


class TaskComment(BaseModel):
    task = models.ForeignKey(
        StaffTask,
        on_delete=models.CASCADE,
        related_name='comments',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    profile = models.ForeignKey(
        'TrackingProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Set when comment is from mobile staff app',
    )
    body = models.TextField()

    class Meta:
        verbose_name = 'Task Comment'
        verbose_name_plural = 'Task Comments'
        ordering = ['created_at']


# ---------------------------------------------------------------------------
# Leave Management
# ---------------------------------------------------------------------------


class LeaveType(BaseModel):
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=20, unique=True)
    default_days_per_year = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    requires_document = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Leave Type'
        verbose_name_plural = 'Leave Types'
        ordering = ['name']

    def __str__(self):
        return self.name


class LeaveBalance(BaseModel):
    profile = models.ForeignKey('TrackingProfile', on_delete=models.CASCADE, related_name='leave_balances')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE, related_name='balances')
    year = models.PositiveIntegerField(db_index=True)
    allocated = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    used = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    pending = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))
    carry_forward = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal('0'))

    class Meta:
        verbose_name = 'Leave Balance'
        verbose_name_plural = 'Leave Balances'
        constraints = [
            models.UniqueConstraint(
                fields=['profile', 'leave_type', 'year'],
                name='unique_leave_balance_per_year',
            ),
        ]

    @property
    def available(self) -> Decimal:
        return self.allocated + self.carry_forward - self.used - self.pending


class LeaveApplication(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        CANCELLED = 'cancelled', 'Cancelled'

    class HalfDay(models.TextChoices):
        FULL = 'full', 'Full Day'
        FIRST_HALF = 'first_half', 'First Half'
        SECOND_HALF = 'second_half', 'Second Half'

    profile = models.ForeignKey('TrackingProfile', on_delete=models.CASCADE, related_name='leave_applications')
    leave_type = models.ForeignKey(LeaveType, on_delete=models.PROTECT, related_name='applications')
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)
    half_day = models.CharField(max_length=20, choices=HalfDay.choices, default=HalfDay.FULL)
    reason = models.TextField()
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    days_count = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal('1'))
    document = models.FileField(upload_to='staff_tracking/leave_docs/%Y/%m/', blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_leave_applications',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_comment = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Leave Application'
        verbose_name_plural = 'Leave Applications'
        ordering = ['-created_at']


class OrgHoliday(BaseModel):
    date = models.DateField(unique=True, db_index=True)
    name = models.CharField(max_length=120)

    class Meta:
        verbose_name = 'Organisation Holiday'
        verbose_name_plural = 'Organisation Holidays'
        ordering = ['date']

    def __str__(self):
        return f'{self.name} ({self.date})'


# ---------------------------------------------------------------------------
# Expense Management
# ---------------------------------------------------------------------------


class ExpenseCategory(BaseModel):
    name = models.CharField(max_length=80, unique=True)
    code = models.CharField(max_length=20, unique=True)
    requires_receipt_above = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('500'),
    )
    km_rate = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True,
        help_text='Auto travel rate per km (INR) when category is travel',
    )
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = 'Expense Category'
        verbose_name_plural = 'Expense Categories'

    def __str__(self):
        return self.name


class ExpenseClaim(BaseModel):
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        PENDING = 'pending', 'Pending'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        PAID = 'paid', 'Paid'

    profile = models.ForeignKey('TrackingProfile', on_delete=models.CASCADE, related_name='expense_claims')
    category = models.ForeignKey(ExpenseCategory, on_delete=models.PROTECT, related_name='claims')
    expense_date = models.DateField(db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0'))
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    distance_km = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    jobcard = models.ForeignKey(JobCard, on_delete=models.SET_NULL, null=True, blank=True, related_name='expense_claims')
    field_visit = models.ForeignKey(FieldVisit, on_delete=models.SET_NULL, null=True, blank=True, related_name='expense_claims')
    attendance_session = models.ForeignKey(
        'AttendanceSession',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expense_claims',
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_expense_claims',
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewer_comment = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Expense Claim'
        verbose_name_plural = 'Expense Claims'
        ordering = ['-expense_date', '-created_at']


class ExpenseReceipt(BaseModel):
    claim = models.ForeignKey(ExpenseClaim, on_delete=models.CASCADE, related_name='receipts')
    image = models.ImageField(upload_to='staff_tracking/expense_receipts/%Y/%m/')
    caption = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = 'Expense Receipt'
        verbose_name_plural = 'Expense Receipts'
