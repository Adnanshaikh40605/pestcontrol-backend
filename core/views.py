import logging
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, permissions, decorators, response, status
from rest_framework.decorators import action
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Client, Inquiry, JobCard, Renewal
from .serializers import ClientSerializer, InquirySerializer, JobCardSerializer, RenewalSerializer
from .services import ClientService, InquiryService, JobCardService, RenewalService

logger = logging.getLogger(__name__)


def health_check(request):
    """Health check endpoint for monitoring."""
    return JsonResponse({
        'status': 'ok',
        'service': 'pestcontrol-backend',
        'version': '1.0.0',
        'endpoint': 'core'
    })


# CORS test endpoint removed for production security
# This endpoint was only for debugging and should not be in production


# LoginRateThrottle moved to core.auth module to avoid duplication


class BaseModelViewSet(viewsets.ModelViewSet):
    """Base viewset with common functionality."""
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    ordering_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']  # Default ordering (latest first)
    
    def handle_exception(self, exc):
        """Custom exception handling."""
        logger.error(f"API Error in {self.__class__.__name__}: {exc}", exc_info=True)
        
        if isinstance(exc, ValidationError):
            return response.Response(
                {'error': 'Validation failed', 'details': exc.message_dict},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().handle_exception(exc)
    
    def create(self, request, *args, **kwargs):
        """Override create to add logging."""
        logger.info(f"Creating {self.get_serializer().Meta.model.__name__}")
        return super().create(request, *args, **kwargs)
    
    def update(self, request, *args, **kwargs):
        """Override update to add logging."""
        logger.info(f"Updating {self.get_serializer().Meta.model.__name__} {kwargs.get('pk')}")
        return super().update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Override destroy to add logging."""
        logger.info(f"Deleting {self.get_serializer().Meta.model.__name__} {kwargs.get('pk')}")
        return super().destroy(request, *args, **kwargs)


class ClientViewSet(BaseModelViewSet):
    """ViewSet for managing clients."""
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    filterset_fields = ['city', 'is_active']
    search_fields = ['full_name', 'mobile', 'email']
    ordering_fields = ['created_at', 'updated_at', 'full_name', 'city', 'mobile']
    ordering = ['-created_at']  # Default: latest clients first
    
    @method_decorator(cache_page(300))  # Cache for 5 minutes
    @method_decorator(vary_on_headers('Authorization'))
    def list(self, request, *args, **kwargs):
        """List clients with caching."""
        return super().list(request, *args, **kwargs)
    
    def create(self, request, *args, **kwargs):
        """Create a new client using service layer."""
        try:
            logger.info(f"Creating client with data: {request.data}")
            client = ClientService.create_client(request.data)
            serializer = self.get_serializer(client)
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.warning(f"Client creation validation error: {e}")
            error_details = {}
            if hasattr(e, 'message_dict'):
                error_details = e.message_dict
            else:
                error_details = {'error': str(e)}
            
            return response.Response(
                {'error': 'Validation failed', 'details': error_details},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error creating client: {e}")
            return response.Response(
                {'error': 'Failed to create client', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def destroy(self, request, *args, **kwargs):
        """Soft delete client."""
        client_id = kwargs.get('pk')
        if ClientService.deactivate_client(client_id):
            return response.Response(status=status.HTTP_204_NO_CONTENT)
        return response.Response(
            {'error': 'Client not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    @decorators.action(detail=False, methods=['post'])
    def create_or_get(self, request):
        """Create a new client or get existing one if mobile number already exists."""
        try:
            logger.info(f"Creating or getting client with data: {request.data}")
            client, created = ClientService.create_or_get_client(request.data)
            serializer = self.get_serializer(client)
            
            response_data = serializer.data
            response_data['created'] = created
            response_data['message'] = 'Client created successfully' if created else 'Existing client found'
            
            return response.Response(response_data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        except ValidationError as e:
            logger.warning(f"Client creation/get validation error: {e}")
            error_details = {}
            if hasattr(e, 'message_dict'):
                error_details = e.message_dict
            else:
                error_details = {'error': str(e)}
            
            return response.Response(
                {'error': 'Validation failed', 'details': error_details},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error creating/getting client: {e}")
            return response.Response(
                {'error': 'Failed to create or get client', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class InquiryViewSet(BaseModelViewSet):
    """ViewSet for managing inquiries."""
    queryset = Inquiry.objects.all()
    serializer_class = InquirySerializer
    filterset_fields = ['status', 'city']
    search_fields = ['name', 'mobile', 'email', 'service_interest']
    ordering_fields = ['created_at', 'updated_at', 'name', 'status', 'city']
    ordering = ['-created_at']  # Default: latest inquiries first

    def get_permissions(self):
        """Allow unauthenticated public creation of inquiries."""
        action = getattr(self, 'action', None)
        if action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_authenticators(self):
        """Do not enforce Session/JWT auth on public create endpoint (avoids CSRF)."""
        action = getattr(self, 'action', None)
        if action == 'create':
            return []
        return super().get_authenticators()
    
    def create(self, request, *args, **kwargs):
        """Create a new inquiry using service layer."""
        try:
            inquiry = InquiryService.create_inquiry(request.data)
            serializer = self.get_serializer(inquiry)
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return response.Response(
                {'error': 'Validation failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @decorators.action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        """Convert inquiry to job card using service layer."""
        try:
            jobcard = InquiryService.convert_to_jobcard(pk, request.data)
            serializer = JobCardSerializer(jobcard)
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            logger.warning(f"Validation error converting inquiry {pk}: {e}")
            return response.Response(
                {'error': 'Validation failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Error converting inquiry {pk}: {e}")
            return response.Response(
                {'error': 'Failed to convert inquiry', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @decorators.action(detail=True, methods=['post'])
    def mark_as_read(self, request, pk=None):
        """Mark inquiry as read."""
        try:
            inquiry = self.get_object()
            inquiry.is_read = True
            inquiry.save()
            return response.Response({'status': 'marked as read'})
        except Exception as e:
            logger.error(f"Error marking inquiry {pk} as read: {e}")
            return response.Response(
                {'error': 'Failed to mark inquiry as read'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @decorators.action(detail=False, methods=['get'])
    def counts(self, request):
        """Get inquiry counts by status for notifications."""
        try:
            # Get counts for different statuses
            new_count = Inquiry.objects.filter(status='New').count()
            contacted_count = Inquiry.objects.filter(status='Contacted').count()
            total_new = new_count + contacted_count  # Total unhandled inquiries
            
            # Get unread counts (for notification badges)
            unread_new = Inquiry.objects.filter(status='New', is_read=False).count()
            unread_contacted = Inquiry.objects.filter(status='Contacted', is_read=False).count()
            unread_total = unread_new + unread_contacted  # Total unread inquiries
            
            return response.Response({
                'new': new_count,
                'contacted': contacted_count,
                'total_new': total_new,
                'unread_new': unread_new,
                'unread_contacted': unread_contacted,
                'unread_total': unread_total,  # This is what the badge should show
                'converted': Inquiry.objects.filter(status='Converted').count(),
                'closed': Inquiry.objects.filter(status='Closed').count(),
                'total': Inquiry.objects.count()
            })
        except Exception as e:
            logger.error(f"Error getting inquiry counts: {e}")
            return response.Response(
                {'error': 'Failed to get inquiry counts'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @decorators.action(detail=True, methods=['get'])
    def check_client_exists(self, request, pk=None):
        """Check if a client exists for the inquiry's mobile number."""
        try:
            inquiry = self.get_object()
            exists, client = ClientService.check_client_exists(inquiry.mobile)
            
            if exists:
                return response.Response({
                    'exists': True,
                    'client': ClientSerializer(client).data,
                    'message': f'A client with mobile number {inquiry.mobile} already exists.'
                })
            else:
                return response.Response({
                    'exists': False,
                    'message': f'No client found with mobile number {inquiry.mobile}.'
                })
        except Exception as e:
            logger.error(f"Error checking client existence for inquiry {pk}: {e}")
            return response.Response(
                {'error': 'Failed to check client existence'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JobCardViewSet(BaseModelViewSet):
    """ViewSet for managing job cards."""
    queryset = JobCard.objects.select_related('client').prefetch_related('renewals').all()
    serializer_class = JobCardSerializer
    filterset_fields = ['status', 'payment_status', 'client__city', 'job_type', 'contract_duration', 'is_paused']
    search_fields = ['code', 'client__full_name', 'client__mobile', 'service_type']
    ordering_fields = [
        'created_at', 'updated_at', 'schedule_date', 'status', 'payment_status', 
        'client__full_name', 'client__city', 'job_type', 'contract_duration'
    ]
    ordering = ['-created_at']  # Default: latest job cards first

    def get_queryset(self):
        """Enhanced queryset with custom filtering."""
        qs = super().get_queryset()
        
        # Support frontend query params
        city = self.request.query_params.get('city')
        if city:
            qs = qs.filter(client__city__iexact=city)
            
        date_from = self.request.query_params.get('from')
        date_to = self.request.query_params.get('to')
        if date_from:
            qs = qs.filter(schedule_date__gte=date_from)
        if date_to:
            qs = qs.filter(schedule_date__lte=date_to)
        
        # Filter by job type for Society Job Cards page
        job_type = self.request.query_params.get('job_type')
        if job_type:
            qs = qs.filter(job_type=job_type)
            
        return qs
    
    def create(self, request, *args, **kwargs):
        """
        Create a new job card with enhanced client handling.
        
        Supports two creation modes:
        1. With existing client ID: {"client": 123, "service_type": "...", ...}
        2. With client data: {"client_data": {"mobile": "1234567890", "full_name": "..."}, "service_type": "...", ...}
        
        The second mode uses get_or_create pattern to find existing client by mobile number
        or create a new one if it doesn't exist.
        """
        try:
            logger.info(f"Creating job card with data: {request.data}")
            
            # Validate that either client ID or client_data is provided
            if not request.data.get('client') and not request.data.get('client_data'):
                return response.Response(
                    {'error': 'Either client ID or client_data must be provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            jobcard = JobCardService.create_jobcard(request.data)
            serializer = self.get_serializer(jobcard)
            
            # Add client creation info to response
            response_data = serializer.data
            if 'client_data' in request.data:
                response_data['client_created'] = True
                response_data['message'] = 'Job card created successfully with client data'
            else:
                response_data['client_created'] = False
                response_data['message'] = 'Job card created successfully with existing client'
            
            return response.Response(response_data, status=status.HTTP_201_CREATED)
            
        except ValidationError as e:
            logger.error(f"Job card creation validation error: {e}")
            error_details = {}
            if hasattr(e, 'message_dict'):
                error_details = e.message_dict
            else:
                error_details = {'error': str(e)}
            
            return response.Response(
                {'error': 'Validation failed', 'details': error_details},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error creating job card: {e}")
            return response.Response(
                {'error': 'Failed to create job card', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @method_decorator(cache_page(60))  # Cache for 1 minute
    @decorators.action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get job card statistics using service layer."""
        qs = self.get_queryset()
        data = JobCardService.calculate_statistics(qs)
        return response.Response(data)
    
    @decorators.action(detail=True, methods=['patch'])
    def update_payment_status(self, request, pk=None):
        """Update payment status of a job card."""
        status_value = request.data.get('payment_status')
        if JobCardService.update_payment_status(pk, status_value):
            return response.Response({'message': 'Payment status updated'})
        return response.Response(
            {'error': 'Failed to update payment status'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    @decorators.action(detail=True, methods=['patch'])
    def toggle_pause(self, request, pk=None):
        """Toggle pause status for a jobcard."""
        try:
            is_paused = request.data.get('is_paused', False)
            success = RenewalService.toggle_jobcard_pause(pk, is_paused)
            
            if success:
                status_text = 'paused' if is_paused else 'resumed'
                return response.Response({
                    'message': f'JobCard {status_text} successfully',
                    'is_paused': is_paused
                })
            else:
                return response.Response(
                    {'error': 'JobCard not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        except Exception as e:
            logger.error(f"Error toggling pause for jobcard {pk}: {e}")
            return response.Response(
                {'error': 'Failed to toggle pause status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='reference-report')
    def reference_report(self, request):
        """Get reference statistics for job cards."""
        try:
            from django.db.models import Count
            
            # Get all job cards with reference field
            job_cards = JobCard.objects.filter(reference__isnull=False).exclude(reference='')
            
            # Count references
            reference_counts = job_cards.values('reference').annotate(
                count=Count('reference')
            ).order_by('-count')
            
            # Define all possible reference options
            all_references = [
                'Google', 'Facebook', 'YouTube', 'LinkedIn', 'SMS', 'website',
                'Play Store', 'Instagram', 'WhatsApp', 'Justdial', 'poster',
                'other', 'previous client', 'friend reference', 'no parking board', 'holding'
            ]
            
            # Create a dictionary with all references and their counts
            reference_data = {}
            for ref in all_references:
                reference_data[ref] = 0
            
            # Update with actual counts
            for item in reference_counts:
                ref_name = item['reference']
                if ref_name in reference_data:
                    reference_data[ref_name] = item['count']
            
            # Convert to list format for frontend
            result = []
            for ref_name, count in reference_data.items():
                result.append({
                    'reference_name': ref_name,
                    'reference_count': count
                })
            
            # Sort by count descending
            result.sort(key=lambda x: x['reference_count'], reverse=True)
            
            return response.Response({
                'results': result,
                'total_job_cards': job_cards.count(),
                'total_with_reference': sum(item['reference_count'] for item in result)
            })
            
        except Exception as e:
            logger.error(f"Error generating reference report: {e}")
            return response.Response(
                {'error': 'Failed to generate reference report'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='check-client')
    def check_client(self, request):
        """
        Check if a client exists by mobile number.
        
        Query parameters:
        - mobile: Mobile number to check
        
        Returns:
        - exists: Boolean indicating if client exists
        - client: Client data if exists
        - message: Descriptive message
        """
        try:
            mobile = request.query_params.get('mobile')
            
            if not mobile:
                return response.Response(
                    {'error': 'Mobile number is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Clean mobile number
            import re
            cleaned_mobile = re.sub(r'[\s\-\(\)]', '', str(mobile))
            
            if not cleaned_mobile.isdigit() or len(cleaned_mobile) != 10:
                return response.Response(
                    {'error': 'Mobile number must be exactly 10 digits'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Check if client exists
            try:
                client = Client.objects.get(mobile=cleaned_mobile)
                return response.Response({
                    'exists': True,
                    'client': ClientSerializer(client).data,
                    'message': f'Client found with mobile number {cleaned_mobile}'
                })
            except Client.DoesNotExist:
                return response.Response({
                    'exists': False,
                    'client': None,
                    'message': f'No client found with mobile number {cleaned_mobile}'
                })
                
        except Exception as e:
            logger.error(f"Error checking client existence: {e}")
            return response.Response(
                {'error': 'Failed to check client existence'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RenewalViewSet(BaseModelViewSet):
    """ViewSet for managing renewals."""
    queryset = Renewal.objects.select_related('jobcard', 'jobcard__client').all()
    serializer_class = RenewalSerializer
    filterset_fields = ['status', 'urgency_level', 'renewal_type']
    search_fields = ['jobcard__code', 'jobcard__client__full_name']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'status', 'urgency_level']
    ordering = ['due_date']  # Default: sort by due date (earliest first for renewals)

    def get_queryset(self):
        """Enhanced queryset with custom filtering for pause functionality and urgency levels."""
        qs = super().get_queryset()
        
        # Filter out paused renewals by default (unless explicitly requested)
        include_paused = self.request.query_params.get('include_paused', 'false').lower() == 'true'
        if not include_paused:
            qs = qs.filter(jobcard__is_paused=False)
        
        # Custom date range filters used by frontend
        due_date_gte = self.request.query_params.get('due_date_gte')
        due_date_lte = self.request.query_params.get('due_date_lte')
        due_date_lt = self.request.query_params.get('due_date_lt')
        
        if due_date_gte:
            qs = qs.filter(due_date__gte=due_date_gte)
        if due_date_lte:
            qs = qs.filter(due_date__lte=due_date_lte)
        if due_date_lt:
            qs = qs.filter(due_date__lt=due_date_lt)
        
        # Filter by urgency level
        urgency_level = self.request.query_params.get('urgency_level')
        if urgency_level:
            qs = qs.filter(urgency_level=urgency_level)
            
        return qs
    
    def create(self, request, *args, **kwargs):
        """Create a new renewal using service layer."""
        try:
            renewal = RenewalService.create_renewal(request.data)
            serializer = self.get_serializer(renewal)
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return response.Response(
                {'error': 'Validation failed', 'details': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @method_decorator(cache_page(300))  # Cache for 5 minutes
    @decorators.action(detail=False, methods=['get'])
    def upcoming_summary(self, request):
        """Get upcoming renewals summary using service layer."""
        data = RenewalService.get_upcoming_summary()
        return response.Response(data)
    
    @decorators.action(detail=True, methods=['patch'])
    def mark_completed(self, request, pk=None):
        """Mark a renewal as completed."""
        if RenewalService.mark_completed(pk):
            return response.Response({'message': 'Renewal marked as completed'})
        return response.Response(
            {'error': 'Renewal not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @decorators.action(detail=False, methods=['get'])
    def active(self, request):
        """Get active renewals (non-paused) with urgency level filtering."""
        try:
            urgency_level = request.query_params.get('urgency_level')
            renewals = RenewalService.get_active_renewals(urgency_level)
            serializer = self.get_serializer(renewals, many=True)
            return response.Response(serializer.data)
        except Exception as e:
            logger.error(f"Error getting active renewals: {e}")
            return response.Response(
                {'error': 'Failed to get active renewals'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @decorators.action(detail=False, methods=['post'])
    def update_urgency_levels(self, request):
        """Update urgency levels for all renewals."""
        try:
            updated_count = RenewalService.update_urgency_levels()
            return response.Response({
                'message': f'Updated urgency levels for {updated_count} renewals'
            })
        except Exception as e:
            logger.error(f"Error updating urgency levels: {e}")
            return response.Response(
                {'error': 'Failed to update urgency levels'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @decorators.action(detail=True, methods=['patch'])
    def toggle_pause(self, request, pk=None):
        """Toggle pause status for a jobcard (affects all its renewals)."""
        try:
            renewal = self.get_object()
            is_paused = request.data.get('is_paused', False)
            success = RenewalService.toggle_jobcard_pause(renewal.jobcard.id, is_paused)
            
            if success:
                status_text = 'paused' if is_paused else 'resumed'
                return response.Response({
                    'message': f'JobCard {status_text} successfully',
                    'is_paused': is_paused
                })
            else:
                return response.Response(
                    {'error': 'Failed to toggle pause status'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.error(f"Error toggling pause for renewal {pk}: {e}")
            return response.Response(
                {'error': 'Failed to toggle pause status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )



