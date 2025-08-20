"""
Business logic services for the pest control application.
"""
from typing import Optional, Dict, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Client, Inquiry, JobCard, Renewal


class ClientService:
    """Service class for Client-related business logic."""
    
    @staticmethod
    def create_client(data: Dict[str, Any]) -> Client:
        """Create a new client with validation."""
        client = Client(**data)
        client.full_clean()  # Run model validation
        client.save()
        return client
    
    @staticmethod
    def get_or_create_client(name: str, mobile: str, email: str = None, city: str = None) -> tuple[Client, bool]:
        """Get existing client or create new one."""
        try:
            client = Client.objects.get(mobile=mobile)
            return client, False
        except Client.DoesNotExist:
            client_data = {
                'full_name': name,
                'mobile': mobile,
                'email': email,
                'city': city or 'Unknown'
            }
            client = ClientService.create_client(client_data)
            return client, True
    
    @staticmethod
    def deactivate_client(client_id: int) -> bool:
        """Soft delete a client by setting is_active to False."""
        try:
            client = Client.objects.get(id=client_id)
            client.is_active = False
            client.save()
            return True
        except Client.DoesNotExist:
            return False


class InquiryService:
    """Service class for Inquiry-related business logic."""
    
    @staticmethod
    def create_inquiry(data: Dict[str, Any]) -> Inquiry:
        """Create a new inquiry with validation."""
        inquiry = Inquiry(**data)
        inquiry.full_clean()  # Run model validation
        inquiry.save()
        return inquiry
    
    @staticmethod
    @transaction.atomic
    def convert_to_jobcard(inquiry_id: int, conversion_data: Dict[str, Any]) -> JobCard:
        """Convert an inquiry to a job card."""
        try:
            inquiry = Inquiry.objects.get(id=inquiry_id)
            
            # Get or create client
            client, created = ClientService.get_or_create_client(
                name=inquiry.name,
                mobile=inquiry.mobile,
                email=inquiry.email,
                city=inquiry.city
            )
            
            # Create job card
            jobcard_data = {
                'client': client,
                'status': JobCard.JobStatus.ENQUIRY,
                'service_type': inquiry.service_interest,
                'schedule_date': conversion_data.get('schedule_date', timezone.now().date()),
                'technician_name': conversion_data.get('technician_name', ''),
                'price_subtotal': conversion_data.get('price_subtotal', 0),
                'tax_percent': conversion_data.get('tax_percent', 18),
                'payment_status': JobCard.PaymentStatus.UNPAID,
            }
            
            jobcard = JobCard(**jobcard_data)
            jobcard.full_clean()
            jobcard.save()
            
            # Update inquiry status
            inquiry.status = Inquiry.InquiryStatus.CONVERTED
            inquiry.save()
            
            return jobcard
            
        except Inquiry.DoesNotExist:
            raise ValidationError("Inquiry not found")


class JobCardService:
    """Service class for JobCard-related business logic."""
    
    @staticmethod
    def create_jobcard(data: Dict[str, Any]) -> JobCard:
        """Create a new job card with validation."""
        jobcard = JobCard(**data)
        jobcard.full_clean()  # Run model validation
        jobcard.save()
        return jobcard
    
    @staticmethod
    def calculate_statistics(queryset=None) -> Dict[str, Any]:
        """Calculate job card statistics."""
        if queryset is None:
            queryset = JobCard.objects.all()
        
        total_jobs = queryset.count()
        completed_jobs = queryset.filter(status=JobCard.JobStatus.DONE).count()
        pending_jobs = total_jobs - completed_jobs
        
        # Calculate total revenue
        total_revenue = sum(job.grand_total for job in queryset.select_related('client'))
        
        # Calculate completion rate
        completion_rate = (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
        
        return {
            'total_jobs': total_jobs,
            'completed_jobs': completed_jobs,
            'pending_jobs': pending_jobs,
            'total_revenue': str(total_revenue),
            'completion_rate': round(completion_rate, 2),
        }
    
    @staticmethod
    def update_payment_status(jobcard_id: int, status: str) -> bool:
        """Update payment status of a job card."""
        try:
            jobcard = JobCard.objects.get(id=jobcard_id)
            if status in [choice[0] for choice in JobCard.PaymentStatus.choices]:
                jobcard.payment_status = status
                jobcard.save()
                return True
            return False
        except JobCard.DoesNotExist:
            return False


class RenewalService:
    """Service class for Renewal-related business logic."""
    
    @staticmethod
    def create_renewal(data: Dict[str, Any]) -> Renewal:
        """Create a new renewal with validation."""
        renewal = Renewal(**data)
        renewal.full_clean()  # Run model validation
        renewal.save()
        return renewal
    
    @staticmethod
    def get_upcoming_summary() -> Dict[str, int]:
        """Get summary of upcoming renewals."""
        from datetime import timedelta
        
        now = timezone.now()
        week = now + timedelta(days=7)
        month = now + timedelta(days=30)
        
        renewals = Renewal.objects.filter(status=Renewal.RenewalStatus.DUE)
        
        return {
            'due_this_week': renewals.filter(due_date__lte=week, due_date__gte=now).count(),
            'due_this_month': renewals.filter(due_date__lte=month, due_date__gte=now).count(),
            'overdue': renewals.filter(due_date__lt=now).count(),
        }
    
    @staticmethod
    def mark_completed(renewal_id: int) -> bool:
        """Mark a renewal as completed."""
        try:
            renewal = Renewal.objects.get(id=renewal_id)
            renewal.status = Renewal.RenewalStatus.COMPLETED
            renewal.save()
            return True
        except Renewal.DoesNotExist:
            return False


class AuditService:
    """Service for audit logging (placeholder for future implementation)."""
    
    @staticmethod
    def log_action(user, action: str, model: str, object_id: int, changes: Dict = None):
        """Log user actions for audit trail."""
        # TODO: Implement audit logging
        # This could be implemented using django-audit-log or custom solution
        pass
