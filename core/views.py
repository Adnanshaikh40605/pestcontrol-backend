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
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Client, Inquiry, JobCard, Renewal
from .serializers import ClientSerializer, InquirySerializer, JobCardSerializer, RenewalSerializer
from .services import ClientService, InquiryService, JobCardService, RenewalService, DashboardService

logger = logging.getLogger(__name__)


@extend_schema(
    summary="Health Check",
    description="Health check endpoint for monitoring service status",
    responses={
        200: {
            'description': 'Service is healthy',
            'content': {
                'application/json': {
                    'example': {
                        'status': 'ok',
                        'service': 'pestcontrol-backend',
                        'version': '1.0.0',
                        'endpoint': 'core'
                    }
                }
            }
        }
    },
    tags=['Health']
)
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


@extend_schema_view(
    list=extend_schema(
        summary="List Clients",
        description="Retrieve a paginated list of clients with filtering and search capabilities",
        parameters=[
            OpenApiParameter(
                name='city',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter clients by city'
            ),
            OpenApiParameter(
                name='is_active',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter clients by active status'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search clients by full name, mobile, or email'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order results by: created_at, updated_at, full_name, city, mobile (prefix with - for descending)'
            ),
        ],
        responses={
            200: ClientSerializer(many=True),
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
        },
        tags=['Clients']
    ),
    create=extend_schema(
        summary="Create Client",
        description="Create a new client record",
        request=ClientSerializer,
        responses={
            201: ClientSerializer,
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
        },
        examples=[
            OpenApiExample(
                'Client Creation Example',
                value={
                    'full_name': 'John Doe',
                    'mobile': '+1234567890',
                    'email': 'john.doe@example.com',
                    'city': 'New York',
                    'address': '123 Main St',
                    'is_active': True
                }
            )
        ],
        tags=['Clients']
    ),
    retrieve=extend_schema(
        summary="Get Client",
        description="Retrieve a specific client by ID",
        responses={
            200: ClientSerializer,
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Client not found'},
        },
        tags=['Clients']
    ),
    update=extend_schema(
        summary="Update Client",
        description="Update a client record",
        request=ClientSerializer,
        responses={
            200: ClientSerializer,
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Client not found'},
        },
        tags=['Clients']
    ),
    partial_update=extend_schema(
        summary="Partially Update Client",
        description="Partially update a client record",
        request=ClientSerializer,
        responses={
            200: ClientSerializer,
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Client not found'},
        },
        tags=['Clients']
    ),
    destroy=extend_schema(
        summary="Delete Client",
        description="Delete a client record",
        responses={
            204: {'description': 'Client deleted successfully'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Client not found'},
        },
        tags=['Clients']
    )
)
class ClientViewSet(BaseModelViewSet):
    """
    API endpoint that allows clients to be viewed, created, updated, or deleted.
    
    This endpoint provides full CRUD operations for client management including:
    - List all clients with filtering and search capabilities
    - Create new clients with validation
    - Update existing client information
    - Soft delete clients (deactivation)
    - Create or get existing client by mobile number
    
    Filtering options:
    - city: Filter by client city
    - is_active: Filter by active status
    
    Search fields:
    - full_name: Search by client name
    - mobile: Search by mobile number
    - email: Search by email address
    
    Ordering options:
    - created_at, updated_at, full_name, city, mobile
    """
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
    
    @extend_schema(
        summary="Create or Get Client",
        description="Create a new client or get existing one if mobile number already exists",
        request=ClientSerializer,
        responses={
            200: {
                'description': 'Existing client found',
                'content': {
                    'application/json': {
                        'example': {
                            'id': 1,
                            'full_name': 'John Doe',
                            'mobile': '+1234567890',
                            'email': 'john.doe@example.com',
                            'city': 'New York',
                            'address': '123 Main St',
                            'is_active': True,
                            'created': False,
                            'message': 'Existing client found'
                        }
                    }
                }
            },
            201: {
                'description': 'Client created successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'id': 2,
                            'full_name': 'Jane Smith',
                            'mobile': '+1987654321',
                            'email': 'jane.smith@example.com',
                            'city': 'Los Angeles',
                            'address': '456 Oak Ave',
                            'is_active': True,
                            'created': True,
                            'message': 'Client created successfully'
                        }
                    }
                }
            },
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            500: {'description': 'Internal server error'},
        },
        tags=['Clients']
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


@extend_schema_view(
    list=extend_schema(
        summary="List Inquiries",
        description="Retrieve a paginated list of inquiries with filtering and search capabilities",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter inquiries by status (pending, contacted, converted, closed)'
            ),
            OpenApiParameter(
                name='city',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter inquiries by city'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search inquiries by name, mobile, email, or service interest'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order results by: created_at, updated_at, name, status, city (prefix with - for descending)'
            ),
        ],
        responses={
            200: InquirySerializer(many=True),
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
        },
        tags=['Inquiries']
    ),
    create=extend_schema(
        summary="Create Inquiry",
        description="Create a new inquiry record (public endpoint - no authentication required)",
        request=InquirySerializer,
        responses={
            201: InquirySerializer,
            400: {'description': 'Validation error'},
        },
        examples=[
            OpenApiExample(
                'Inquiry Creation Example',
                value={
                    'name': 'John Doe',
                    'mobile': '+1234567890',
                    'email': 'john.doe@example.com',
                    'city': 'New York',
                    'address': '123 Main St',
                    'service_interest': 'Pest Control',
                    'message': 'Need pest control service for my home'
                }
            )
        ],
        tags=['Inquiries']
    ),
    retrieve=extend_schema(
        summary="Get Inquiry",
        description="Retrieve a specific inquiry by ID",
        responses={
            200: InquirySerializer,
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Inquiry not found'},
        },
        tags=['Inquiries']
    ),
    update=extend_schema(
        summary="Update Inquiry",
        description="Update an inquiry record",
        request=InquirySerializer,
        responses={
            200: InquirySerializer,
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Inquiry not found'},
        },
        tags=['Inquiries']
    ),
    partial_update=extend_schema(
        summary="Partially Update Inquiry",
        description="Partially update an inquiry record",
        request=InquirySerializer,
        responses={
            200: InquirySerializer,
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Inquiry not found'},
        },
        tags=['Inquiries']
    ),
    destroy=extend_schema(
        summary="Delete Inquiry",
        description="Delete an inquiry record",
        responses={
            204: {'description': 'Inquiry deleted successfully'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Inquiry not found'},
        },
        tags=['Inquiries']
    )
)
class InquiryViewSet(BaseModelViewSet):
    """
    API endpoint that allows inquiries to be viewed, created, updated, or deleted.
    
    This endpoint provides full CRUD operations for inquiry management including:
    - List all inquiries with filtering and search capabilities
    - Create new inquiries (public endpoint - no authentication required)
    - Update inquiry status and information
    - Convert inquiries to job cards
    - Mark inquiries as read/unread
    - Get inquiry counts and information
    
    Filtering options:
    - status: Filter by inquiry status (New, Contacted, Converted, Closed)
    - city: Filter by city
    
    Search fields:
    - name: Search by customer name
    - mobile: Search by mobile number
    - email: Search by email address
    - service_interest: Search by service interest
    
    Ordering options:
    - created_at, updated_at, name, status, city
    """
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

    @extend_schema(
        summary="Convert Inquiry to Job Card",
        description="Convert an inquiry to a job card with client and service details",
        request={
            'type': 'object',
            'properties': {
                'client_data': {
                    'type': 'object',
                    'description': 'Client information for job card creation'
                },
                'service_details': {
                    'type': 'object',
                    'description': 'Service details for the job card'
                }
            }
        },
        responses={
            201: JobCardSerializer,
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Inquiry not found'},
            500: {'description': 'Internal server error'},
        },
        tags=['Inquiries']
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

    @extend_schema(
        summary="Mark Inquiry as Read",
        description="Mark an inquiry as read to track which inquiries have been reviewed",
        responses={
            200: {
                'description': 'Inquiry marked as read successfully',
                'content': {
                    'application/json': {
                        'example': {'status': 'marked as read'}
                    }
                }
            },
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Inquiry not found'},
            500: {'description': 'Internal server error'},
        },
        tags=['Inquiries']
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



    @extend_schema(
        summary="Check if Client Exists",
        description="Check if a client exists based on inquiry data (mobile number)",
        responses={
            200: {
                'description': 'Client existence check result',
                'content': {
                    'application/json': {
                        'example': {
                            'client_exists': True,
                            'client_id': 123,
                            'client_name': 'John Doe'
                        }
                    }
                }
            },
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Inquiry not found'},
        },
        tags=['Inquiries']
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
                    'client': None,
                    'message': f'No client found with mobile number {inquiry.mobile}.'
                })
        except Exception as e:
            logger.error(f"Error checking client existence: {e}")
            return response.Response(
                {'error': 'Failed to check client existence'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    list=extend_schema(
        summary="List Job Cards",
        description="Retrieve a paginated list of job cards with filtering and search capabilities",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter job cards by status (pending, in_progress, completed, cancelled)'
            ),
            OpenApiParameter(
                name='payment_status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter job cards by payment status (pending, paid, overdue)'
            ),
            OpenApiParameter(
                name='client__city',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter job cards by client city'
            ),
            OpenApiParameter(
                name='job_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter job cards by job type'
            ),
            OpenApiParameter(
                name='contract_duration',
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description='Filter job cards by contract duration in months'
            ),
            OpenApiParameter(
                name='is_paused',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Filter job cards by paused status'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search job cards by code, client name, mobile, or service type'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order results by: created_at, updated_at, schedule_date, status, payment_status, client__full_name, client__city, job_type, contract_duration (prefix with - for descending)'
            ),
        ],
        responses={
            200: JobCardSerializer(many=True),
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
        },
        tags=['Job Cards']
    ),
    create=extend_schema(
        summary="Create Job Card",
        description="Create a new job card record",
        request=JobCardSerializer,
        responses={
            201: JobCardSerializer,
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
        },
        examples=[
            OpenApiExample(
                'Job Card Creation Example',
                value={
                    'client': 1,
                    'service_type': 'Pest Control',
                    'job_type': 'residential',
                    'schedule_date': '2024-01-15',
                    'contract_duration': 12,
                    'amount': 1500.00,
                    'description': 'Regular pest control service'
                }
            )
        ],
        tags=['Job Cards']
    ),
    retrieve=extend_schema(
        summary="Get Job Card",
        description="Retrieve a specific job card by ID",
        responses={
            200: JobCardSerializer,
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Job card not found'},
        },
        tags=['Job Cards']
    ),
    update=extend_schema(
        summary="Update Job Card",
        description="Update a job card record",
        request=JobCardSerializer,
        responses={
            200: JobCardSerializer,
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Job card not found'},
        },
        tags=['Job Cards']
    ),
    partial_update=extend_schema(
        summary="Partially Update Job Card",
        description="Partially update a job card record",
        request=JobCardSerializer,
        responses={
            200: JobCardSerializer,
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Job card not found'},
        },
        tags=['Job Cards']
    ),
    destroy=extend_schema(
        summary="Delete Job Card",
        description="Delete a job card record",
        responses={
            204: {'description': 'Job card deleted successfully'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Job card not found'},
        },
        tags=['Job Cards']
    )
)
class JobCardViewSet(BaseModelViewSet):
    """
    API endpoint that allows job cards to be viewed, created, updated, or deleted.
    
    This endpoint provides full CRUD operations for job card management including:
    - List all job cards with filtering and search capabilities
    - Create new job cards with client data or existing client ID
    - Update job card information and status
    - Update payment status
    - Toggle pause/resume functionality
    - Check client existence by mobile number
    
    Filtering options:
    - status: Filter by job card status
    - payment_status: Filter by payment status
    - client__city: Filter by client city
    - job_type: Filter by job type (Residential, Commercial, Society)
    - contract_duration: Filter by contract duration
    - is_paused: Filter by pause status
    
    Search fields:
    - code: Search by job card code
    - client__full_name: Search by client name
    - client__mobile: Search by client mobile
    - service_type: Search by service type
    
    Ordering options:
    - created_at, updated_at, schedule_date, status, payment_status, 
      client__full_name, client__city, job_type, contract_duration
    """
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
        Create a NEW job card with enhanced client handling.
        
        IMPORTANT: This endpoint ALWAYS creates a new job card. Multiple job cards can be created
        for the same client (same phone number). Each job card is independent and will have
        its own unique code and ID.
        
        Supports two creation modes:
        1. With existing client ID: {"client": 123, "service_type": "...", ...}
           - Creates a new job card for the existing client
        2. With client data: {"client_data": {"mobile": "1234567890", "full_name": "..."}, "service_type": "...", ...}
           - Uses get_or_create pattern to find existing client by mobile number or create a new one
           - Then creates a new job card for that client
        
        Note: If a client already exists with the provided phone number, a new job card will still
        be created for that existing client. Previous job cards are never overwritten.
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
            
            # Automatically generate renewals for the job card if conditions are met
            try:
                generated_renewals = RenewalService.generate_renewals_for_jobcard(jobcard)
                logger.info(f"Generated {len(generated_renewals)} renewals for job card {jobcard.code}")
            except Exception as e:
                logger.warning(f"Failed to generate renewals for job card {jobcard.code}: {e}")
                # Don't fail job card creation if renewal generation fails
            
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

    def update(self, request, *args, **kwargs):
        """Update job card and generate renewals if relevant fields changed."""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Store original values to check for changes
        original_next_service_date = instance.next_service_date
        original_contract_duration = instance.contract_duration
        original_job_type = instance.job_type
        
        # Handle client updates if client_data is provided
        # IMPORTANT: Only update email, city, address, notes - NOT full_name
        if 'client_data' in request.data and request.data['client_data']:
            client_data = request.data['client_data']
            client = instance.client
            update_fields = []
            
            # Only update editable fields - NOT full_name
            if 'email' in client_data and client_data.get('email') is not None:
                new_email = client_data.get('email', '').strip()
                current_email = client.email or ''
                if new_email != current_email:
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
                logger.info(f"Updated client fields during job card update: {', '.join(update_fields)}")
        
        # Handle client_address fallback if not provided or empty
        # If client_address is not in request data or is empty, use client.address
        request_client_address = request.data.get('client_address', '').strip() if request.data.get('client_address') else ''
        if not request_client_address and instance.client and instance.client.address and instance.client.address.strip():
            # Only update if current client_address is empty/null
            current_client_address = instance.client_address or ''
            if not current_client_address.strip():
                instance.client_address = instance.client.address
                instance.save(update_fields=['client_address'])
                logger.info(f"Updated jobcard {instance.code} client_address from client.address: {instance.client.address}")
        
        # Perform the update
        response_obj = super().update(request, *args, partial=partial, **kwargs)
        
        # Check if renewal-related fields changed
        instance.refresh_from_db()
        renewal_fields_changed = (
            instance.next_service_date != original_next_service_date or
            instance.contract_duration != original_contract_duration or
            instance.job_type != original_job_type
        )
        
        # Generate renewals if relevant fields changed
        if renewal_fields_changed:
            try:
                generated_renewals = RenewalService.generate_renewals_for_jobcard(instance)
                logger.info(f"Generated {len(generated_renewals)} renewals for updated job card {instance.code}")
            except Exception as e:
                logger.warning(f"Failed to generate renewals for updated job card {instance.code}: {e}")
        
        return response_obj

    
    @extend_schema(
        summary="Update Payment Status",
        description="Update the payment status of a specific job card",
        request={
            'type': 'object',
            'properties': {
                'payment_status': {
                    'type': 'string',
                    'enum': ['pending', 'paid', 'overdue'],
                    'description': 'New payment status for the job card'
                }
            },
            'required': ['payment_status']
        },
        responses={
            200: {
                'description': 'Payment status updated successfully',
                'content': {
                    'application/json': {
                        'example': {'message': 'Payment status updated'}
                    }
                }
            },
            400: {'description': 'Invalid payment status or validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Job card not found'},
            500: {'description': 'Internal server error'},
        },
        tags=['Job Cards']
    )
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
    
    @extend_schema(
        summary="Toggle Job Card Pause Status",
        description="Pause or resume a job card and its associated renewals",
        request={
            'type': 'object',
            'properties': {
                'is_paused': {
                    'type': 'boolean',
                    'description': 'Whether to pause (true) or resume (false) the job card'
                }
            },
            'required': ['is_paused']
        },
        responses={
            200: {
                'description': 'Job card pause status updated successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'message': 'JobCard paused successfully',
                            'is_paused': True
                        }
                    }
                }
            },
            400: {'description': 'Validation error'},
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            404: {'description': 'Job card not found'},
            500: {'description': 'Internal server error'},
        },
        tags=['Job Cards']
    )
    @decorators.action(detail=True, methods=['patch', 'post'])
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



    @extend_schema(
        summary="Get Reference Report",
        description="Get simplified reference report showing reference names and their counts. Returns data in a simplified format with reference_name and reference_count for each lead source.",
        responses={
            200: {
                'description': 'Reference report retrieved successfully',
                'content': {
                    'application/json': {
                        'example': [
                            {
                                'reference_name': 'Google',
                                'reference_count': 46
                            },
                            {
                                'reference_name': 'SMS',
                                'reference_count': 1
                            },
                            {
                                'reference_name': 'website',
                                'reference_count': 1
                            },
                            {
                                'reference_name': 'Play Store',
                                'reference_count': 1
                            },
                            {
                                'reference_name': 'previous client',
                                'reference_count': 1
                            },
                            {
                                'reference_name': 'Facebook',
                                'reference_count': 0
                            }
                        ]
                    }
                }
            },
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            500: {'description': 'Internal server error'},
        },
        tags=['Job Cards']
    )
    @decorators.action(detail=False, methods=['get'], url_path='reference-report', permission_classes=[])
    def reference_statistics(self, request):
        """Get simplified reference report with reference_name and reference_count."""
        try:
            from django.db.models import Count
            
            # Define all possible reference sources
            all_references = [
                'Google', 'SMS', 'website', 'Play Store', 'previous client',
                'Facebook', 'YouTube', 'LinkedIn', 'Instagram', 'WhatsApp',
                'Justdial', 'poster', 'other', 'friend reference', 
                'no parking board', 'holding'
            ]
            
            # Get actual counts from database
            reference_counts = JobCard.objects.values('reference').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Create a dictionary for quick lookup
            counts_dict = {}
            for item in reference_counts:
                reference_name = item['reference'] or 'other'
                counts_dict[reference_name] = item['count']
            
            # Build the response with all references, including those with 0 count
            result = []
            for reference in all_references:
                result.append({
                    'reference_name': reference,
                    'reference_count': counts_dict.get(reference, 0)
                })
            
            # Add any additional references found in database that aren't in our predefined list
            for reference_name, count in counts_dict.items():
                if reference_name not in all_references:
                    result.append({
                        'reference_name': reference_name,
                        'reference_count': count
                    })
            
            return response.Response(result)
            
        except Exception as e:
            logger.error(f"Error generating reference report: {e}")
            return response.Response(
                {'error': 'Failed to generate reference report'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @extend_schema(
        summary="Get Reference Statistics",
        description="Get comprehensive reference statistics including total references, top references, and recent references.",
        responses={
            200: {
                'description': 'Reference statistics retrieved successfully',
                'content': {
                    'application/json': {
                        'example': {
                            'total_references': 150,
                            'top_references': [
                                {
                                    'reference': 'Google',
                                    'count': 45
                                },
                                {
                                    'reference': 'previous client',
                                    'count': 32
                                },
                                {
                                    'reference': 'Facebook',
                                    'count': 28
                                }
                            ],
                            'recent_references': [
                                {
                                    'reference': 'Google',
                                    'client_name': 'John Doe',
                                    'created_at': '2024-01-15T10:30:00Z'
                                },
                                {
                                    'reference': 'Facebook',
                                    'client_name': 'Jane Smith',
                                    'created_at': '2024-01-14T15:45:00Z'
                                }
                            ]
                        }
                    }
                }
            },
            401: {'description': 'Authentication required'},
            403: {'description': 'Permission denied'},
            500: {'description': 'Internal server error'},
        },
        tags=['Job Cards']
    )
    @decorators.action(detail=False, methods=['get'], url_path='reference-statistics', permission_classes=[])
    def get_reference_statistics(self, request):
        """Get comprehensive reference statistics with total, top references, and recent references."""
        try:
            from django.db.models import Count
            from django.utils import timezone
            from datetime import timedelta
            
            # Get total references count
            total_references = JobCard.objects.count()
            
            # Get top references (top 5 by count)
            top_references_data = JobCard.objects.values('reference').annotate(
                count=Count('id')
            ).order_by('-count')[:5]
            
            top_references = []
            for item in top_references_data:
                reference_name = item['reference'] or 'other'
                top_references.append({
                    'reference': reference_name,
                    'count': item['count']
                })
            
            # Get recent references (last 10 job cards with reference and client info)
            recent_references_data = JobCard.objects.select_related('client').order_by('-created_at')[:10]
            
            recent_references = []
            for jobcard in recent_references_data:
                recent_references.append({
                    'reference': jobcard.reference or 'other',
                    'client_name': jobcard.client.full_name if jobcard.client else 'Unknown',
                    'created_at': jobcard.created_at.isoformat()
                })
            
            result = {
                'total_references': total_references,
                'top_references': top_references,
                'recent_references': recent_references
            }
            
            return response.Response(result)
            
        except Exception as e:
            logger.error(f"Error generating reference statistics: {e}")
            return response.Response(
                {'error': 'Failed to generate reference statistics'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@extend_schema_view(
    statistics=extend_schema(
        summary="Get comprehensive dashboard statistics",
        description="Retrieve comprehensive statistical data for the dashboard including total counts for inquiries, job cards, clients, and renewals. Data is cached for 5 minutes for optimal performance.",
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'total_inquiries': {'type': 'integer', 'description': 'Total number of inquiries'},
                    'total_job_cards': {'type': 'integer', 'description': 'Total number of job cards'},
                    'total_clients': {'type': 'integer', 'description': 'Total number of clients'},
                    'renewals': {'type': 'integer', 'description': 'Total number of renewals'},
                    'status': {'type': 'string', 'description': 'Response status'},
                    'timestamp': {'type': 'string', 'description': 'Response timestamp'}
                },
                'example': {
                    'total_inquiries': 150,
                    'total_job_cards': 89,
                    'total_clients': 75,
                    'renewals': 23,
                    'status': 'success',
                    'timestamp': '2024-01-15T10:30:00Z'
                }
            },
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            500: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'status': {'type': 'string'},
                    'message': {'type': 'string'}
                },
                'example': {
                    'error': 'Failed to retrieve dashboard statistics',
                    'status': 'error',
                    'message': 'An internal error occurred while processing your request'
                }
            }
        },
        tags=['Dashboard']
    )
)
class DashboardViewSet(viewsets.GenericViewSet):
    """
    Dashboard API ViewSet for comprehensive statistical data.
    
    Provides endpoints for:
    - Get comprehensive dashboard statistics
    """
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [UserRateThrottle, AnonRateThrottle]
    
    @method_decorator(cache_page(300))  # Cache for 5 minutes
    @method_decorator(vary_on_headers('Authorization'))
    @decorators.action(detail=False, methods=['get'], url_path='statistics')
    def statistics(self, request):
        """
        Get comprehensive dashboard statistics.
        
        Returns:
            JSON response with total counts for inquiries, job cards, clients, and renewals.
            
        Response format:
        {
            "total_inquiries": 150,
            "total_job_cards": 89,
            "total_clients": 75,
            "renewals": 23,
            "status": "success",
            "timestamp": "2024-01-15T10:30:00Z"
        }
        """
        try:
            # Get dashboard statistics from service
            stats = DashboardService.get_dashboard_statistics()
            
            # Add metadata
            stats.update({
                'status': 'success',
                'timestamp': request.META.get('HTTP_DATE', ''),
            })
            
            logger.info(f"Dashboard statistics retrieved successfully for user {request.user.id}")
            
            return response.Response(
                stats,
                status=status.HTTP_200_OK,
                headers={
                    'Cache-Control': 'public, max-age=300',  # 5 minutes cache
                    'X-API-Version': 'v1',
                    'Content-Type': 'application/json'
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving dashboard statistics: {e}", exc_info=True)
            return response.Response(
                {
                    'error': 'Failed to retrieve dashboard statistics',
                    'status': 'error',
                    'message': 'An internal error occurred while processing your request'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    
    @extend_schema(
        summary="Check if client exists by mobile number",
        description="Check if a client exists in the system by their mobile number. Returns client data if found.",
        parameters=[
            OpenApiParameter(
                name='mobile',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Mobile number to check (10 digits)',
                required=True,
                examples=[
                    OpenApiExample('Valid Mobile', value='9876543210'),
                ]
            ),
        ],
        responses={
            200: {
                'type': 'object',
                'properties': {
                    'exists': {'type': 'boolean', 'description': 'Whether the client exists'},
                    'client': {'type': 'object', 'description': 'Client data if exists, null otherwise'},
                    'message': {'type': 'string', 'description': 'Descriptive message'}
                },
                'examples': {
                    'client_found': {
                        'summary': 'Client Found',
                        'value': {
                            'exists': True,
                            'client': {
                                'id': 1,
                                'full_name': 'John Doe',
                                'mobile': '9876543210',
                                'email': 'john@example.com'
                            },
                            'message': 'Client found with mobile number 9876543210'
                        }
                    },
                    'client_not_found': {
                        'summary': 'Client Not Found',
                        'value': {
                            'exists': False,
                            'client': None,
                            'message': 'No client found with mobile number 9876543210'
                        }
                    }
                }
            },
            400: {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'}
                },
                'examples': {
                    'missing_mobile': {
                        'summary': 'Missing Mobile Number',
                        'value': {'error': 'Mobile number is required'}
                    },
                    'invalid_mobile': {
                        'summary': 'Invalid Mobile Number',
                        'value': {'error': 'Mobile number must be exactly 10 digits'}
                    }
                }
            },
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            500: OpenApiExample('Server Error', value={'error': 'Failed to check client existence'})
        },
        tags=['Dashboard']
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


@extend_schema_view(
    list=extend_schema(
        summary="List all renewals",
        description="Retrieve a paginated list of all renewals with filtering and search capabilities. Supports filtering by status, urgency level, renewal type, and date ranges.",
        parameters=[
            OpenApiParameter(
                name='status',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by renewal status (Pending, In Progress, Completed, Overdue)',
                examples=[
                    OpenApiExample('Pending', value='Pending'),
                    OpenApiExample('Completed', value='Completed'),
                ]
            ),
            OpenApiParameter(
                name='urgency_level',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by urgency level (Low, Medium, High, Critical)',
                examples=[
                    OpenApiExample('High', value='High'),
                    OpenApiExample('Critical', value='Critical'),
                ]
            ),
            OpenApiParameter(
                name='renewal_type',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by renewal type'
            ),
            OpenApiParameter(
                name='include_paused',
                type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
                description='Include paused renewals in results (default: false)'
            ),
            OpenApiParameter(
                name='due_date_gte',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter renewals with due date greater than or equal to this date'
            ),
            OpenApiParameter(
                name='due_date_lte',
                type=OpenApiTypes.DATE,
                location=OpenApiParameter.QUERY,
                description='Filter renewals with due date less than or equal to this date'
            ),
            OpenApiParameter(
                name='search',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Search by job card code or client name'
            ),
            OpenApiParameter(
                name='ordering',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Order results by field (created_at, updated_at, due_date, status, urgency_level)'
            ),
        ],
        responses={
            200: RenewalSerializer(many=True),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            500: OpenApiExample('Server Error', value={'error': 'Internal server error'})
        },
        tags=['Renewals']
    ),
    create=extend_schema(
        summary="Create a new renewal",
        description="Create a new renewal for a job card with specified due date and renewal type.",
        request=RenewalSerializer,
        examples=[
            OpenApiExample(
                'Create Renewal',
                value={
                    'jobcard': 1,
                    'due_date': '2024-02-15',
                    'renewal_type': 'Annual',
                    'notes': 'Annual pest control renewal'
                }
            )
        ],
        responses={
            201: RenewalSerializer,
            400: OpenApiExample('Bad Request', value={'error': 'Validation failed', 'details': 'Invalid data provided'}),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            500: OpenApiExample('Server Error', value={'error': 'Internal server error'})
        },
        tags=['Renewals']
    ),
    retrieve=extend_schema(
        summary="Retrieve a specific renewal",
        description="Get detailed information about a specific renewal by its ID.",
        responses={
            200: RenewalSerializer,
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            404: OpenApiExample('Not Found', value={'detail': 'Not found.'}),
            500: OpenApiExample('Server Error', value={'error': 'Internal server error'})
        },
        tags=['Renewals']
    ),
    update=extend_schema(
        summary="Update a renewal",
        description="Update all fields of a specific renewal.",
        request=RenewalSerializer,
        responses={
            200: RenewalSerializer,
            400: OpenApiExample('Bad Request', value={'error': 'Validation failed'}),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            404: OpenApiExample('Not Found', value={'detail': 'Not found.'}),
            500: OpenApiExample('Server Error', value={'error': 'Internal server error'})
        },
        tags=['Renewals']
    ),
    partial_update=extend_schema(
        summary="Partially update a renewal",
        description="Update specific fields of a renewal.",
        request=RenewalSerializer,
        responses={
            200: RenewalSerializer,
            400: OpenApiExample('Bad Request', value={'error': 'Validation failed'}),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            404: OpenApiExample('Not Found', value={'detail': 'Not found.'}),
            500: OpenApiExample('Server Error', value={'error': 'Internal server error'})
        },
        tags=['Renewals']
    ),
    destroy=extend_schema(
        summary="Delete a renewal",
        description="Delete a specific renewal from the system.",
        responses={
            204: OpenApiExample('No Content', value=None),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            404: OpenApiExample('Not Found', value={'detail': 'Not found.'}),
            500: OpenApiExample('Server Error', value={'error': 'Internal server error'})
        },
        tags=['Renewals']
    )
)
class RenewalViewSet(BaseModelViewSet):
    """
    API endpoint that allows renewals to be viewed, created, updated, or deleted.
    
    This endpoint provides full CRUD operations for renewal management including:
    - List all renewals with filtering and search capabilities
    - Create new renewals for job cards
    - Update renewal information and status
    - Mark renewals as completed
    - Toggle pause/resume functionality for job cards
    - Get upcoming renewals summary
    - Update urgency levels for all renewals
    - Get active renewals with urgency filtering
    
    Filtering options:
    - status: Filter by renewal status
    - urgency_level: Filter by urgency level (Low, Medium, High, Critical)
    - renewal_type: Filter by renewal type
    
    Search fields:
    - jobcard__code: Search by job card code
    - jobcard__client__full_name: Search by client name
    
    Ordering options:
    - created_at, updated_at, due_date, status, urgency_level
    """
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


    
    @extend_schema(
        summary="Mark renewal as completed",
        description="Mark a specific renewal as completed and update its status.",
        request=None,
        responses={
            200: OpenApiExample('Success', value={'message': 'Renewal marked as completed'}),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            404: OpenApiExample('Not Found', value={'error': 'Renewal not found'}),
            500: OpenApiExample('Server Error', value={'error': 'Internal server error'})
        },
        tags=['Renewals']
    )
    @decorators.action(detail=True, methods=['patch', 'post'])
    def mark_completed(self, request, pk=None):
        """Mark a renewal as completed."""
        if RenewalService.mark_completed(pk):
            renewal = self.get_object()
            serializer = self.get_serializer(renewal)
            return response.Response({
                'message': 'Renewal marked as completed',
                'renewal': serializer.data
            })
        return response.Response(
            {'error': 'Renewal not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @extend_schema(
        summary="Get active renewals",
        description="Retrieve all active (non-paused) renewals with optional urgency level filtering.",
        parameters=[
            OpenApiParameter(
                name='urgency_level',
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description='Filter by urgency level (Low, Medium, High, Critical)',
                examples=[
                    OpenApiExample('High', value='High'),
                    OpenApiExample('Critical', value='Critical'),
                ]
            ),
        ],
        responses={
            200: RenewalSerializer(many=True),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            500: OpenApiExample('Server Error', value={'error': 'Failed to get active renewals'})
        },
        tags=['Renewals']
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
    
    @extend_schema(
        summary="Update urgency levels for all renewals",
        description="Automatically update urgency levels for all renewals based on their due dates and current status.",
        request=None,
        responses={
            200: OpenApiExample('Success', value={'message': 'Updated urgency levels for 15 renewals'}),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            500: OpenApiExample('Server Error', value={'error': 'Failed to update urgency levels'})
        },
        tags=['Renewals']
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
    
    @extend_schema(
        summary="Toggle pause status for renewal's job card",
        description="Toggle the pause status for the job card associated with this renewal, affecting all renewals for that job card.",
        request={
            'type': 'object',
            'properties': {
                'is_paused': {
                    'type': 'boolean',
                    'description': 'Whether to pause (true) or resume (false) the job card'
                }
            },
            'required': ['is_paused']
        },
        examples=[
            OpenApiExample('Pause Job Card', value={'is_paused': True}),
            OpenApiExample('Resume Job Card', value={'is_paused': False}),
        ],
        responses={
            200: OpenApiExample('Success', value={'message': 'JobCard paused successfully', 'is_paused': True}),
            400: OpenApiExample('Bad Request', value={'error': 'Failed to toggle pause status'}),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            403: OpenApiExample('Forbidden', value={'detail': 'You do not have permission to perform this action.'}),
            404: OpenApiExample('Not Found', value={'detail': 'Not found.'}),
            500: OpenApiExample('Server Error', value={'error': 'Failed to toggle pause status'})
        },
        tags=['Renewals']
    )
    @decorators.action(detail=True, methods=['patch', 'post'])
    def toggle_pause(self, request, pk=None):
        """Toggle pause status for a jobcard (affects all its renewals)."""
        try:
            renewal = self.get_object()
            is_paused = request.data.get('is_paused', False)
            success = RenewalService.toggle_jobcard_pause(renewal.jobcard.id, is_paused)
            
            if success:
                # Refresh the renewal object to get updated jobcard status
                renewal.refresh_from_db()
                serializer = self.get_serializer(renewal)
                status_text = 'paused' if is_paused else 'resumed'
                return response.Response({
                    'message': f'JobCard {status_text} successfully',
                    'is_paused': is_paused,
                    'renewal': serializer.data
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
    
    @extend_schema(
        summary="Bulk mark renewals as completed",
        description="Mark multiple renewals as completed in a single operation.",
        request={
            'type': 'object',
            'properties': {
                'renewal_ids': {
                    'type': 'array',
                    'items': {'type': 'integer'},
                    'description': 'List of renewal IDs to mark as completed'
                }
            },
            'required': ['renewal_ids']
        },
        examples=[
            OpenApiExample('Bulk Mark Completed', value={'renewal_ids': [1, 2, 3]}),
        ],
        responses={
            200: OpenApiExample('Success', value={
                'message': 'Bulk operation completed',
                'success_count': 3,
                'failed_count': 0,
                'failed_ids': [],
                'total': 3
            }),
            400: OpenApiExample('Bad Request', value={'error': 'renewal_ids is required'}),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            500: OpenApiExample('Server Error', value={'error': 'Failed to process bulk operation'})
        },
        tags=['Renewals']
    )
    @decorators.action(detail=False, methods=['post'])
    def bulk_mark_completed(self, request):
        """Bulk mark renewals as completed."""
        try:
            renewal_ids = request.data.get('renewal_ids', [])
            
            if not renewal_ids:
                return response.Response(
                    {'error': 'renewal_ids is required and cannot be empty'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not isinstance(renewal_ids, list):
                return response.Response(
                    {'error': 'renewal_ids must be a list of integers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            result = RenewalService.bulk_mark_completed(renewal_ids)
            
            return response.Response({
                'message': 'Bulk operation completed',
                **result
            })
        except Exception as e:
            logger.error(f"Error in bulk mark completed: {e}")
            return response.Response(
                {'error': 'Failed to process bulk operation'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @extend_schema(
        summary="Generate renewals for a job card",
        description="Manually trigger renewal generation for a specific job card.",
        request={
            'type': 'object',
            'properties': {
                'jobcard_id': {
                    'type': 'integer',
                    'description': 'ID of the job card to generate renewals for'
                },
                'force_regenerate': {
                    'type': 'boolean',
                    'description': 'Force regeneration even if renewals exist (default: false)'
                }
            },
            'required': ['jobcard_id']
        },
        responses={
            200: OpenApiExample('Success', value={
                'message': 'Renewals generated successfully',
                'renewals_count': 3,
                'renewals': []
            }),
            400: OpenApiExample('Bad Request', value={'error': 'Job card not found'}),
            401: OpenApiExample('Unauthorized', value={'detail': 'Authentication credentials were not provided.'}),
            500: OpenApiExample('Server Error', value={'error': 'Failed to generate renewals'})
        },
        tags=['Renewals']
    )
    @decorators.action(detail=False, methods=['post'])
    def generate_renewals(self, request):
        """Manually generate renewals for a job card."""
        try:
            jobcard_id = request.data.get('jobcard_id')
            force_regenerate = request.data.get('force_regenerate', False)
            
            if not jobcard_id:
                return response.Response(
                    {'error': 'jobcard_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                jobcard = JobCard.objects.get(id=jobcard_id)
            except JobCard.DoesNotExist:
                return response.Response(
                    {'error': 'Job card not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            generated_renewals = RenewalService.generate_renewals_for_jobcard(jobcard, force_regenerate=force_regenerate)
            
            serializer = self.get_serializer(generated_renewals, many=True)
            
            return response.Response({
                'message': 'Renewals generated successfully',
                'renewals_count': len(generated_renewals),
                'renewals': serializer.data
            })
        except Exception as e:
            logger.error(f"Error generating renewals: {e}")
            return response.Response(
                {'error': 'Failed to generate renewals', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )




