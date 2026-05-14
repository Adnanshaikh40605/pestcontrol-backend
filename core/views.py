import logging
from django.http import JsonResponse
from django.core.exceptions import ValidationError
from django.db.models import Q, Count, Value, Avg
from django.db.models.functions import Coalesce
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, permissions, decorators, response, status, views
from rest_framework.decorators import action
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.views.decorators.vary import vary_on_headers
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiExample
from drf_spectacular.types import OpenApiTypes

from .models import Client, Inquiry, JobCard, Renewal, Technician, CRMInquiry, Feedback, ActivityLog, Reminder, Country, State, City, Location, Quotation, QuotationItem, QuotationScope, QuotationPaymentTerm, QuotationHistory
from .serializers import (
    ClientSerializer, InquirySerializer, JobCardSerializer, 
    RenewalSerializer, TechnicianSerializer, CRMInquirySerializer, 
    FeedbackSerializer, TechnicianPerformanceSerializer,
    StaffSerializer, ActivityLogSerializer, ReminderSerializer,
    CountrySerializer, StateSerializer, CitySerializer, LocationSerializer,
    QuotationSerializer, QuotationItemSerializer, QuotationHistorySerializer
)
from django.contrib.auth.models import User
from django.db.models import Q, Count, Sum, Avg, FloatField, ExpressionWrapper, F, Case, When, Value, IntegerField
from django.db.models.functions import Cast, Coalesce
from .services import ClientService, InquiryService, JobCardService, RenewalService, DashboardService, TechnicianService, CRMInquiryService

from django.db.models import Case, When, Value, IntegerField
import pytz
import logging
import re

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


from rest_framework.pagination import PageNumberPagination


class LargePagination(PageNumberPagination):
    """Pagination for master data endpoints (Countries, States, Cities, Locations)."""
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 2000


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
        logger.info(f"Creating {self.get_serializer_class().Meta.model.__name__}")
        return super().create(request, *args, **kwargs)


class CountryViewSet(BaseModelViewSet):
    queryset = Country.objects.all()
    serializer_class = CountrySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargePagination
    search_fields = ['name']
    filterset_fields = ['is_active']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @decorators.action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bulk create countries from a list of JSON objects."""
        data = request.data
        if not isinstance(data, list):
            return response.Response({"error": "Data must be a list of objects"}, status=status.HTTP_400_BAD_REQUEST)
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return response.Response({
                    "error": f"Item at index {i} must be a dictionary (object), but got {type(item).__name__}",
                    "received_value": item
                }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=data, many=True)
        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class StateViewSet(BaseModelViewSet):
    queryset = State.objects.all()
    serializer_class = StateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargePagination
    search_fields = ['name']
    filterset_fields = ['country', 'is_active']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @decorators.action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bulk create states from a list of JSON objects."""
        data = request.data
        if not isinstance(data, list):
            return response.Response({"error": "Data must be a list of objects"}, status=status.HTTP_400_BAD_REQUEST)
        
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return response.Response({
                    "error": f"Item at index {i} must be a dictionary (object), but got {type(item).__name__}",
                    "received_value": item
                }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=data, many=True)
        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CityViewSet(BaseModelViewSet):
    queryset = City.objects.all()
    serializer_class = CitySerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargePagination
    search_fields = ['name']
    filterset_fields = ['state', 'is_active']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @decorators.action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bulk create cities from a list of JSON objects."""
        data = request.data
        if not isinstance(data, list):
            return response.Response({"error": "Data must be a list of objects"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate each item is a dictionary
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return response.Response({
                    "error": f"Item at index {i} must be a dictionary (object), but got {type(item).__name__}",
                    "received_value": item
                }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=data, many=True)
        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LocationViewSet(BaseModelViewSet):
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = LargePagination
    search_fields = ['name']
    filterset_fields = ['city', 'is_active']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]

    @decorators.action(detail=False, methods=['post'], url_path='bulk-create')
    def bulk_create(self, request):
        """Bulk create locations from a list of JSON objects."""
        data = request.data
        if not isinstance(data, list):
            return response.Response({"error": "Data must be a list of objects"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate each item is a dictionary
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                return response.Response({
                    "error": f"Item at index {i} must be a dictionary (object), but got {type(item).__name__}",
                    "received_value": item
                }, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(data=data, many=True)
        if serializer.is_valid():
            serializer.save()
            return response.Response(serializer.data, status=status.HTTP_201_CREATED)
        return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
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
        summary="List Technicians",
        description="Retrieve a list of all technicians",
        tags=['Technician']
    ),
    create=extend_schema(
        summary="Create Technician",
        description="Add a new technician to the system",
        tags=['Technician']
    ),
    retrieve=extend_schema(
        summary="Get Technician Details",
        description="Retrieve specific technician details by ID",
        tags=['Technician']
    ),
    update=extend_schema(
        summary="Update Technician",
        description="Update all fields of an existing technician",
        tags=['Technician']
    ),
    partial_update=extend_schema(
        summary="Partial Update Technician",
        description="Update specific fields of an existing technician",
        tags=['Technician']
    ),
    destroy=extend_schema(
        summary="Delete Technician",
        description="Remove a technician from the system",
        tags=['Technician']
    )
)
class TechnicianViewSet(BaseModelViewSet):
    """
    ViewSet for managing technicians.
    Provides standard CRUD operations with searching and filtering.
    """
    queryset = Technician.objects.all()
    serializer_class = TechnicianSerializer
    search_fields = ['name', 'mobile', 'alternative_mobile']
    filterset_fields = ['is_active']
    ordering_fields = ['name', 'created_at']

    def get_queryset(self):
        return Technician.objects.annotate(
            active_jobs=Count('jobcards', filter=Q(jobcards__status__iexact='On Process'))
        )

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Helper action to get only active technicians for assignment dropdowns."""
        active_techs = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_techs, many=True)
        return response.Response(serializer.data)

    @action(detail=False, methods=['get'])
    def performance(self, request):
        """Get performance metrics for all technicians with filtering."""
        # Filters
        from_date = request.query_params.get('from')
        to_date = request.query_params.get('to')
        service_type = request.query_params.get('service_type')
        
        # Base filter for jobcards
        job_filter = Q()
        if from_date:
            job_filter &= Q(jobcards__schedule_datetime__date__gte=from_date)
        if to_date:
            job_filter &= Q(jobcards__schedule_datetime__date__lte=to_date)
        if service_type:
            job_filter &= Q(jobcards__service_type__icontains=service_type)

        # Performance annotation
        queryset = Technician.objects.annotate(
            assigned_count=Count('jobcards', filter=job_filter, distinct=True),
            completed_count=Count('jobcards', filter=job_filter & Q(jobcards__status='Done'), distinct=True),
            pending_count=Count('jobcards', filter=job_filter & Q(jobcards__status='Pending'), distinct=True),
            on_process_count=Count('jobcards', filter=job_filter & Q(jobcards__status='On Process'), distinct=True),
            service_calls_count=Count('jobcards', filter=job_filter & Q(jobcards__booking_type__in=[JobCard.BookingType.AMC_FOLLOWUP, JobCard.BookingType.SERVICE_CALL]), distinct=True),
            
            # Revenue calculation (casting CharField price to Float)
            # Using Coalesce to handle None values
            # Excluding free follow-ups/complaints from revenue
            total_revenue=Coalesce(
                Sum(
                    Cast('jobcards__price', FloatField()),
                    filter=job_filter & Q(
                        jobcards__status='Done',
                        jobcards__booking_type__in=[JobCard.BookingType.NEW_BOOKING, JobCard.BookingType.AMC_MAIN]
                    )
                ),
                Value(0.0, output_field=FloatField())
            ),
            
            avg_rating=Coalesce(Avg('jobcards__feedbacks__rating', filter=job_filter), Value(0.0, output_field=FloatField())),
            feedback_count=Count('jobcards__feedbacks', filter=job_filter, distinct=True)
        ).annotate(
            completion_rate=Case(
                When(assigned_count__gt=0, then=ExpressionWrapper(F('completed_count') * 100.0 / F('assigned_count'), output_field=FloatField())),
                default=Value(0.0, output_field=FloatField())
            )
        ).order_by('-completed_count')

        # Leaderboard summaries
        # Use a sub-query or simple aggregation for the stats
        stats_agg = queryset.aggregate(
            total_completed=Sum('completed_count'),
            total_revenue_sum=Sum('total_revenue'),
            overall_avg_rating=Avg('avg_rating'),
            total_pending=Sum('pending_count'),
            total_service_calls=Sum('service_calls_count')
        )

        stats = {
            'total_technicians': queryset.count(),
            'total_completed': stats_agg['total_completed'] or 0,
            'total_revenue': stats_agg['total_revenue_sum'] or 0,
            'avg_rating': stats_agg['overall_avg_rating'] or 0,
            'pending_jobs': stats_agg['total_pending'] or 0,
            'service_calls': stats_agg['total_service_calls'] or 0,
        }

        serializer = TechnicianPerformanceSerializer(queryset, many=True)
        
        return response.Response({
            'stats': stats,
            'technicians': serializer.data
        })

    @action(detail=True, methods=['get'])
    def performance_detail(self, request, pk=None):
        """Get detailed performance metrics for a specific technician."""
        technician = self.get_object()
        
        # We can reuse the same logic or provide more time-series data
        # For now, let's provide basic monthly breakdown
        current_year = timezone.now().year
        
        monthly_stats = []
        for month in range(1, 13):
            # Calculate stats for each month
            month_filter = Q(jobcards__schedule_datetime__year=current_year, jobcards__schedule_datetime__month=month)
            
            stats = technician.jobcards.filter(month_filter).aggregate(
                completed=Count('id', filter=Q(status='Done')),
                revenue=Coalesce(
                    Sum(
                        Cast('price', FloatField()), 
                        filter=Q(status='Done', booking_type__in=[JobCard.BookingType.NEW_BOOKING, JobCard.BookingType.AMC_MAIN])
                    ), 
                    Value(0.0, output_field=FloatField())
                ),
                avg_rating=Avg('feedbacks__rating')
            )
            
            monthly_stats.append({
                'month': month,
                'name': timezone.datetime(current_year, month, 1).strftime('%b'),
                **stats
            })
            
        # Recent feedbacks
        recent_feedbacks = Feedback.objects.filter(booking__technician=technician).order_by('-created_at')[:10]
        feedback_serializer = FeedbackSerializer(recent_feedbacks, many=True)
        
        return response.Response({
            'technician_name': technician.name,
            'monthly_stats': monthly_stats,
            'recent_feedbacks': feedback_serializer.data
        })


@extend_schema_view(
    list=extend_schema(
        summary="List CRM Inquiries",
        description="Retrieve a list of staff-created inquiries with searching and status filtering",
        tags=['CRM Inquiry']
    ),
    create=extend_schema(
        summary="Create CRM Inquiry",
        description="Add a new manual inquiry to the system",
        tags=['CRM Inquiry']
    ),
    convert=extend_schema(
        summary="Convert Inquiry to Booking",
        description="Transform a CRM inquiry into a live JobCard",
        tags=['CRM Inquiry']
    )
)
class CRMInquiryViewSet(BaseModelViewSet):
    """
    ViewSet for managing staff-created manual inquiries.
    Supports status transitions and conversion to live bookings.
    """
    queryset = CRMInquiry.objects.all()
    serializer_class = CRMInquirySerializer
    search_fields = ['name', 'mobile', 'location']
    filterset_fields = ['status', 'pest_type', 'inquiry_date']
    
    def perform_create(self, serializer):
        """Automatically set the creator of the inquiry."""
        instance = serializer.save(created_by=self.request.user)
        log_activity(self.request.user, "Created Inquiry", details=f"Customer: {instance.name}")

    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        """Action to trigger conversion from Inquiry to Booking."""
        try:
            job_card = CRMInquiryService.convert_to_booking(pk, user=request.user)
            log_activity(request.user, "Converted Inquiry to Booking", booking_id=job_card.code)
            return response.Response({
                'message': 'Successfully converted to booking',
                'job_card_id': job_card.id,
                'job_card_code': job_card.code
            }, status=status.HTTP_200_OK)
        except ValidationError as e:
            return response.Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error converting inquiry: {e}")
            return response.Response({'error': 'Conversion failed'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):
        instance = serializer.save()
        log_activity(self.request.user, "Updated Inquiry", details=f"Customer: {instance.name}")

    @action(detail=False, methods=['get'])
    def reminders(self, request):
        """Get active CRM inquiry reminders for the Reminders tab."""
        qs = CRMInquiry.objects.filter(
            reminder_date__isnull=False,
            is_reminder_done=False
        )

        # Apply date range filters
        date_from = request.query_params.get('from')
        date_to = request.query_params.get('to')

        if date_from or date_to:
            if date_from:
                qs = qs.filter(reminder_date__gte=date_from)
            if date_to:
                qs = qs.filter(reminder_date__lte=date_to)
        else:
            # Default: today + tomorrow only
            today = timezone.now().date()
            tomorrow = today + timezone.timedelta(days=1)
            qs = qs.filter(reminder_date__in=[today, tomorrow])

        qs = qs.order_by('reminder_date', 'reminder_time')
        serializer = self.get_serializer(qs, many=True)
        return response.Response({
            'count': qs.count(),
            'results': serializer.data
        })

    @action(detail=True, methods=['post'])
    def mark_reminder_done(self, request, pk=None):
        """Mark a CRM inquiry reminder as done."""
        try:
            inquiry = CRMInquiry.objects.get(id=pk)
            inquiry.is_reminder_done = True
            inquiry.save(update_fields=['is_reminder_done'])
            log_activity(request.user, "Marked Reminder Done", details=f"Inquiry: {inquiry.name}")
            return response.Response({'message': 'Reminder marked as done'})
        except CRMInquiry.DoesNotExist:
            return response.Response({'error': 'Inquiry not found'}, status=status.HTTP_404_NOT_FOUND)


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
            # Pass user if authenticated, otherwise None (public website inquiry)
            user = request.user if request.user.is_authenticated else None
            inquiry = InquiryService.create_inquiry(request.data, user=user)
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
            jobcard = InquiryService.convert_to_jobcard(pk, request.data, user=request.user)
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
                {'error': 'Internal server error', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """Mark all unread inquiries as read."""
        Inquiry.objects.filter(is_read=False).update(is_read=True)
        return response.Response({'status': 'success'})

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
    @action(detail=True, methods=['post'])
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
    @action(detail=True, methods=['get'])
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


class FeedbackViewSet(BaseModelViewSet):
    """
    ViewSet for managing customer feedback.
    Supports manual entry and WhatsApp link generation/submission.
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    filterset_fields = ['rating', 'feedback_type']
    search_fields = ['booking__code', 'booking__client__full_name', 'remark']
    ordering_fields = ['created_at', 'rating']

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request or self.action != 'list':
            return qs
        # Filter out placeholders (rating=0) from listing if needed, 
        # but for now we'll show all. Actually, rating=0 are just generated links not yet filled.
        return qs.exclude(rating=0, feedback_type='WhatsApp Link')

    def get_permissions(self):
        """Allow public access to submit and retrieve booking info for feedback."""
        action_name = getattr(self, 'action', None)
        if action_name in ['submit', 'booking_info']:
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_authenticators(self):
        """Disable auth for public actions."""
        action_name = getattr(self, 'action', None)
        if action_name in ['submit', 'booking_info']:
            return []
        return super().get_authenticators()

    @action(detail=False, methods=['post'], url_path='mark-all-read')
    def mark_all_read(self, request):
        """Mark all unread feedbacks as read."""
        Feedback.objects.filter(is_read=False).update(is_read=True)
        return response.Response({'status': 'success'})

    @action(detail=False, methods=['post'], url_path='generate')
    def generate(self, request):
        """Generate a secure feedback link for a booking."""
        booking_id = request.data.get('booking_id')
        if not booking_id:
            return response.Response({'error': 'booking_id is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            booking = JobCard.objects.get(id=booking_id)
            if booking.status != JobCard.JobStatus.DONE:
                return response.Response({'error': 'Feedback can only be generated for DONE bookings'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Check if feedback already exists for this booking
            feedback = Feedback.objects.filter(booking=booking).first()
            if not feedback:
                feedback = Feedback.objects.create(
                    booking=booking,
                    rating=0,  # Placeholder until submitted
                    feedback_type='WhatsApp Link'
                )
            elif feedback.rating > 0:
                # If feedback exists and is completed, return the existing one but maybe we should allow re-sending the link?
                # The user says "Do not allow multiple submissions".
                pass
            
            # Simplified link format as requested: https://pestcontrol99.com/feedback/BOOKING_ID
            link = f"https://pestcontrol99.com/feedback/{booking.id}"
            
            return response.Response({
                'booking_id': booking.id,
                'token': feedback.token,
                'link': link,
                'customer_name': booking.client.full_name
            })
        except JobCard.DoesNotExist:
            return response.Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='booking-info/(?P<booking_id>[^/.]+)')
    def booking_info(self, request, booking_id=None):
        """Get booking info for the public feedback page."""
        token = request.query_params.get('token')
        try:
            # 1. Try to find the Feedback record first
            feedback = None
            if token:
                feedback = Feedback.objects.filter(booking_id=booking_id, token=token).first()
            else:
                feedback = Feedback.objects.filter(booking_id=booking_id).first()
            
            # 2. If Feedback record exists, use its booking
            if feedback:
                booking = feedback.booking
                is_submitted = feedback.rating > 0
            else:
                # 3. If no Feedback record, look up JobCard directly (for direct ID links)
                booking = JobCard.objects.filter(id=booking_id).first()
                if not booking:
                    return response.Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
                
                # Ensure it's a DONE booking
                if booking.status != JobCard.JobStatus.DONE:
                    return response.Response({'error': 'Feedback link is only active for completed services'}, status=status.HTTP_400_BAD_REQUEST)
                
                is_submitted = False
            
            return response.Response({
                'booking_id': booking.code or booking.id,
                'service_name': booking.service_type,
                'service_date': booking.schedule_datetime,
                'technician_name': booking.technician.name if booking.technician else 'N/A',
                'is_submitted': is_submitted
            })
        except Exception as e:
            logger.error(f"Error in booking_info: {e}")
            return response.Response({'error': 'An error occurred fetching booking info'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['post'], url_path='submit')
    def submit(self, request):
        """Submit feedback from the public link."""
        booking_id = request.data.get('booking_id')
        token = request.data.get('token')
        rating = request.data.get('rating')
        remark = request.data.get('remark', '')
        behavior = request.data.get('technician_behavior')
        
        try:
            # 1. Find or Create Feedback record
            feedback = None
            if token:
                feedback = Feedback.objects.filter(booking_id=booking_id, token=token).first()
            else:
                feedback = Feedback.objects.filter(booking_id=booking_id).first()
            
            if not feedback:
                # Direct submission via ID - check booking exists and is DONE
                booking = JobCard.objects.filter(id=booking_id).first()
                if not booking:
                    return response.Response({'error': 'Booking not found'}, status=status.HTTP_404_NOT_FOUND)
                
                if booking.status != JobCard.JobStatus.DONE:
                    return response.Response({'error': 'Feedback can only be submitted for completed services'}, status=status.HTTP_400_BAD_REQUEST)
                
                feedback = Feedback.objects.create(
                    booking=booking,
                    rating=0,
                    feedback_type='Direct Link'
                )
            
            if feedback.rating > 0:
                 return response.Response({'error': 'Feedback already submitted'}, status=status.HTTP_400_BAD_REQUEST)
            
            feedback.rating = rating
            feedback.remark = remark
            feedback.technician_behavior = behavior
            feedback.save()
            
            return response.Response({'message': 'Thank you for your feedback ❤️'})
        except Exception as e:
            logger.error(f"Error in feedback submit: {e}")
            return response.Response({'error': 'Failed to submit feedback'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=['get'])
    def performance(self, request):
        """Get technician performance averages."""
        from django.db.models import Avg
        performance = Feedback.objects.filter(rating__gt=0).values(
            'booking__technician__name', 'booking__technician__id'
        ).annotate(
            average_rating=Avg('rating'),
            total_feedbacks=Count('id')
        ).order_by('-average_rating')
        
        # Format the response for easier consumption
        results = []
        for p in performance:
            if p['booking__technician__id']:
                results.append({
                    'technician_name': p['booking__technician__name'],
                    'technician_id': p['booking__technician__id'],
                    'average_rating': round(p['average_rating'], 1),
                    'total_feedbacks': p['total_feedbacks']
                })
        
        return response.Response(results)

    def perform_create(self, serializer):
        """Handle manual feedback entry."""
        booking = serializer.validated_data.get('booking')
        if booking.status != JobCard.JobStatus.DONE:
            raise ValidationError("Feedback can only be recorded for DONE bookings")
        
        # Check if a feedback record already exists for this booking
        # If it's a placeholder (WhatsApp Link with no rating), we update it.
        # Otherwise, we don't allow duplicate manual entries if one already exists.
        existing_feedback = Feedback.objects.filter(booking=booking).first()
        if existing_feedback:
            if existing_feedback.rating > 0:
                raise ValidationError("Feedback has already been recorded for this booking")
            
            # Update the existing placeholder
            serializer.instance = existing_feedback
        
        serializer.save(feedback_type='Manual')

    def create(self, request, *args, **kwargs):
        """Override to provide better error messages for 400 errors."""
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            logger.warning(f"Feedback validation failed: {serializer.errors}")
            return response.Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return response.Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


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
                description='Order results by: created_at, updated_at, schedule_datetime, status, payment_status, client__full_name, client__city, job_type, contract_duration (prefix with - for descending)'
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
                    'schedule_datetime': '2024-01-15T10:00:00Z',
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
    - created_at, updated_at, schedule_datetime, status, payment_status, 
      client__full_name, client__city, job_type, contract_duration
    """
    queryset = JobCard.objects.select_related('client').prefetch_related('renewals').all()
    serializer_class = JobCardSerializer
    filterset_fields = ['status', 'payment_status', 'client__city', 'client__mobile', 'job_type', 'commercial_type', 'service_category', 'contract_duration', 'is_paused', 'assigned_to']
    search_fields = ['code', 'client__full_name', 'client__mobile', 'service_type', 'assigned_to', 'area', 'commercial_type']
    ordering_fields = [
        'id', 'code', 'created_at', 'updated_at', 'schedule_datetime', 'status', 'payment_status', 
        'client__full_name', 'client__city', 'job_type', 'service_category', 'contract_duration'
    ]
    ordering = ['-created_at']  # Default: latest job cards first

    def get_queryset(self):
        qs = super().get_queryset()
        if not self.request or self.action != 'list':
            return qs
        
        # 1. Handle Booking Type Categories (Tabs)
        booking_type = self.request.query_params.get('booking_type', '').lower()
        logger.info(f"🔍 JobCard list requested with booking_type: {booking_type}")
        
        # Apply strict status filters based on booking_type
        if booking_type == 'pending':
            # Tab 1: Pending Booking - Strictly PENDING status and NOT a follow-up/service/complaint
            qs = qs.filter(
                status=JobCard.JobStatus.PENDING, 
                booking_type__in=[JobCard.BookingType.NEW_BOOKING, JobCard.BookingType.AMC_MAIN]
            )
        elif booking_type == 'on_process':
            # Tab 2: On Process - Strictly ON_PROCESS status only
            qs = qs.filter(status=JobCard.JobStatus.ON_PROCESS)
        elif booking_type == 'done':
            # Tab 3: Done - Strictly DONE status only
            qs = qs.filter(status=JobCard.JobStatus.DONE)
        elif booking_type == 'upcoming_renewals':
            # Tab 4: Upcoming Renewals - Today + Tomorrow only
            today = timezone.now().date()
            tomorrow = today + timezone.timedelta(days=1)
            qs = qs.filter(renewals__status='Due', renewals__due_date__in=[today, tomorrow]).distinct()
        elif booking_type == 'upcoming_services':
            # Tab 5: Upcoming Services - Only show services for the next 7 days
            tz = pytz.timezone('Asia/Kolkata')
            today = timezone.now().astimezone(tz).date()
            seven_days_later = today + timezone.timedelta(days=7)
            
            qs = qs.filter(
                booking_type__in=[JobCard.BookingType.AMC_FOLLOWUP, JobCard.BookingType.SERVICE_CALL],
                schedule_datetime__date__range=[today, seven_days_later]
            ).exclude(status__in=[JobCard.JobStatus.DONE, JobCard.JobStatus.CANCELLED])
        elif booking_type == 'cancelled':
            # Tab 6: Cancelled - Strictly CANCELLED status only
            qs = qs.filter(status=JobCard.JobStatus.CANCELLED)
        elif booking_type == 'reminders':
            # Tab 7: Reminders - Initially show all active reminders
            qs = qs.filter(reminder_date__isnull=False, is_reminder_done=False)
        elif booking_type == 'complaint_calls':
            # Tab 8: Complaint Calls - Strictly Complaint Booking Type
            qs = qs.filter(booking_type=JobCard.BookingType.COMPLAINT_CALL)
        elif booking_type == 'all':
            # No specific tab filter, show all
            pass
        
        # 2. Handle Sorting Priority for Pending + On Process
        if booking_type in ['pending', 'on_process']:
            # Sort by: Today bookings first, Tomorrow second, Future bookings after
            
            # Use Asia/Kolkata for comparison
            tz = pytz.timezone('Asia/Kolkata')
            now_local = timezone.now().astimezone(tz)
            today_date = now_local.date()
            tomorrow_date = today_date + timezone.timedelta(days=1)
            
            qs = qs.annotate(
                booking_priority=Case(
                    When(schedule_datetime__date=today_date, then=Value(1)),
                    When(schedule_datetime__date=tomorrow_date, then=Value(2)),
                    When(schedule_datetime__date__gt=tomorrow_date, then=Value(3)),
                    When(schedule_datetime__date__lt=today_date, then=Value(4)), # Past bookings
                    default=Value(5),
                    output_field=IntegerField(),
                )
            ).order_by('booking_priority', 'schedule_datetime')
        else:
            # Default ordering for other tabs or no booking_type
            qs = qs.order_by('-created_at')

        # 3. Handle Robust Search (Explicitly)
        # Check for both 'q' and 'search' parameters for frontend compatibility
        search_query = self.request.query_params.get('q', 
                      self.request.query_params.get('search', '')).strip()
        if search_query:
            # Search by Code (e.g. 0030 matches JC-0030), Client Name, and Mobile
            search_filter = Q(code__icontains=search_query) | \
                           Q(client__full_name__icontains=search_query) | \
                           Q(client__mobile__icontains=search_query)
            
            # Also allow searching by the numeric part only for Job Cards (JC-0001 -> 0001)
            if search_query.isdigit():
                search_filter |= Q(code__endswith=search_query)
            
            qs = qs.filter(search_filter)

        # 4. Handle Context-Aware Date Ranges
        date_from = self.request.query_params.get('from')
        date_to = self.request.query_params.get('to')
        
        if date_from or date_to:
            if booking_type == 'reminders':
                if date_from: qs = qs.filter(reminder_date__gte=date_from)
                if date_to: qs = qs.filter(reminder_date__lte=date_to)
            elif booking_type == 'upcoming_renewals':
                if date_from: qs = qs.filter(renewals__due_date__gte=date_from)
                if date_to: qs = qs.filter(renewals__due_date__lte=date_to)
            else:
                # Default for Pending, On Process, Done, Cancelled, Upcoming Services
                if date_from: qs = qs.filter(schedule_datetime__date__gte=date_from)
                if date_to: qs = qs.filter(schedule_datetime__date__lte=date_to)
        elif booking_type == 'reminders':
            # Default for Reminders tab if no date filter: Today + Tomorrow only (staff focus)
            today = timezone.now().date()
            tomorrow = today + timezone.timedelta(days=1)
            qs = qs.filter(reminder_date__in=[today, tomorrow])
            
        final_qs = qs.distinct()
        logger.info(f"✅ JobCard list returning {final_qs.count()} records for booking_type: {booking_type}")
        return final_qs
    
    def list(self, request, *args, **kwargs):
        """List job cards with enhanced error handling."""
        try:
            return super().list(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"Error listing job cards: {e}", exc_info=True)
            return response.Response(
                {
                    'error': 'Failed to retrieve job cards',
                    'message': 'An error occurred while fetching job cards. Please try again or contact support.',
                    'details': str(e) if request.user.is_staff else 'Internal server error'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        """Quickly assign a technician and update status to On Process."""
        try:
            instance = self.get_object()
            technician_id = request.data.get('technician_id')
            
            if not technician_id:
                return response.Response(
                    {'error': 'technician_id is required'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from .models import Technician
            try:
                technician = Technician.objects.get(id=technician_id)
            except Technician.DoesNotExist:
                return response.Response(
                    {'error': 'Technician not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Atomic update
            instance.technician = technician
            instance.assigned_to = technician.name
            instance.status = JobCard.JobStatus.ON_PROCESS
            instance.removal_remarks = ''  # Clear removal remarks when re-assigned
            instance.save()
            
            serializer = self.get_serializer(instance)
            return response.Response(serializer.data)
            
        except Exception as e:
            logger.error(f"Error in JobCardViewSet.assign: {e}", exc_info=True)
            return response.Response(
                {'error': 'Failed to assign technician', 'details': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
            
            jobcard = JobCardService.create_jobcard(request.data, user=request.user)
            
            # Automatically generate renewals for the job card if conditions are met
            try:
                generated_renewals = RenewalService.generate_renewals_for_jobcard(jobcard, user=request.user)
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
            
            log_activity(request.user, "Created Booking", booking_id=jobcard.code)
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
        
        # Ensure request.data is mutable for our fallback logic
        if hasattr(request.data, '_mutable'):
            request.data._mutable = True
            
        logger.info(f"🚀 Updating JobCard {instance.code} (ID: {instance.id})")
        logger.info(f"Incoming Price: {request.data.get('price')} (Current: {instance.price})")
        
        # Store original values to check for changes
        original_schedule_datetime = instance.schedule_datetime
        original_next_service_date = instance.next_service_date
        original_contract_duration = instance.contract_duration
        original_job_type = instance.job_type
        
        # Handle client updates if client_data is provided
        if 'client_data' in request.data and request.data['client_data']:
            client_data = request.data['client_data']
            client = instance.client
            update_fields = []
            
            # Only update email, city, address, notes - NOT full_name
            for field in ['email', 'city', 'address', 'notes']:
                if field in client_data and client_data.get(field) is not None:
                    new_val = str(client_data.get(field)).strip()
                    current_val = str(getattr(client, field) or '').strip()
                    if new_val != current_val:
                        setattr(client, field, new_val)
                        if field not in update_fields: update_fields.append(field)
            
            if update_fields:
                client.save(update_fields=update_fields)
                logger.info(f"✅ Updated client {client.id} fields: {', '.join(update_fields)}")
        
        # Handle client_address fallback if not provided
        request_client_address = request.data.get('client_address', '').strip() if request.data.get('client_address') else ''
        if not request_client_address and instance.client and instance.client.address:
            if not (instance.client_address or '').strip():
                # Update it in request.data so serializer picks it up
                request.data['client_address'] = instance.client.address
                logger.info(f"📍 Auto-filling client_address from client profile")
        
        # Perform the update
        try:
            # Track status changes before update
            old_status = instance.status
            new_status = request.data.get('status')
            
            response_obj = super().update(request, *args, partial=partial, **kwargs)
            
            # Reload instance to get updated values from DB
            instance.refresh_from_db()
            
            # Track who changed status
            if new_status and new_status != old_status:
                if new_status == JobCard.JobStatus.ON_PROCESS:
                    instance.on_process_by = request.user
                    instance.save(update_fields=['on_process_by'])
                elif new_status == JobCard.JobStatus.DONE:
                    instance.done_by = request.user
                    instance.save(update_fields=['done_by'])
            
            logger.info(f"✅ JobCard {instance.code} updated. New Price in DB: {instance.price}")
            
            # 1. Handle automation when job is marked DONE
            if instance.status == JobCard.JobStatus.DONE:
                JobCardService.handle_job_completion(instance)
                log_activity(request.user, "Completed Booking", booking_id=instance.code, details=f"Payment: {instance.payment_mode}")
            else:
                log_activity(request.user, "Updated Booking", booking_id=instance.code)

            # 2. Re-calculate next_service_date if missing and relevant fields changed
            if not request.data.get('next_service_date'):
                needs_calc = (
                    not instance.next_service_date or
                    instance.schedule_datetime != original_schedule_datetime
                )
                if needs_calc:
                    next_date, max_cycle = JobCardService.calculate_next_service_date(instance)
                    if next_date != instance.next_service_date or max_cycle != instance.max_cycle:
                        instance.next_service_date = next_date
                        instance.max_cycle = max_cycle
                        instance.save(update_fields=['next_service_date', 'max_cycle'])
            
            # 3. Generate renewals if relevant fields changed
            renewal_fields_changed = (
                instance.next_service_date != original_next_service_date or
                instance.contract_duration != original_contract_duration or
                instance.job_type != original_job_type
            )
            
            if renewal_fields_changed:
                try:
                    RenewalService.generate_renewals_for_jobcard(instance, user=request.user)
                except Exception as e:
                    logger.warning(f"Failed to generate renewals: {e}")
            
            return response_obj
            
        except Exception as e:
            logger.error(f"❌ Error updating job card {instance.code}: {e}", exc_info=True)
            raise e

    
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
                log_activity(request.user, f"{status_text.capitalize()} Booking", booking_id=pk)
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

    @extend_schema(
        summary="Get Indian States and Cities",
        description="Get a list of Indian states and their major cities for Pan-India support.",
        responses={
            200: {
                'type': 'object',
                'description': 'Mapping of states to lists of cities'
            }
        },
        tags=['Locations']
    )
    @decorators.action(detail=False, methods=['get'], url_path='locations', permission_classes=[])
    def get_locations(self, request):
        """Action to provide states and cities data."""
        try:
            from .location_data import INDIAN_LOCATIONS
            return response.Response(INDIAN_LOCATIONS)
        except ImportError:
            return response.Response(
                {'error': 'Location data not found'},
                status=status.HTTP_404_NOT_FOUND
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
            # Get date range from query params
            from_date = request.query_params.get('from')
            to_date = request.query_params.get('to')
            
            # Get dashboard statistics from service
            stats = DashboardService.get_dashboard_statistics(from_date=from_date, to_date=to_date)
            
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

    @action(detail=False, methods=['get'], url_path='counts')
    def counts(self, request):
        """
        Get lightweight counts for sidebar badges.
        """
        try:
            counts = DashboardService.get_dashboard_counts()
            return response.Response(counts, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving dashboard counts: {e}")
            return response.Response(
                {'error': 'Failed to retrieve dashboard counts'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=['get'], url_path='performance')
    def performance(self, request):
        """
        Get staff performance report.
        """
        try:
            period = request.query_params.get('period', 'today')
            performance_data = DashboardService.get_staff_performance(period)
            return response.Response(performance_data, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error retrieving staff performance: {e}")
            return response.Response(
                {'error': 'Failed to retrieve staff performance report'},
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
    filterset_fields = ['status', 'urgency_level', 'renewal_type', 'jobcard__service_category', 'jobcard__assigned_to']
    search_fields = ['jobcard__code', 'jobcard__client__full_name', 'jobcard__client__mobile', 'jobcard__assigned_to']
    ordering_fields = ['created_at', 'updated_at', 'due_date', 'status', 'urgency_level']
    ordering = ['due_date']  # Default: sort by due date (earliest first for renewals)

    def get_queryset(self):
        """Enhanced queryset with custom filtering for pause functionality and urgency levels."""
        qs = super().get_queryset()
        if not self.request or self.action != 'list':
            return qs
        
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
            renewal = RenewalService.create_renewal(request.data, user=request.user)
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


class GlobalSearchView(views.APIView):
    """
    Search globally across Clients, JobCards, and CRM Inquiries.
    """
    permission_classes = [permissions.IsAuthenticated]
    
    @extend_schema(
        summary="Global search across CRM",
        description="Search by name, mobile, booking code, or address across Clients and Job Cards.",
        parameters=[
            OpenApiParameter(name="q", description="Search query string", required=True, type=str)
        ],
        tags=['Search']
    )
    def get(self, request):
        query = request.query_params.get('q', '').strip()
        if not query:
            return response.Response([], status=status.HTTP_200_OK)

        results = []

        # 1. Search Clients
        clients = Client.objects.filter(
            Q(full_name__icontains=query) | 
            Q(mobile__icontains=query)
        ).distinct()[:10]
        
        for client in clients:
            results.append({
                'id': client.id,
                'title': client.full_name,
                'subtitle': client.mobile,
                'type': 'Customer',
                'link': f'/clients/{client.id}'
            })

        # 2. Search JobCards (Bookings)
        jobcards = JobCard.objects.select_related('client').filter(
            Q(code__icontains=query) |
            Q(client__full_name__icontains=query) |
            Q(client__mobile__icontains=query) |
            Q(client_address__icontains=query)
        ).distinct()[:10]

        for jc in jobcards:
            results.append({
                'id': jc.id,
                'title': f"Booking #{jc.code}",
                'subtitle': f"{jc.client.full_name} - {jc.service_type}",
                'type': 'Booking',
                'link': f'/jobcards/{jc.id}',
                'client_id': jc.client_id
            })
            
        # 3. Search CRM Inquiries
        inquiries = CRMInquiry.objects.filter(
            Q(name__icontains=query) |
            Q(mobile__icontains=query)
        ).distinct()[:5]
        
        for inc in inquiries:
            results.append({
                'id': inc.id,
                'title': f"Inquiry: {inc.name}",
                'subtitle': f"{inc.mobile} - {inc.pest_type}",
                'type': 'Inquiry',
                'link': f'/crm-inquiries/{inc.id}'
            })

        # 4. Search Reminders
        reminders = Reminder.objects.filter(
            Q(customer_name__icontains=query) |
            Q(mobile_number__icontains=query) |
            Q(note__icontains=query)
        ).distinct()[:5]

        for rem in reminders:
            results.append({
                'id': rem.id,
                'title': f"Reminder: {rem.customer_name}",
                'subtitle': f"{rem.mobile_number} - {rem.note[:30]}...",
                'type': 'Reminder',
                'link': f'/jobcards?tab=reminders'
            })

        return response.Response(results)


class CustomerHistoryView(views.APIView):
    """
    Get complete history for a specific customer.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get customer history",
        description="Returns all bookings, feedbacks, reminders, and revenue summary for a specific client.",
        tags=['Search']
    )
    def get(self, request, client_id):
        try:
            # Fetch client with optimized related data
            client = Client.objects.prefetch_related(
                'jobcards', 
                'jobcards__feedbacks',
                'jobcards__technician'
            ).get(id=client_id)
        except Client.DoesNotExist:
            return response.Response({'error': 'Client not found'}, status=status.HTTP_404_NOT_FOUND)

        # 1. Booking History
        jobcards = client.jobcards.all().order_by('-schedule_datetime', '-created_at')
        jobcards_data = JobCardSerializer(jobcards, many=True).data

        # 2. Feedback History
        feedbacks = Feedback.objects.filter(booking__client=client).order_by('-created_at')
        feedback_data = FeedbackSerializer(feedbacks, many=True).data

        # 3. Revenue Summary
        total_revenue = 0
        amc_revenue = 0
        paid_services = 0
        
        for jc in jobcards:
            # Only count revenue for main bookings, exclude free follow-ups and complaints
            if jc.included_in_amc or jc.is_complaint_call or jc.is_followup_visit:
                if jc.payment_status == JobCard.PaymentStatus.PAID:
                    paid_services += 1
                continue

            try:
                price_str = str(jc.price).replace('₹', '').replace(',', '').strip()
                p = float(price_str) if price_str else 0
                total_revenue += p
                if jc.service_category == JobCard.ServiceCategory.AMC:
                    amc_revenue += p
                if jc.payment_status == JobCard.PaymentStatus.PAID:
                    paid_services += 1
            except ValueError:
                pass

        # 4. Reminders
        reminders = []
        for jc in jobcards:
            if jc.reminder_date:
                reminders.append({
                    'id': jc.id,
                    'type': 'Booking Reminder',
                    'date': jc.reminder_date,
                    'time': jc.reminder_time,
                    'note': jc.reminder_note,
                    'status': 'Done' if jc.is_reminder_done else 'Pending'
                })
        
        # Also include inquiries with the same mobile
        crm_inquiries = CRMInquiry.objects.filter(mobile=client.mobile)
        for inc in crm_inquiries:
            if inc.reminder_date:
                reminders.append({
                    'id': inc.id,
                    'type': 'Inquiry Reminder',
                    'date': inc.reminder_date,
                    'time': inc.reminder_time,
                    'note': inc.reminder_note,
                    'status': 'Done' if inc.is_reminder_done else 'Pending'
                })

        # Also include new unified reminders
        new_reminders = Reminder.objects.filter(mobile_number=client.mobile)
        for rem in new_reminders:
            reminders.append({
                'id': rem.id,
                'type': f"{rem.inquiry_type.upper()} Reminder",
                'date': rem.reminder_date,
                'time': rem.reminder_time,
                'note': rem.note,
                'status': rem.status.capitalize()
            })

        # 5. Technician History
        technicians = set()
        for jc in jobcards:
            if jc.technician:
                technicians.add(jc.technician.name)
            elif jc.assigned_to:
                technicians.add(jc.assigned_to)

        # 6. Upcoming Services
        upcoming = jobcards.filter(
            status__in=[JobCard.JobStatus.PENDING, JobCard.JobStatus.ON_PROCESS],
            schedule_datetime__gte=timezone.now()
        )

        return response.Response({
            'client': ClientSerializer(client).data,
            'stats': {
                'total_bookings': jobcards.count(),
                'total_revenue': total_revenue,
                'amc_revenue': amc_revenue,
                'paid_services': paid_services,
                'first_booking': jobcards.last().schedule_datetime if jobcards.exists() else None,
                'last_service': jobcards.first().schedule_datetime if jobcards.exists() else None,
            },
            'bookings': jobcards_data,
            'feedbacks': feedback_data,
            'reminders': sorted(reminders, key=lambda x: str(x['date']), reverse=True),
            'technicians': list(technicians),
            'upcoming': JobCardSerializer(upcoming, many=True).data
        })


class ComplaintViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling Complaint Calls.
    """
    queryset = JobCard.objects.filter(booking_type=JobCard.BookingType.COMPLAINT_CALL)
    serializer_class = JobCardSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['complaint_status', 'priority', 'technician']
    search_fields = ['client__full_name', 'client__mobile', 'code', 'complaint_note']

    @extend_schema(
        summary="Create a complaint from an existing booking",
        request={
            'type': 'object',
            'properties': {
                'parent_booking_id': {'type': 'integer'},
                'complaint_type': {'type': 'string'},
                'complaint_note': {'type': 'string'},
                'priority': {'type': 'string'},
                'revisit_date': {'type': 'string', 'format': 'date'},
                'technician_id': {'type': 'integer'}
            },
            'required': ['parent_booking_id', 'complaint_type']
        },
        responses={201: JobCardSerializer},
        tags=['Complaints']
    )
    @decorators.action(detail=False, methods=['post'])
    def create_complaint(self, request):
        parent_id = request.data.get('parent_booking_id')
        try:
            parent = JobCard.objects.get(id=parent_id)
        except JobCard.DoesNotExist:
            return response.Response({'error': 'Parent booking not found'}, status=status.HTTP_404_NOT_FOUND)

        # Create new complaint booking by copying parent details
        complaint = JobCard.objects.create(
            client=parent.client,
            is_complaint_call=True,
            complaint_parent_booking=parent,
            service_type=parent.service_type,
            client_address=parent.client_address,
            city=parent.city,
            state=parent.state,
            job_type=parent.job_type,
            commercial_type=parent.commercial_type,
            service_category=parent.service_category,
            complaint_type=request.data.get('complaint_type'),
            complaint_note=request.data.get('complaint_note', ''),
            priority=request.data.get('priority', 'Medium'),
            schedule_datetime=request.data.get('revisit_date'),
            technician_id=request.data.get('technician_id'),
            status=JobCard.JobStatus.PENDING,
            complaint_status=JobCard.ComplaintStatus.OPEN,
            booking_type=JobCard.BookingType.COMPLAINT_CALL,
            price="0"  # Complaint calls are usually free
        )

        serializer = self.get_serializer(complaint)
        log_activity(request.user, "Created Complaint", booking_id=complaint.code, details=f"Parent Booking: {parent.code}")
        return response.Response(serializer.data, status=status.HTTP_201_CREATED)


class ComplaintAnalyticsView(views.APIView):
    """
    Get analytics for complaints.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get complaint analytics",
        tags=['Complaints']
    )
    def get(self, request):
        total = JobCard.objects.filter(booking_type=JobCard.BookingType.COMPLAINT_CALL).count()
        resolved_statuses = [JobCard.ComplaintStatus.RESOLVED, JobCard.ComplaintStatus.CLOSED]
        resolved = JobCard.objects.filter(booking_type=JobCard.BookingType.COMPLAINT_CALL, complaint_status__in=resolved_statuses).count()
        unresolved = JobCard.objects.filter(booking_type=JobCard.BookingType.COMPLAINT_CALL).exclude(complaint_status__in=resolved_statuses).count()
        high_priority = JobCard.objects.filter(booking_type=JobCard.BookingType.COMPLAINT_CALL, priority=JobCard.Priority.HIGH).exclude(complaint_status__in=resolved_statuses).count()
        
        # Technician complaint rate (complaints per technician)
        tech_stats = JobCard.objects.filter(booking_type=JobCard.BookingType.COMPLAINT_CALL, technician__isnull=False).values('technician__name').annotate(
            count=Count('id')
        ).order_by('-count')

        return response.Response({
            'total_count': total,
            'resolved_count': resolved,
            'unresolved_count': unresolved,
            'high_priority_count': high_priority,
            'resolution_rate': round((resolved / total * 100), 1) if total > 0 else 0,
            'technician_stats': list(tech_stats)
        })


class ReminderViewSet(viewsets.ModelViewSet):
    """
    ViewSet for handling Reminders.
    """
    queryset = Reminder.objects.all()
    serializer_class = ReminderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'inquiry_type']
    search_fields = ['customer_name', 'mobile_number', 'note']
    ordering_fields = ['reminder_date', 'reminder_time', 'created_at']
    ordering = ['reminder_date', 'reminder_time']

    def perform_create(self, serializer):
        inquiry_type = serializer.validated_data.get('inquiry_type')
        inquiry_id = serializer.validated_data.get('inquiry_id')
        reminder_date = serializer.validated_data.get('reminder_date')
        
        # Check for existing pending reminder for same inquiry and date
        existing = Reminder.objects.filter(
            inquiry_type=inquiry_type,
            inquiry_id=inquiry_id,
            reminder_date=reminder_date,
            status=Reminder.ReminderStatus.PENDING
        ).exists()
        
        if existing:
            raise ValidationError("A pending reminder already exists for this inquiry on this date.")
            
        serializer.save(created_by=self.request.user)
        log_activity(self.request.user, "Created Reminder", details=f"Customer: {serializer.validated_data.get('customer_name')}")

    @decorators.action(detail=True, methods=['post'])
    def mark_complete(self, request, pk=None):
        reminder = self.get_object()
        reminder.status = Reminder.ReminderStatus.COMPLETED
        reminder.save()
        log_activity(request.user, "Completed Reminder", details=f"Customer: {reminder.customer_name}")
        return response.Response({'status': 'Reminder marked as completed'})


class QuotationViewSet(BaseModelViewSet):
    queryset = Quotation.objects.all()
    serializer_class = QuotationSerializer
    search_fields = ['quotation_no', 'customer_name', 'mobile', 'company_name']
    filterset_fields = ['status', 'quotation_type', 'is_amc']

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get summary statistics for the quotation dashboard."""
        qs = self.get_queryset()
        stats = {
            'total': qs.count(),
            'pending': qs.filter(status='Sent').count(),
            'approved': qs.filter(status='Approved').count(),
            'converted': qs.filter(status='Converted').count(),
            'revenue': qs.filter(status='Converted').aggregate(total=Sum('grand_total'))['total'] or 0
        }
        return response.Response(stats)

    @action(detail=True, methods=['post'])
    def convert_to_booking(self, request, pk=None):
        """Convert an approved quotation into a booking (JobCard)."""
        quotation = self.get_object()
        
        if quotation.status != 'Approved' and quotation.status != 'Sent':
             # For flexibility, we allow 'Sent' too, but ideally 'Approved'
             pass

        try:
            # 1. Create or Get Client
            client, created = Client.objects.get_or_create(
                mobile=quotation.mobile,
                defaults={
                    'full_name': quotation.customer_name,
                    'email': quotation.email,
                    'address': quotation.address,
                    'city': quotation.city,
                    'state': quotation.state,
                }
            )

            # 2. Create Main Job Card
            main_job = JobCard.objects.create(
                client=client,
                service_type=", ".join([item.service_name for item in quotation.items.all()]),
                price=str(quotation.grand_total),
                service_category=JobCard.ServiceCategory.AMC if quotation.is_amc else JobCard.ServiceCategory.ONE_TIME,
                client_address=quotation.address,
                city=quotation.city,
                state=quotation.state,
                status=JobCard.JobStatus.PENDING,
                created_by=request.user,
                is_amc_main_booking=quotation.is_amc,
                max_cycle=quotation.visit_count if quotation.is_amc else 1,
                service_cycle=1,
                extra_notes=f"Converted from Quotation {quotation.quotation_no}. {quotation.notes or ''}"
            )

            # 3. If AMC, create follow-up visits (placeholder bookings)
            if quotation.is_amc and quotation.visit_count > 1:
                for i in range(2, quotation.visit_count + 1):
                    JobCard.objects.create(
                        client=client,
                        service_type=main_job.service_type,
                        price="0", # Follow-ups have no revenue
                        service_category=JobCard.ServiceCategory.AMC,
                        client_address=quotation.address,
                        city=quotation.city,
                        state=quotation.state,
                        status=JobCard.JobStatus.PENDING,
                        created_by=request.user,
                        is_followup_visit=True,
                        included_in_amc=True,
                        parent_job=main_job,
                        service_cycle=i,
                        max_cycle=quotation.visit_count
                    )

            # 4. Update Quotation Status
            quotation.status = Quotation.QuotationStatus.CONVERTED
            quotation.save()

            # 5. Log History
            QuotationHistory.objects.create(
                quotation=quotation,
                action="Converted to Booking",
                details=f"Quotation converted to JobCard {main_job.code} by {request.user.username}",
                performed_by=request.user
            )

            log_activity(request.user, "Converted Quotation to Booking", booking_id=main_job.code)

            return response.Response({
                'message': 'Successfully converted to booking',
                'booking_id': main_job.id,
                'booking_code': main_job.code
            })

        except Exception as e:
            logger.error(f"Error converting quotation: {e}")
            return response.Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def log_activity(user, action, booking_id=None, details=None):
    """Utility to log staff activities."""
    if not user or user.is_anonymous:
        return
    try:
        ActivityLog.objects.create(
            user=user,
            action=action,
            booking_id=booking_id,
            details=details
        )
    except Exception as e:
        print(f"Error logging activity: {e}")


class IsSuperAdmin(permissions.BasePermission):
    """
    Allows access only to superusers.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)


class StaffViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Staff users.
    """
    queryset = User.objects.filter(is_staff=True).order_by('-date_joined')
    serializer_class = StaffSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    search_fields = ['first_name', 'username']

    @decorators.action(detail=True, methods=['post'])
    def reset_password(self, request, pk=None):
        user = self.get_object()
        new_password = request.data.get('password')
        if not new_password:
            return response.Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        log_activity(request.user, f"Reset password for staff: {user.first_name}")
        return response.Response({'status': 'Password reset successfully'})


class ActivityLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for viewing Activity Logs.
    """
    queryset = ActivityLog.objects.all().order_by('-created_at')
    serializer_class = ActivityLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['user', 'action']
    search_fields = ['action', 'booking_id', 'details', 'user__first_name']






