"""
Business logic services for the pest control application.
"""
from typing import Optional, Dict, Any
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import Client, Inquiry, JobCard, Renewal
import re


class ClientService:
    """Service class for Client-related business logic."""
    
    @staticmethod
    def create_client(data: Dict[str, Any]) -> Client:
        """Create a new client with validation."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Clean and validate mobile number
            if 'mobile' in data and data['mobile']:
                # Remove any spaces, dashes, or parentheses from mobile
                cleaned_mobile = re.sub(r'[\s\-\(\)]', '', str(data['mobile']))
                data['mobile'] = cleaned_mobile
            
            # Check if client already exists with this mobile
            try:
                existing_client = Client.objects.get(mobile=data['mobile'])
                raise ValidationError(f"A client with mobile number {data['mobile']} already exists.")
            except Client.DoesNotExist:
                pass  # Client doesn't exist, we can proceed
            
            # Ensure required fields are present
            required_fields = ['full_name', 'mobile', 'city']
            for field in required_fields:
                if not data.get(field):
                    raise ValidationError(f"{field.replace('_', ' ').title()} is required.")
            
            # Validate mobile number format
            if data.get('mobile') and not re.match(r'^\d{10}$', data['mobile']):
                raise ValidationError("Mobile number must be exactly 10 digits.")
            
            # Validate email if provided
            if data.get('email') and data['email'].strip():
                from django.core.validators import validate_email
                try:
                    validate_email(data['email'])
                except ValidationError:
                    raise ValidationError("Please enter a valid email address.")
            
            client = Client(**data)
            client.full_clean()  # Run model validation
            client.save()
            logger.debug(f"Successfully created client: {client}")
            return client
        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating client: {e}")
            raise ValidationError(f"Failed to create client: {str(e)}")
    
    @staticmethod
    def get_or_create_client(name: str, mobile: str, email: str = None, city: str = None) -> tuple[Client, bool]:
        """Get existing client or create new one."""
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Clean mobile number for consistent lookup
            cleaned_mobile = re.sub(r'[\s\-\(\)]', '', str(mobile))
            logger.debug(f"Looking for client with mobile: {cleaned_mobile}")
            
            # Try to find existing client with cleaned mobile
            client = Client.objects.get(mobile=cleaned_mobile)
            logger.debug(f"Found existing client: {client}")
            return client, False
        except Client.DoesNotExist:
            logger.debug(f"No existing client found, attempting to create new client with mobile: {cleaned_mobile}")
            # Try to create new client, but handle the case where it might already exist
            try:
                client_data = {
                    'full_name': name,
                    'mobile': cleaned_mobile,
                    'email': email,
                    'city': city or 'Unknown'
                }
                client = ClientService.create_client(client_data)
                logger.debug(f"Successfully created new client: {client}")
                return client, True
            except ValidationError as e:
                logger.warning(f"Client creation failed with validation error: {e}")
                # If creation fails due to unique constraint, try to get the existing client again
                if 'mobile' in str(e) and 'already exists' in str(e):
                    logger.debug(f"Mobile number conflict detected, trying to find existing client again")
                    try:
                        client = Client.objects.get(mobile=cleaned_mobile)
                        logger.debug(f"Found existing client after conflict: {client}")
                        return client, False
                    except Client.DoesNotExist:
                        # If we still can't find it, re-raise the original error
                        logger.error(f"Client creation failed and cannot find existing client with mobile: {cleaned_mobile}")
                        raise e
                else:
                    raise e
    
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
    
    @staticmethod
    def check_client_exists(mobile: str) -> tuple[bool, Optional[Client]]:
        """Check if a client exists with the given mobile number."""
        try:
            # Clean mobile number for consistent lookup
            cleaned_mobile = re.sub(r'[\s\-\(\)]', '', str(mobile))
            client = Client.objects.get(mobile=cleaned_mobile)
            return True, client
        except Client.DoesNotExist:
            return False, None
    
    @staticmethod
    def create_or_get_client(data: Dict[str, Any]) -> tuple[Client, bool]:
        """Create a new client or get existing one if mobile number already exists."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Clean mobile number
        if 'mobile' in data and data['mobile']:
            cleaned_mobile = re.sub(r'[\s\-\(\)]', '', str(data['mobile']))
            data['mobile'] = cleaned_mobile
        
        # Check if client already exists
        try:
            existing_client = Client.objects.get(mobile=data['mobile'])
            logger.info(f"Client with mobile {data['mobile']} already exists: {existing_client}")
            return existing_client, False
        except Client.DoesNotExist:
            # Create new client
            try:
                client = ClientService.create_client(data)
                logger.info(f"Created new client: {client}")
                return client, True
            except ValidationError as e:
                # If creation fails due to unique constraint, try to get the existing client again
                if 'mobile' in str(e) and 'already exists' in str(e):
                    logger.debug(f"Mobile number conflict detected, trying to find existing client again")
                    try:
                        existing_client = Client.objects.get(mobile=data['mobile'])
                        logger.info(f"Found existing client after conflict: {existing_client}")
                        return existing_client, False
                    except Client.DoesNotExist:
                        logger.error(f"Client creation failed and cannot find existing client with mobile: {data['mobile']}")
                        raise e
                else:
                    raise e


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
            
            # Check if a specific client ID was provided in conversion data
            client_id = conversion_data.get('client_id')
            if client_id:
                try:
                    client = Client.objects.get(id=client_id)
                except Client.DoesNotExist:
                    raise ValidationError(f"Client with ID {client_id} does not exist.")
            else:
                # Get or create client
                try:
                    client, created = ClientService.get_or_create_client(
                        name=inquiry.name,
                        mobile=inquiry.mobile,
                        email=inquiry.email,
                        city=inquiry.city
                    )
                except ValidationError as e:
                    # Provide more specific error message for mobile number conflicts
                    if 'mobile' in str(e) and 'already exists' in str(e):
                        raise ValidationError(f"A client with mobile number {inquiry.mobile} already exists. Please use the existing client or update the mobile number.")
                    raise e
            
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
        try:
            # Handle client ID - convert to Client instance if it's an ID
            if 'client' in data and isinstance(data['client'], int):
                try:
                    client = Client.objects.get(id=data['client'])
                    data['client'] = client
                except Client.DoesNotExist:
                    raise ValidationError(f"Client with ID {data['client']} does not exist.")
            
            # Validate required fields
            required_fields = ['client', 'service_type', 'schedule_date', 'price_subtotal']
            for field in required_fields:
                if not data.get(field):
                    raise ValidationError(f"{field.replace('_', ' ').title()} is required.")
            
            # Validate price is positive
            if data.get('price_subtotal') and data['price_subtotal'] <= 0:
                raise ValidationError("Price must be greater than zero.")
            
            # Validate tax percentage if provided
            if data.get('tax_percent') and (data['tax_percent'] < 0 or data['tax_percent'] > 100):
                raise ValidationError("Tax percentage must be between 0 and 100.")
            
            jobcard = JobCard(**data)
            jobcard.full_clean()  # Run model validation
            jobcard.save()
            return jobcard
        except ValidationError:
            raise
        except Exception as e:
            raise ValidationError(f"Failed to create job card: {str(e)}")
    
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
