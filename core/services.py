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
    """
    Service class for Client-related business logic.
    
    This service handles all client operations including creation, validation,
    and business rule enforcement. It provides a clean separation between
    the API layer and the database layer.
    
    Key Features:
    - Client creation with validation
    - Mobile number conflict resolution
    - Business rule enforcement
    - Audit logging integration
    
    Example:
        client_data = {
            'full_name': 'John Doe',
            'mobile': '9876543210',
            'email': 'john@example.com',
            'city': 'Mumbai'
        }
        client, created = ClientService.create_or_get_client(client_data)
    """
    
    @staticmethod
    def create_client(data: Dict[str, Any]) -> Client:
        """
        Create a new client with comprehensive validation.
        
        Args:
            data (Dict[str, Any]): Client data dictionary containing:
                - full_name (str): Client's full name
                - mobile (str): Mobile number (will be cleaned)
                - email (str, optional): Email address
                - city (str): City name
                - address (str, optional): Address
                - notes (str, optional): Additional notes
        
        Returns:
            Client: The created client instance
            
        Raises:
            ValidationError: If validation fails
            Exception: For unexpected errors
            
        Example:
            client_data = {
                'full_name': 'John Doe',
                'mobile': '9876543210',
                'city': 'Mumbai'
            }
            client = ClientService.create_client(client_data)
        """
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
    @transaction.atomic
    def get_or_create_client(name: str, mobile: str, email: str = None, city: str = None) -> tuple[Client, bool]:
        """Get existing client or create new one with proper locking to prevent race conditions."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Clean mobile number for consistent lookup
        cleaned_mobile = re.sub(r'[\s\-\(\)]', '', str(mobile))
        logger.debug(f"Looking for client with mobile: {cleaned_mobile}")
        
        # Use select_for_update to prevent race conditions
        try:
            # First, try to get existing client with row-level locking
            client = Client.objects.select_for_update().get(mobile=cleaned_mobile)
            logger.debug(f"Found existing client: {client}")
            return client, False
        except Client.DoesNotExist:
            logger.debug(f"No existing client found, attempting to create new client with mobile: {cleaned_mobile}")
            
            # Create new client with proper validation
            client_data = {
                'full_name': name,
                'mobile': cleaned_mobile,
                'email': email,
                'city': city or 'Unknown'
            }
            
            try:
                client = ClientService.create_client(client_data)
                logger.debug(f"Successfully created new client: {client}")
                return client, True
            except ValidationError as e:
                # If creation fails due to unique constraint, try to get the existing client again
                if 'mobile' in str(e) and 'already exists' in str(e):
                    logger.debug(f"Mobile number conflict detected, trying to find existing client again")
                    try:
                        client = Client.objects.select_for_update().get(mobile=cleaned_mobile)
                        logger.debug(f"Found existing client after conflict: {client}")
                        return client, False
                    except Client.DoesNotExist:
                        logger.error(f"Client creation failed and cannot find existing client with mobile: {cleaned_mobile}")
                        raise ValidationError(f"Unable to create or find client with mobile number {cleaned_mobile}")
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
    @transaction.atomic
    def create_or_get_client(data: Dict[str, Any]) -> tuple[Client, bool]:
        """Create a new client or get existing one if mobile number already exists with proper locking."""
        import logging
        logger = logging.getLogger(__name__)
        
        # Clean mobile number
        if 'mobile' in data and data['mobile']:
            cleaned_mobile = re.sub(r'[\s\-\(\)]', '', str(data['mobile']))
            data['mobile'] = cleaned_mobile
        
        # Use select_for_update to prevent race conditions
        try:
            existing_client = Client.objects.select_for_update().get(mobile=data['mobile'])
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
                        existing_client = Client.objects.select_for_update().get(mobile=data['mobile'])
                        logger.info(f"Found existing client after conflict: {existing_client}")
                        return existing_client, False
                    except Client.DoesNotExist:
                        logger.error(f"Client creation failed and cannot find existing client with mobile: {data['mobile']}")
                        raise ValidationError(f"Unable to create or find client with mobile number {data['mobile']}")
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
            
            # Create job card with proper defaults
            jobcard_data = {
                'client': client,
                'status': JobCard.JobStatus.ENQUIRY,
                'service_type': inquiry.service_interest,
                'schedule_date': conversion_data.get('schedule_date', timezone.now().date()),
                'technician_name': conversion_data.get('technician_name', 'TBD'),  # Default to 'TBD' instead of empty string
                'price': conversion_data.get('price', ''),
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
        """
        Create a new job card with client get_or_create pattern.
        
        This method handles two scenarios:
        1. If 'client' is provided as an ID, it uses the existing client
        2. If 'client_data' is provided, it uses get_or_create to find or create a client by mobile number
        
        Args:
            data (Dict[str, Any]): JobCard data with optional client_data for client creation
            
        Returns:
            JobCard: The created job card instance
            
        Raises:
            ValidationError: If validation fails or client creation fails
        """
        import logging
        from django.db import IntegrityError, transaction
        
        logger = logging.getLogger(__name__)
        
        try:
            client = None
            
            # Scenario 1: Client ID is provided (existing client)
            if 'client' in data and isinstance(data['client'], int):
                try:
                    client = Client.objects.get(id=data['client'])
                    logger.info(f"Using existing client ID: {data['client']}")
                except Client.DoesNotExist:
                    raise ValidationError(f"Client with ID {data['client']} does not exist.")
            
            # Scenario 2: Client data is provided (get_or_create pattern)
            elif 'client_data' in data and data['client_data']:
                client_data = data['client_data']
                mobile = client_data.get('mobile')
                
                if not mobile:
                    raise ValidationError("Mobile number is required in client_data for client creation.")
                
                # Clean mobile number
                cleaned_mobile = re.sub(r'[\s\-\(\)]', '', str(mobile))
                
                # Validate mobile number format
                if not cleaned_mobile.isdigit() or len(cleaned_mobile) != 10:
                    raise ValidationError("Mobile number must be exactly 10 digits.")
                
                # Use get_or_create with proper error handling for race conditions
                try:
                    with transaction.atomic():
                        client, created = Client.objects.get_or_create(
                            mobile=cleaned_mobile,
                            defaults={
                                'full_name': client_data.get('full_name', ''),
                                'email': client_data.get('email', ''),
                                'city': client_data.get('city', ''),
                                'address': client_data.get('address', ''),
                                'notes': client_data.get('notes', ''),
                                'is_active': True
                            }
                        )
                        
                        if created:
                            logger.info(f"Created new client with mobile: {cleaned_mobile}")
                        else:
                            logger.info(f"Found existing client with mobile: {cleaned_mobile}")
                            
                except IntegrityError as e:
                    # Handle race condition where another request created the client
                    logger.warning(f"IntegrityError during client creation: {e}")
                    
                    # Try to get the existing client
                    try:
                        client = Client.objects.get(mobile=cleaned_mobile)
                        logger.info(f"Retrieved existing client after IntegrityError: {cleaned_mobile}")
                    except Client.DoesNotExist:
                        # This shouldn't happen, but handle it gracefully
                        raise ValidationError("Failed to create or retrieve client due to database constraint.")
            
            else:
                raise ValidationError("Either 'client' (ID) or 'client_data' must be provided.")
            
            # Validate that we have a client
            if not client:
                raise ValidationError("No valid client found or created.")
            
            # Remove client_data from jobcard data as it's not a JobCard field
            jobcard_data = {k: v for k, v in data.items() if k != 'client_data'}
            jobcard_data['client'] = client
            
            # Validate required fields
            required_fields = ['service_type', 'schedule_date']
            for field in required_fields:
                if not jobcard_data.get(field):
                    raise ValidationError(f"{field.replace('_', ' ').title()} is required.")
            
            # Set default values
            if not jobcard_data.get('price'):
                jobcard_data['price'] = ''
            
            if not jobcard_data.get('technician_name'):
                jobcard_data['technician_name'] = 'TBD'
            
            # Create and save jobcard
            jobcard = JobCard(**jobcard_data)
            jobcard.full_clean()  # Run model validation
            jobcard.save()
            
            logger.info(f"Successfully created jobcard {jobcard.code} for client {client.full_name}")
            return jobcard
            
        except ValidationError:
            raise
        except IntegrityError as e:
            logger.error(f"IntegrityError during jobcard creation: {e}")
            raise ValidationError("Failed to create job card due to database constraint.")
        except Exception as e:
            logger.error(f"Unexpected error during jobcard creation: {e}")
            raise ValidationError(f"Failed to create job card: {str(e)}")
    
    @staticmethod
    def calculate_statistics(queryset=None) -> Dict[str, Any]:
        """Calculate job card statistics."""
        if queryset is None:
            queryset = JobCard.objects.all()
        
        total_jobs = queryset.count()
        completed_jobs = queryset.filter(status=JobCard.JobStatus.DONE).count()
        pending_jobs = total_jobs - completed_jobs
        
        # Calculate total revenue (using price field as string, so we'll skip this for now)
        total_revenue = 0
        
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
        # Handle jobcard field - convert ID to instance if needed
        if 'jobcard' in data and isinstance(data['jobcard'], (int, str)):
            try:
                data['jobcard'] = JobCard.objects.get(id=data['jobcard'])
            except JobCard.DoesNotExist:
                raise ValidationError("JobCard with the given ID does not exist.")
        
        renewal = Renewal(**data)
        renewal.full_clean()  # Run model validation
        renewal.save()
        return renewal
    
    @staticmethod
    def generate_renewals_for_jobcard(jobcard: JobCard) -> list[Renewal]:
        """Generate renewals for a jobcard based on customer type and contract duration."""
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        renewals = []
        
        if jobcard.job_type == JobCard.JobType.CUSTOMER:
            # For customers, create renewal based on next_service_date
            if jobcard.next_service_date:
                renewal_date = timezone.make_aware(
                    timezone.datetime.combine(jobcard.next_service_date, timezone.datetime.min.time())
                )
                renewal = Renewal(
                    jobcard=jobcard,
                    due_date=renewal_date,
                    renewal_type=Renewal.RenewalType.CONTRACT_RENEWAL,
                    remarks=f"Service renewal for customer {jobcard.client.full_name}"
                )
                renewal.save()
                renewals.append(renewal)
        
        elif jobcard.job_type == JobCard.JobType.SOCIETY and jobcard.contract_duration:
            # For societies, create contract renewal and monthly reminders
            contract_months = int(jobcard.contract_duration)
            start_date = jobcard.schedule_date
            
            # Create contract renewal (main renewal)
            contract_end_date = start_date + relativedelta(months=contract_months)
            contract_renewal_date = timezone.make_aware(
                timezone.datetime.combine(contract_end_date - timedelta(days=1), timezone.datetime.min.time())
            )
            
            contract_renewal = Renewal(
                jobcard=jobcard,
                due_date=contract_renewal_date,
                renewal_type=Renewal.RenewalType.CONTRACT_RENEWAL,
                remarks=f"Contract renewal for society {jobcard.client.full_name} ({contract_months} months contract)"
            )
            contract_renewal.save()
            renewals.append(contract_renewal)
            
            # Create monthly reminders
            current_date = start_date
            for month in range(1, contract_months + 1):
                monthly_date = start_date + relativedelta(months=month)
                reminder_date = timezone.make_aware(
                    timezone.datetime.combine(monthly_date - timedelta(days=1), timezone.datetime.min.time())
                )
                
                monthly_reminder = Renewal(
                    jobcard=jobcard,
                    due_date=reminder_date,
                    renewal_type=Renewal.RenewalType.MONTHLY_REMINDER,
                    remarks=f"Monthly service reminder for society {jobcard.client.full_name} (Month {month})"
                )
                monthly_reminder.save()
                renewals.append(monthly_reminder)
        
        return renewals
    
    @staticmethod
    def get_active_renewals(include_paused: bool = False):
        """Get renewals that are not paused (unless specifically requested)."""
        renewals = Renewal.objects.select_related('jobcard', 'jobcard__client').filter(
            status=Renewal.RenewalStatus.DUE
        )
        
        if not include_paused:
            renewals = renewals.filter(jobcard__is_paused=False)
        
        return renewals
    
    @staticmethod
    def get_upcoming_summary(include_paused: bool = False) -> Dict[str, int]:
        """Get summary of upcoming renewals with pause functionality."""
        from datetime import timedelta
        
        now = timezone.now()
        week = now + timedelta(days=7)
        month = now + timedelta(days=30)
        
        renewals = RenewalService.get_active_renewals(include_paused=include_paused)
        
        return {
            'due_this_week': renewals.filter(due_date__lte=week, due_date__gte=now).count(),
            'due_this_month': renewals.filter(due_date__lte=month, due_date__gte=now).count(),
            'overdue': renewals.filter(due_date__lt=now).count(),
            'high_urgency': renewals.filter(urgency_level=Renewal.UrgencyLevel.HIGH).count(),
            'medium_urgency': renewals.filter(urgency_level=Renewal.UrgencyLevel.MEDIUM).count(),
            'normal_urgency': renewals.filter(urgency_level=Renewal.UrgencyLevel.NORMAL).count(),
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
    
    @staticmethod
    def update_urgency_levels():
        """Update urgency levels for all due renewals."""
        due_renewals = Renewal.objects.filter(status=Renewal.RenewalStatus.DUE)
        updated_count = 0
        for renewal in due_renewals:
            old_urgency = renewal.urgency_level
            renewal.update_urgency_level()
            if old_urgency != renewal.urgency_level:
                renewal.save(update_fields=['urgency_level'])
                updated_count += 1
        return updated_count
    
    @staticmethod
    def update_urgency_levels_for_jobcard(jobcard_id: int):
        """Update urgency levels for all renewals of a specific jobcard."""
        renewals = Renewal.objects.filter(jobcard_id=jobcard_id, status=Renewal.RenewalStatus.DUE)
        updated_count = 0
        for renewal in renewals:
            old_urgency = renewal.urgency_level
            renewal.update_urgency_level()
            if old_urgency != renewal.urgency_level:
                renewal.save(update_fields=['urgency_level'])
                updated_count += 1
        return updated_count
    
    @staticmethod
    def toggle_jobcard_pause(jobcard_id: int, is_paused: bool) -> bool:
        """Toggle pause status for a jobcard and its renewals."""
        try:
            jobcard = JobCard.objects.get(id=jobcard_id)
            jobcard.is_paused = is_paused
            jobcard.save()
            return True
        except JobCard.DoesNotExist:
            return False


class AuditService:
    """Service for comprehensive audit logging."""
    
    @staticmethod
    def log_action(user, action: str, model: str, object_id: int, changes: Dict = None, ip_address: str = None):
        """Log user actions for audit trail with comprehensive details."""
        import logging
        from django.utils import timezone
        
        logger = logging.getLogger('audit')
        
        audit_data = {
            'timestamp': timezone.now().isoformat(),
            'user_id': user.id if user and hasattr(user, 'id') else None,
            'username': user.username if user and hasattr(user, 'username') else 'Anonymous',
            'action': action,
            'model': model,
            'object_id': object_id,
            'changes': changes or {},
            'ip_address': ip_address,
        }
        
        # Log to audit logger
        logger.info(f"AUDIT: {action} on {model} (ID: {object_id}) by {audit_data['username']}", 
                   extra=audit_data)
    
    @staticmethod
    def log_client_action(user, action: str, client_id: int, changes: Dict = None, ip_address: str = None):
        """Log client-specific actions."""
        AuditService.log_action(user, action, 'Client', client_id, changes, ip_address)
    
    @staticmethod
    def log_inquiry_action(user, action: str, inquiry_id: int, changes: Dict = None, ip_address: str = None):
        """Log inquiry-specific actions."""
        AuditService.log_action(user, action, 'Inquiry', inquiry_id, changes, ip_address)
    
    @staticmethod
    def log_jobcard_action(user, action: str, jobcard_id: int, changes: Dict = None, ip_address: str = None):
        """Log job card-specific actions."""
        AuditService.log_action(user, action, 'JobCard', jobcard_id, changes, ip_address)
    
    @staticmethod
    def log_renewal_action(user, action: str, renewal_id: int, changes: Dict = None, ip_address: str = None):
        """Log renewal-specific actions."""
        AuditService.log_action(user, action, 'Renewal', renewal_id, changes, ip_address)
