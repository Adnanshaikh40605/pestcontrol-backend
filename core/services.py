"""
Business logic services for the pest control application.
"""
from typing import Optional, Dict, Any, List
import logging
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum, Count, Value, FloatField, Q
from django.db.models.functions import Coalesce, Cast
from django.utils import timezone

from .models import Client, Inquiry, JobCard, Renewal, Technician, CRMInquiry
from .telegram import notify_new_inquiry


logger = logging.getLogger(__name__)


class TechnicianService:
    """
    Service class for Technician-related business logic.
    """
    
    @staticmethod
    def create_technician(data: Dict[str, Any]) -> Technician:
        """Create a new technician with validation."""
        logger.info(f"Creating technician: {data.get('name')}")
        technician = Technician.objects.create(**data)
        return technician

    @staticmethod
    def update_technician(technician_id: int, data: Dict[str, Any]) -> Technician:
        """Update technician details."""
        technician = Technician.objects.get(id=technician_id)
        for key, value in data.items():
            setattr(technician, key, value)
        technician.save()
        return technician





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
            required_fields = ['full_name', 'mobile']
            
            # Validate mobile number format
            mobile_pattern = r'^\d{10}$'
            if data.get('mobile') and not re.match(mobile_pattern, data['mobile']):
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
    def create_inquiry(data: Dict[str, Any], user=None) -> Inquiry:
        """Create a new inquiry with validation."""
        inquiry = Inquiry(created_by=user, **data)
        inquiry.full_clean()  # Run model validation
        inquiry.save()

        try:
            notify_new_inquiry(
                name=inquiry.name,
                mobile=inquiry.mobile,
                city=inquiry.city,
                service=inquiry.service_interest,
                message=inquiry.message,
                email=inquiry.email,
                premise_type=inquiry.premise_type,
                premise_size=inquiry.premise_size,
                estimated_price=str(inquiry.estimated_price) if inquiry.estimated_price else None,
                service_frequency=inquiry.service_frequency,
            )
        except Exception as exc:
            logger.error(
                "Failed to send Telegram notification for inquiry %s: %s",
                inquiry.id,
                exc,
                exc_info=True,
            )

        return inquiry
    
    @staticmethod
    @transaction.atomic
    def convert_to_jobcard(inquiry_id: int, conversion_data: Dict[str, Any], user=None) -> JobCard:
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
                'status': JobCard.JobStatus.PENDING,
                'service_type': inquiry.service_interest,
                'service_category': JobCard.ServiceCategory.AMC if inquiry.service_frequency == 'amc' else JobCard.ServiceCategory.ONE_TIME,
                'schedule_datetime': conversion_data.get('schedule_datetime', timezone.now()),
                'price': conversion_data.get('price', ''),
                'payment_status': JobCard.PaymentStatus.UNPAID,
                'created_by': user,
                'reference': 'Website',
            }
            
            # Set client_address from conversion_data or fallback to client.address
            client_address = conversion_data.get('client_address', '').strip() if conversion_data.get('client_address') else ''
            if not client_address and client.address and client.address.strip():
                client_address = client.address
            if client_address:
                jobcard_data['client_address'] = client_address
            
            jobcard = JobCard(**jobcard_data)
            jobcard.full_clean()
            jobcard.save()
            
            # Update inquiry status
            inquiry.status = Inquiry.InquiryStatus.CONVERTED
            inquiry.converted_by = user
            inquiry.save()
            
            return jobcard
            
        except Inquiry.DoesNotExist:
            raise ValidationError("Inquiry not found")


class JobCardService:
    """Service class for JobCard-related business logic."""

    @staticmethod
    def _normalize_fk_ids(jobcard_data: Dict[str, Any]) -> None:
        """API/CRM sends FK primary keys as ints; JobCard() expects *_id or model instances."""
        fk_fields = (
            'master_country',
            'master_state',
            'master_city',
            'master_location',
            'technician',
            'partner',
            'complaint_parent_booking',
            'parent_job',
        )
        for field in fk_fields:
            if field not in jobcard_data:
                continue
            val = jobcard_data[field]
            if val is None or val == '':
                jobcard_data[field] = None
                continue
            if isinstance(val, int):
                jobcard_data[f'{field}_id'] = val
                del jobcard_data[field]
    
    @staticmethod
    @transaction.atomic
    def create_jobcard(data: Dict[str, Any], user=None) -> JobCard:
        """
        Create a NEW job card with client get_or_create pattern.
        
        IMPORTANT: This method ALWAYS creates a new job card. Multiple job cards can be created
        for the same client (same phone number). Each job card is independent and will have
        its own unique code and ID.
        
        This method handles two scenarios:
        1. If 'client' is provided as an ID, it uses the existing client to create a new job card
        2. If 'client_data' is provided, it uses get_or_create to find or create a client by mobile number,
           then creates a new job card for that client
        
        Args:
            data (Dict[str, Any]): JobCard data with optional client_data for client creation
            
        Returns:
            JobCard: The newly created job card instance (always a new record)
            
        Raises:
            ValidationError: If validation fails or client creation fails
        """
        import logging
        from django.db import IntegrityError, transaction
        from django.core.exceptions import ValidationError
        
        logger = logging.getLogger(__name__)
        
        try:
            client = None
            client_was_created = False
            
            # Scenario 1: Client ID is provided (existing client)
            if 'client' in data and isinstance(data['client'], int):
                try:
                    client = Client.objects.get(id=data['client'])
                    logger.info(f"Using existing client ID: {data['client']}")
                    client_was_created = False
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
                            client_was_created = True
                        else:
                            logger.info(f"Found existing client with mobile: {cleaned_mobile}")
                            client_was_created = False
                            
                except IntegrityError as e:
                    # Handle race condition where another request created the client
                    logger.warning(f"IntegrityError during client creation: {e}")
                    
                    # Try to get the existing client
                    try:
                        client = Client.objects.get(mobile=cleaned_mobile)
                        logger.info(f"Retrieved existing client after IntegrityError: {cleaned_mobile}")
                        client_was_created = False
                    except Client.DoesNotExist:
                        # This shouldn't happen, but handle it gracefully
                        raise ValidationError("Failed to create or retrieve client due to database constraint.")
            
            else:
                raise ValidationError("Either 'client' (ID) or 'client_data' must be provided.")
            
            # Validate that we have a client
            if not client:
                raise ValidationError("No valid client found or created.")
            
            # If client already existed (not created), update editable fields if provided in client_data
            # This ensures email, city, address, notes can be updated even when client exists
            # IMPORTANT: Client name (full_name) should NOT be updated - it remains as-is
            if 'client_data' in data and data['client_data'] and not client_was_created:
                client_data = data['client_data']
                update_fields = []
                
                # Only update email, city, address, notes - NOT full_name
                # Check each field and only update if value changed
                if 'email' in client_data and client_data.get('email') is not None:
                    new_email = client_data.get('email', '').strip()
                    current_email = client.email or ''
                    if new_email and new_email != current_email:
                        client.email = new_email
                        update_fields.append('email')
                
                if 'city' in client_data and client_data.get('city'):
                    new_city = client_data.get('city', '').strip()
                    if new_city and client.city != new_city:
                        client.city = new_city
                        update_fields.append('city')
                
                if 'address' in client_data and client_data.get('address') is not None:
                    new_address = client_data.get('address', '').strip()
                    current_address = client.address or ''
                    if new_address != current_address:
                        client.address = new_address
                        update_fields.append('address')




                
                if 'notes' in client_data and client_data.get('notes') is not None:
                    new_notes = client_data.get('notes', '').strip()
                    current_notes = client.notes or ''
                    if new_notes != current_notes:
                        client.notes = new_notes
                        update_fields.append('notes')
                
                if update_fields:
                    client.save(update_fields=update_fields)
                    logger.info(f"Updated existing client fields: {', '.join(update_fields)}")
            
            # Remove client_data and id from jobcard data
            # client_data is not a JobCard field
            # id should never be set during creation to prevent accidental updates
            jobcard_data = {k: v for k, v in data.items() if k not in ['client_data', 'id']}
            jobcard_data['client'] = client
            JobCardService._normalize_fk_ids(jobcard_data)
            
            # Use Pending as default status if not provided or empty
            if not jobcard_data.get('status'):
                jobcard_data['status'] = JobCard.JobStatus.PENDING
            elif jobcard_data.get('status') in ['Enquiry', 'WIP', 'Done', 'Cancel']:
                # Map old statuses to new ones if they come from old frontend code
                status_map = {
                    'Enquiry': JobCard.JobStatus.PENDING,
                    'WIP': JobCard.JobStatus.ON_PROCESS,
                    'Done': JobCard.JobStatus.DONE,
                    'Cancel': JobCard.JobStatus.CANCELLED
                }
                jobcard_data['status'] = status_map.get(jobcard_data['status'], JobCard.JobStatus.PENDING)
            
            # Explicitly ensure we're creating a new job card (not updating)
            if 'id' in jobcard_data:
                del jobcard_data['id']
            
            # Validate required fields (only basic ones for quick reminders)
            pass
            
            # Set default values
            if not jobcard_data.get('price'):
                jobcard_data['price'] = ''
            
            # Set client_address from client.address if not provided or empty
            # This ensures job cards always have an address, even if not explicitly provided
            client_address = jobcard_data.get('client_address', '').strip() if jobcard_data.get('client_address') else ''
            if not client_address and client.address and client.address.strip():
                jobcard_data['client_address'] = client.address
                logger.info(f"Using client's address for jobcard: {client.address}")
            
            # DUPLICATE SAFETY CHECK (Idempotency)
            # Prevent double-submits from frontend creating identical jobs within a short timeframe
            # Or same date/service/client combination
            if jobcard_data.get('schedule_datetime'):
                import dateutil.parser
                try:
                    schedule_date = dateutil.parser.parse(str(jobcard_data['schedule_datetime'])).date()
                    duplicate_check = JobCard.objects.filter(
                        client=client,
                        service_type=jobcard_data.get('service_type'),
                        schedule_datetime__date=schedule_date
                    ).order_by('-created_at').first()
                    
                    if duplicate_check:
                        # Check if it was created very recently (within 5 minutes) to avoid double clicks
                        time_diff = timezone.now() - duplicate_check.created_at
                        if time_diff.total_seconds() < 300:
                            logger.warning(f"DUPLICATE CREATION BLOCKED for client {client.id}, service {jobcard_data.get('service_type')}")
                            return duplicate_check
                except Exception as e:
                    logger.warning(f"Error checking for duplicate: {e}")

            # IMPORTANT: Always create a NEW job card - never update existing ones
            # Multiple job cards can exist for the same client
            jobcard = JobCard(created_by=user, creation_source=JobCard.CreationSource.API, **jobcard_data)
            
            # Set AMC Main Booking flag and Booking Type if it's the first AMC service
            if jobcard.service_category == JobCard.ServiceCategory.AMC and jobcard.service_cycle == 1:
                jobcard.is_amc_main_booking = True
                jobcard.booking_type = JobCard.BookingType.AMC_MAIN
            elif jobcard.is_complaint_call:
                jobcard.booking_type = JobCard.BookingType.COMPLAINT_CALL
            elif jobcard.is_followup_visit or jobcard.included_in_amc:
                jobcard.booking_type = JobCard.BookingType.AMC_FOLLOWUP
            elif jobcard.is_service_call:
                jobcard.booking_type = JobCard.BookingType.SERVICE_CALL
            else:
                jobcard.booking_type = JobCard.BookingType.NEW_BOOKING
            
            # Auto-calculate next service date if not provided
            if not jobcard.next_service_date:
                next_date, max_cycle = JobCardService.calculate_next_service_date(jobcard)
                jobcard.next_service_date = next_date
                jobcard.max_cycle = max_cycle
            elif jobcard.service_type:
                # If next_service_date IS provided manually, still ensure max_cycle is set correctly
                _, max_cycle = JobCardService.calculate_next_service_date(jobcard)
                jobcard.max_cycle = max_cycle

            jobcard.full_clean()  # Run model validation
            jobcard.save()  # This will create a new record with a new ID and code
            
            logger.info(f"Successfully created NEW jobcard {jobcard.code} (ID: {jobcard.id}) for client {client.full_name} (ID: {client.id})")
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
    def calculate_next_service_date(jobcard: JobCard) -> tuple[Optional[timezone.datetime.date], int]:
        """
        Calculate the next service date and max cycle based on service rules.
        Returns (next_date, max_cycle).
        """
        from datetime import timedelta, datetime, date
        from dateutil.relativedelta import relativedelta
        
        service_type = jobcard.service_type.lower() if jobcard.service_type else ""
        service_category = jobcard.service_category
        schedule_datetime = jobcard.schedule_datetime
        
        if not schedule_datetime:
            return None, 1

        # Extract date from datetime
        if hasattr(schedule_datetime, 'date'):
            schedule_date = schedule_datetime.date()
        elif isinstance(schedule_datetime, str):
            try:
                from datetime import datetime as dt_
                schedule_date = dt_.strptime(schedule_datetime[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                return None, 1
        else:
            return None, 1
            
        next_date = None
        max_cycle = 1
        
        # Cockroach AMC: 3 services total, 4-month gap
        if "cockroach" in service_type and service_category == JobCard.ServiceCategory.AMC:
            max_cycle = 3
            next_date = schedule_date + relativedelta(months=4)
        # BedBug: 2 services total, 15-day gap
        elif "bedbug" in service_type or "bed bug" in service_type:
            max_cycle = 2
            next_date = schedule_date + timedelta(days=15)
            
        return next_date, max_cycle

    @staticmethod
    @transaction.atomic
    def handle_job_completion(jobcard: JobCard) -> Optional[JobCard]:
        """
        Handle automation when a job is marked as DONE.
        Creates the next job in the sequence if applicable for AMC or BedBug.
        Uses select_for_update to prevent race conditions and duplicate creation.
        """
        # Refetch with lock to prevent race conditions
        jobcard = JobCard.objects.select_for_update().get(id=jobcard.id)
        
        logger.info(f"Checking completion automation for JobCard {jobcard.code} (Status: {jobcard.status})")
        
        if jobcard.status == JobCard.JobStatus.DONE and jobcard.next_service_date:
            if jobcard.service_cycle < jobcard.max_cycle:
                # Check if next job already exists to avoid duplicates
                existing_next = JobCard.objects.filter(
                    parent_job=jobcard,
                    service_cycle=jobcard.service_cycle + 1
                ).exists()
                
                # Double safety: Check if ANY booking for this customer/service/date exists
                # regardless of parent_job to catch cases where relation broke
                duplicate_safety_check = JobCard.objects.filter(
                    client=jobcard.client,
                    service_type=jobcard.service_type,
                    schedule_datetime__date=jobcard.next_service_date,
                    service_cycle=jobcard.service_cycle + 1
                ).exists()
                
                if existing_next or duplicate_safety_check:
                    logger.info(f"Follow-up for {jobcard.code} already exists (Relation: {existing_next}, Loose Match: {duplicate_safety_check}), skipping duplicate creation.")
                    return None

                logger.info(f"Creating follow-up cycle {jobcard.service_cycle + 1} for JobCard {jobcard.code}")
                
                # Prepare data for next job
                # Note: next_job will automatically have is_service_call=True via model save logic
                next_job_data = {
                    'client': jobcard.client,
                    'service_type': jobcard.service_type,
                    'service_category': jobcard.service_category,
                    'schedule_datetime': jobcard.next_service_date,
                    'service_cycle': jobcard.service_cycle + 1,
                    'max_cycle': jobcard.max_cycle,
                    'parent_job': jobcard,
                    'commercial_type': jobcard.commercial_type,
                    'property_type': jobcard.property_type,
                    'bhk_size': jobcard.bhk_size,
                    'contract_duration': jobcard.contract_duration,
                    'price': "0",  # Follow-up visits are free
                    'client_address': jobcard.client_address,
                    'state': jobcard.state,
                    'city': jobcard.city,
                    'status': JobCard.JobStatus.UPCOMING,
                    'payment_status': JobCard.PaymentStatus.PAID,  # Mark as paid since it's included in AMC
                    'is_service_call': True,
                    'is_followup_visit': True,
                    'included_in_amc': True, # Always included for auto-generated follow-ups
                    'booking_type': JobCard.BookingType.AMC_FOLLOWUP if jobcard.service_category == JobCard.ServiceCategory.AMC else JobCard.BookingType.SERVICE_CALL,
                    'created_by': jobcard.created_by,
                    'creation_source': JobCard.CreationSource.AMC_AUTO,
                }
                
                next_job = JobCard.objects.create(**next_job_data)
                
                # Calculate next service date for the NEWLY created job
                next_next_date, _ = JobCardService.calculate_next_service_date(next_job)
                if next_job.service_cycle < next_job.max_cycle:
                    next_job.next_service_date = next_next_date
                    next_job.save(update_fields=['next_service_date'])
                
                logger.info(f"✅ Successfully auto-created follow-up job {next_job.code} for job {jobcard.code}")
                return next_job
        return None
    

    
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
    def create_renewal(data: Dict[str, Any], user=None) -> Renewal:
        """Create a new renewal with validation."""
        # Handle jobcard field - convert ID to instance if needed
        if 'jobcard' in data and isinstance(data['jobcard'], (int, str)):
            try:
                data['jobcard'] = JobCard.objects.get(id=data['jobcard'])
            except JobCard.DoesNotExist:
                raise ValidationError("JobCard with the given ID does not exist.")
        
        renewal = Renewal(created_by=user, **data)
        renewal.full_clean()  # Run model validation
        renewal.save()
        return renewal
    
    @staticmethod
    def generate_renewals_for_jobcard(jobcard: JobCard, force_regenerate: bool = False, user=None) -> list[Renewal]:
        """
        Generate renewals for a jobcard based on customer type and contract duration.
        Prevents duplicate renewals by checking existing ones.
        
        Args:
            jobcard: The job card to generate renewals for
            force_regenerate: If True, will regenerate even if renewals exist (default: False)
        
        Returns:
            List of created renewals (may be empty if duplicates exist)
        """
        from datetime import timedelta
        from dateutil.relativedelta import relativedelta
        
        renewals = []
        
        # Check if renewals already exist for this jobcard
        if not force_regenerate:
            existing_renewals = Renewal.objects.filter(jobcard=jobcard, status=Renewal.RenewalStatus.DUE)
            if existing_renewals.exists():
                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"Renewals already exist for job card {jobcard.code}, skipping generation")
                return list(existing_renewals)
        
        if jobcard.job_type == JobCard.JobType.CUSTOMER:
            # For customers, create renewal based on next_service_date
            if jobcard.next_service_date:
                renewal_date = jobcard.next_service_date
                
                # Check if renewal already exists for this date
                existing = Renewal.objects.filter(
                    jobcard=jobcard,
                    due_date=renewal_date,
                    renewal_type=Renewal.RenewalType.CONTRACT_RENEWAL
                ).first()
                
                if not existing:
                    renewal = Renewal(
                        jobcard=jobcard,
                        due_date=renewal_date,
                        renewal_type=Renewal.RenewalType.CONTRACT_RENEWAL,
                        remarks=f"Service renewal for customer {jobcard.client.full_name}",
                        created_by=user
                    )
                    renewal.save()
                    renewals.append(renewal)
                else:
                    renewals.append(existing)
        
        elif jobcard.job_type == JobCard.JobType.SOCIETY and jobcard.contract_duration:
            # For societies, create contract renewal and monthly reminders
            contract_months = int(jobcard.contract_duration)
            start_date = jobcard.schedule_datetime.date() if hasattr(jobcard.schedule_datetime, 'date') else jobcard.schedule_datetime
            
            # Create contract renewal (main renewal)
            contract_end_date = start_date + relativedelta(months=contract_months)
            contract_renewal_date = contract_end_date - timedelta(days=1)
            
            # Check if contract renewal already exists
            existing_contract = Renewal.objects.filter(
                jobcard=jobcard,
                due_date=contract_renewal_date,
                renewal_type=Renewal.RenewalType.CONTRACT_RENEWAL
            ).first()
            
            if not existing_contract:
                contract_renewal = Renewal(
                    jobcard=jobcard,
                    due_date=contract_renewal_date,
                    renewal_type=Renewal.RenewalType.CONTRACT_RENEWAL,
                    remarks=f"Contract renewal for society {jobcard.client.full_name} ({contract_months} months contract)",
                    created_by=user
                )
                contract_renewal.save()
                renewals.append(contract_renewal)
            else:
                renewals.append(existing_contract)
            
            # Create monthly reminders
            for month in range(1, contract_months + 1):
                monthly_date = start_date + relativedelta(months=month)
                reminder_date = monthly_date - timedelta(days=1)
                
                # Check if monthly reminder already exists
                existing_monthly = Renewal.objects.filter(
                    jobcard=jobcard,
                    due_date=reminder_date,
                    renewal_type=Renewal.RenewalType.MONTHLY_REMINDER
                ).first()
                
                if not existing_monthly:
                    monthly_reminder = Renewal(
                        jobcard=jobcard,
                        due_date=reminder_date,
                        renewal_type=Renewal.RenewalType.MONTHLY_REMINDER,
                        remarks=f"Monthly service reminder for society {jobcard.client.full_name} (Month {month})",
                        created_by=user
                    )
                    monthly_reminder.save()
                    renewals.append(monthly_reminder)
                else:
                    renewals.append(existing_monthly)
        
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
    def bulk_mark_completed(renewal_ids: list[int]) -> Dict[str, Any]:
        """
        Mark multiple renewals as completed.
        
        Returns:
            Dictionary with success_count, failed_count, and failed_ids
        """
        success_count = 0
        failed_count = 0
        failed_ids = []
        
        for renewal_id in renewal_ids:
            try:
                if RenewalService.mark_completed(renewal_id):
                    success_count += 1
                else:
                    failed_count += 1
                    failed_ids.append(renewal_id)
            except Exception as e:
                failed_count += 1
                failed_ids.append(renewal_id)
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Error marking renewal {renewal_id} as completed: {e}")
        
        return {
            'success_count': success_count,
            'failed_count': failed_count,
            'failed_ids': failed_ids,
            'total': len(renewal_ids)
        }
    
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


class DashboardService:
    """
    Service class for Dashboard-related business logic.
    
    This service handles all dashboard statistics operations including
    comprehensive data aggregation for the dashboard API endpoint.
    
    Key Features:
    - Efficient database queries for statistics
    - Comprehensive data aggregation
    - Performance optimized counting
    - Error handling and validation
    
    Example:
        stats = DashboardService.get_dashboard_statistics()
        # Returns: {
        #     'total_inquiries': 150,
        #     'total_job_cards': 89,
        #     'total_clients': 75,
        #     'renewals': 45
        # }
    """
    
    @staticmethod
    def get_dashboard_statistics(from_date: str = None, to_date: str = None) -> Dict[str, Any]:
        """Get comprehensive dashboard statistics with optional date range filtering."""
        try:
            from django.utils import timezone
            from django.db.models import Count, Q
            from datetime import timedelta
            
            today = timezone.now().date()
            
            # Prepare filters
            inquiry_filters = Q()
            jobcard_filters = Q()
            renewal_filters = Q()
            
            if from_date:
                inquiry_filters &= Q(created_at__date__gte=from_date)
                jobcard_filters &= Q(schedule_datetime__date__gte=from_date)
                renewal_filters &= Q(due_date__gte=from_date)
            if to_date:
                inquiry_filters &= Q(created_at__date__lte=to_date)
                jobcard_filters &= Q(schedule_datetime__date__lte=to_date)
                renewal_filters &= Q(due_date__lte=to_date)
            
            # Basic counts
            total_web_inquiries = Inquiry.objects.filter(inquiry_filters).count()
            total_crm_inquiries = CRMInquiry.objects.filter(inquiry_filters).count()
            total_inquiries = total_web_inquiries + total_crm_inquiries
            
            total_job_cards = JobCard.objects.filter(jobcard_filters).count()
            total_clients = Client.objects.count() 
            total_technicians = Technician.objects.filter(is_active=True).count()
            renewals = Renewal.objects.filter(renewal_filters).count()
            
            # Quotation counts
            from .models import Quotation
            quotation_filters = Q()
            if from_date:
                quotation_filters &= Q(created_at__date__gte=from_date)
            if to_date:
                quotation_filters &= Q(created_at__date__lte=to_date)
                
            total_quotations = Quotation.objects.filter(quotation_filters).count()
            approved_quotations = Quotation.objects.filter(quotation_filters, status='Approved').count()
            converted_quotations = Quotation.objects.filter(quotation_filters, status='Converted').count()
            
            # Service Category Breakdown
            category_stats = {
                'one_time': JobCard.objects.filter(jobcard_filters, service_category=JobCard.ServiceCategory.ONE_TIME).count(),
                'amc': JobCard.objects.filter(jobcard_filters, service_category=JobCard.ServiceCategory.AMC).count()
            }
            
            # Category Breakdown (Retail vs Corporate)
            job_type_stats = {
                'individual': JobCard.objects.filter(jobcard_filters, commercial_type=JobCard.CommercialType.HOME).count(),
                'society': JobCard.objects.filter(jobcard_filters).exclude(commercial_type=JobCard.CommercialType.HOME).count(),
            }
            
            # Status Breakdown (Pending = operational queue only, not scheduled service visits)
            status_stats = {
                'pending': JobCard.objects.filter(
                    jobcard_filters,
                    status=JobCard.JobStatus.PENDING,
                ).count(),
                'upcoming': JobCard.objects.filter(
                    jobcard_filters,
                    status=JobCard.JobStatus.UPCOMING,
                    booking_category__in=JobCard.UPCOMING_SERVICE_CATEGORIES,
                ).count(),
                'on_process': JobCard.objects.filter(jobcard_filters, status=JobCard.JobStatus.ON_PROCESS).count(),
                'done': JobCard.objects.filter(jobcard_filters, status=JobCard.JobStatus.DONE).count(),
                # Today's Jobs (always relative to today unless explicitly filtering for a range that excludes it)
                'confirmed': JobCard.objects.filter(schedule_datetime__date=today).count(),
                'completed': 0,
                'cancelled': 0,
                'hold': 0
            }
            
            # City breakdown (Top 5)
            city_stats = list(JobCard.objects.filter(jobcard_filters)
                             .exclude(city=None).exclude(city='')
                             .values('city')
                             .annotate(count=Count('city'))
                             .order_by('-count')[:5])
            
            # Property Type breakdown
            property_type_stats = list(JobCard.objects.filter(jobcard_filters)
                                     .exclude(property_type=None).exclude(property_type='')
                                     .values('property_type')
                                     .annotate(count=Count('property_type'))
                                     .order_by('-count'))
            
            # Revenue Stats (Only Done bookings, excluding complaints)
            # We include NEW_BOOKING, AMC_MAIN, AMC_FOLLOWUP, and SERVICE_CALL if they have a price
            revenue_filter_base = Q(
                status=JobCard.JobStatus.DONE,
                booking_type__in=[
                    JobCard.BookingType.NEW_BOOKING, 
                    JobCard.BookingType.AMC_MAIN,
                    JobCard.BookingType.AMC_FOLLOWUP,
                    JobCard.BookingType.SERVICE_CALL
                ]
            )
            
            yesterday = today - timedelta(days=1)
            month_start = today.replace(day=1)
            
            # Helper to aggregate revenue safely from CharField 'price'
            def get_revenue(filters):
                return JobCard.objects.filter(filters).aggregate(
                    total=Coalesce(Sum(Cast('price', FloatField())), Value(0.0, output_field=FloatField()))
                )['total']

            # Use completed_at if available, fallback to updated_at for legacy/manual marks
            today_revenue = get_revenue(revenue_filter_base & Q(completed_at__date=today))
            if today_revenue == 0: # Fallback check
                today_revenue = get_revenue(revenue_filter_base & Q(updated_at__date=today, completed_at__isnull=True))

            yesterday_revenue = get_revenue(revenue_filter_base & Q(completed_at__date=yesterday))
            if yesterday_revenue == 0:
                yesterday_revenue = get_revenue(revenue_filter_base & Q(updated_at__date=yesterday, completed_at__isnull=True))

            # Monthly Revenue for the target chart (Current Month)
            month_revenue = get_revenue(revenue_filter_base & Q(completed_at__date__gte=month_start))
            if month_revenue == 0:
                month_revenue = get_revenue(revenue_filter_base & Q(updated_at__date__gte=month_start, completed_at__isnull=True))

            # For the filtered range revenue
            range_revenue = 0
            if from_date or to_date:
                range_filter = Q(revenue_filter_base)
                if from_date:
                    range_filter &= Q(completed_at__date__gte=from_date)
                if to_date:
                    range_filter &= Q(completed_at__date__lte=to_date)
                
                range_revenue = get_revenue(range_filter)
            else:
                range_revenue = month_revenue # Default to monthly if no range

            logger.info(f"Dashboard Revenue Stats - Today: {today_revenue}, Yesterday: {yesterday_revenue}, Month: {month_revenue}, Range: {range_revenue}")
            
            return {
                'total_inquiries': total_inquiries,
                'total_web_inquiries': total_web_inquiries,
                'total_crm_inquiries': total_crm_inquiries,
                'total_job_cards': total_job_cards,
                'total_clients': total_clients,
                'total_technicians': total_technicians,
                'renewals': renewals,
                'total_quotations': total_quotations,
                'approved_quotations': approved_quotations,
                'converted_quotations': converted_quotations,
                'today_revenue': today_revenue,
                'yesterday_revenue': yesterday_revenue,
                'month_revenue': month_revenue,
                'range_revenue': range_revenue,
                'category_stats': category_stats,
                'status_stats': status_stats,
                'job_type_stats': job_type_stats,
                'city_stats': city_stats,
                'property_type_stats': property_type_stats,
            }
        except Exception as e:
            logger.error(f"Error retrieving dashboard statistics: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_dashboard_counts() -> Dict[str, Any]:
        """Get lightweight counts for sidebar badges."""
        try:
            from django.utils import timezone
            from .models import Inquiry, JobCard, CRMInquiry, Feedback, Reminder, Quotation
            today = timezone.now().date()
            
            return {
                "website_leads_unread": Inquiry.objects.filter(is_read=False).count(),
                "complaint_calls": JobCard.objects.filter(
                    booking_category=JobCard.BookingCategory.COMPLAINT_CALL,
                    status=JobCard.JobStatus.PENDING,
                ).count(),
                "reminders": Reminder.objects.filter(status='pending').count(),
                "feedbacks": Feedback.objects.filter(is_read=False).count(),
                "pending_quotations": Quotation.objects.filter(status='Sent').count()
            }
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error retrieving dashboard counts: {str(e)}")
            return {
                "website_leads_unread": 0,
                "complaint_calls": 0,
                "reminders": 0,
                "feedbacks": 0
            }

    @staticmethod
    def get_staff_performance(period: str = 'today') -> List[Dict[str, Any]]:
        """
        Get staff performance report based on the specified period.
        Periods: today, yesterday, this_week, this_month
        """
        from django.contrib.auth.models import User
        from django.utils import timezone
        from django.db.models import Count, Q
        from datetime import timedelta
        from .models import Inquiry, JobCard, CRMInquiry, Renewal

        now = timezone.now()
        today = now.date()
        
        if period == 'yesterday':
            start_date = today - timedelta(days=1)
            end_date = today
        elif period == 'this_week':
            start_date = today - timedelta(days=today.weekday())
            end_date = today + timedelta(days=1)
        elif period == 'this_month':
            start_date = today.replace(day=1)
            next_month = today.replace(day=28) + timedelta(days=4)
            end_date = next_month.replace(day=1)
        else:  # today
            start_date = today
            end_date = today + timedelta(days=1)

        # Get all active staff/admins
        staff_users = User.objects.filter(is_active=True).order_by('first_name', 'username')
        
        performance_data = []
        
        for user in staff_users:
            # Filters for the period
            date_filter_created = Q(created_at__date__gte=start_date, created_at__date__lt=end_date)
            date_filter_updated = Q(updated_at__date__gte=start_date, updated_at__date__lt=end_date)
            
            # 1. Inquiries Created (Website + CRM)
            website_inquiries_created = Inquiry.objects.filter(created_by=user).filter(date_filter_created).count()
            crm_inquiries_created = CRMInquiry.objects.filter(created_by=user).filter(date_filter_created).count()
            total_inquiries_created = website_inquiries_created + crm_inquiries_created
            
            # 2. Inquiries Converted
            website_converted = Inquiry.objects.filter(converted_by=user).filter(date_filter_updated).count()
            crm_converted = CRMInquiry.objects.filter(converted_by=user).filter(date_filter_updated).count()
            
            # 3. Bookings Created
            bookings_created = JobCard.objects.filter(created_by=user).filter(date_filter_created).count()
            
            # 4. Status Updates
            on_process_updates = JobCard.objects.filter(on_process_by=user).filter(date_filter_updated).count()
            done_updates = JobCard.objects.filter(done_by=user).filter(date_filter_updated).count()
            
            # 5. Complaint Calls Created
            complaint_calls_created = JobCard.objects.filter(created_by=user, booking_type=JobCard.BookingType.COMPLAINT_CALL).filter(date_filter_created).count()
            
            # 6. Reminders Created (Renewals)
            reminders_created = Renewal.objects.filter(created_by=user).filter(date_filter_created).count()
            
            # 7. Conversion Rate
            total_converted = website_converted + crm_converted
            conversion_rate = 0
            if total_inquiries_created > 0:
                conversion_rate = (total_converted / total_inquiries_created) * 100
            
            performance_data.append({
                'staff_id': user.id,
                'staff_name': user.get_full_name() or user.username,
                'total_inquiries_created': total_inquiries_created,
                'website_inquiries_converted': website_converted,
                'crm_inquiries_converted': crm_converted,
                'total_bookings_created': bookings_created,
                'total_on_process_updates': on_process_updates,
                'total_done_updates': done_updates,
                'total_complaint_calls_created': complaint_calls_created,
                'total_reminders_created': reminders_created,
                'conversion_rate': round(conversion_rate, 2)
            })
            
        return performance_data

class CRMInquiryService:
    """
    Service class for CRM Inquiry-related business logic.
    Supports staff-created inquiries and quick conversion to bookings.
    """
    
    @staticmethod
    def create_inquiry(data: Dict[str, Any], user=None) -> CRMInquiry:
        """Create a new CRM inquiry with optional user attribution."""
        logger.info(f"Creating CRM inquiry for: {data.get('name')} by user {user}")
        inquiry = CRMInquiry.objects.create(created_by=user, **data)
        return inquiry

    @staticmethod
    def update_inquiry(inquiry_id: int, data: Dict[str, Any]) -> CRMInquiry:
        """Update inquiry details."""
        inquiry = CRMInquiry.objects.get(id=inquiry_id)
        for key, value in data.items():
            setattr(inquiry, key, value)
        inquiry.save()
        return inquiry

    @staticmethod
    def convert_to_booking(inquiry_id: int, user=None) -> JobCard:
        """
        Convert a CRM inquiry into a live JobCard/Booking.
        This handles client resolution and job card initialization.
        """
        with transaction.atomic():
            inquiry = CRMInquiry.objects.select_for_update().get(id=inquiry_id)
            
            if inquiry.status == CRMInquiry.InquiryStatus.CONVERTED:
                raise ValidationError("This inquiry has already been converted to a booking.")

            # 1. Resolve Client (Get or Create)
            client, _ = ClientService.get_or_create_client(
                name=inquiry.name,
                mobile=inquiry.mobile,
                city=inquiry.location.split(',')[0] if inquiry.location else 'Unknown'
            )
            
            # 2. Map Inquiry to JobCard fields
            job_card_data = {
                'client': client.id,
                'client_address': inquiry.location or '',
                'service_type': inquiry.pest_type,
                'service_category': JobCard.ServiceCategory.AMC if inquiry.service_frequency == 'amc' else JobCard.ServiceCategory.ONE_TIME,
                'notes': inquiry.remark or '',
                'status': 'Pending',
                'schedule_datetime': timezone.now(),
                'state': client.state or 'Maharashtra',
                'city': client.city or 'Pune',
                'reference': 'CRM Inquiry',
            }
            
            # 3. Create the Job Card
            job_card = JobCardService.create_jobcard(job_card_data, user=user)
            
            # 4. Finalize Inquiry status
            inquiry.status = CRMInquiry.InquiryStatus.CONVERTED
            inquiry.converted_by = user
            inquiry.remark = f"{inquiry.remark or ''}\n[Converted to Booking {job_card.code}]".strip()
            inquiry.save()
            
            logger.info(f"Inquiry {inquiry_id} successfully converted to Booking {job_card.code}")
            return job_card
