from django.shortcuts import get_object_or_404
from django.db.models import Q, Count, Sum
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from datetime import date, timedelta
import logging

from .models import Client, Inquiry, JobCard, Renewal
from .serializers import ClientSerializer, InquirySerializer, JobCardSerializer, RenewalSerializer
from .permissions import IsAdminUserOrReadOnly, IsOwnerOrAdmin, AllowWebhookPost

logger = logging.getLogger(__name__)


class ClientViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing clients.
    
    Provides CRUD operations for client management with filtering and search capabilities.
    """
    queryset = Client.objects.select_related().all()
    serializer_class = ClientSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['city', 'is_active']
    search_fields = ['full_name', 'mobile', 'email']
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]
    
    def get_queryset(self):
        """Return filtered queryset based on request parameters."""
        queryset = super().get_queryset()
        
        # Filter by active status if specified
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    def perform_create(self, serializer):
        """Log client creation and save with validation."""
        try:
            client = serializer.save()
            logger.info(f"Client created: {client.full_name} ({client.mobile})")
        except Exception as e:
            logger.error(f"Error creating client: {str(e)}")
            raise
    
    def perform_update(self, serializer):
        """Log client updates and save with validation."""
        try:
            client = serializer.save()
            logger.info(f"Client updated: {client.full_name} ({client.mobile})")
        except Exception as e:
            logger.error(f"Error updating client: {str(e)}")
            raise


class InquiryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing inquiries.
    
    Provides CRUD operations for inquiry management and conversion to job cards.
    """
    queryset = Inquiry.objects.select_related().all()
    serializer_class = InquirySerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'city']
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]
    
    def get_permissions(self):
        """Return appropriate permissions based on action."""
        if self.action == 'create' and 'webhook' in self.request.path:
            return [AllowWebhookPost()]
        return super().get_permissions()
    
    def get_queryset(self):
        """Return filtered queryset based on request parameters."""
        queryset = super().get_queryset()
        
        # Filter by date range if specified
        from_date = self.request.query_params.get('from_date', None)
        to_date = self.request.query_params.get('to_date', None)
        
        if from_date:
            queryset = queryset.filter(created_at__date__gte=from_date)
        if to_date:
            queryset = queryset.filter(created_at__date__lte=to_date)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        """
        Convert an inquiry to a job card.
        
        Creates a new client (if doesn't exist) and job card from the inquiry.
        """
        try:
            inquiry = self.get_object()
            
            # Create a new client if doesn't exist
            client, created = Client.objects.get_or_create(
                mobile=inquiry.mobile,
                defaults={
                    'full_name': inquiry.name,
                    'email': inquiry.email,
                    'city': inquiry.city,
                }
            )
            
            if created:
                logger.info(f"New client created from inquiry: {client.full_name}")
            
            # Validate required fields for job card creation
            schedule_date = request.data.get('schedule_date')
            if not schedule_date:
                return Response(
                    {'error': 'schedule_date is required'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Create a new job card
            job_card = JobCard.objects.create(
                client=client,
                service_type=inquiry.service_interest,
                schedule_date=schedule_date,
                technician_name=request.data.get('technician_name', ''),
                price_subtotal=request.data.get('price_subtotal', 0),
                tax_percent=request.data.get('tax_percent', 18),
                notes=inquiry.message
            )
            
            # Update inquiry status
            inquiry.status = 'Converted'
            inquiry.save()
            
            logger.info(f"Inquiry {inquiry.id} converted to job card {job_card.code}")
            
            return Response({
                'job_card_id': job_card.id,
                'job_card_code': job_card.code,
                'client_id': client.id,
                'message': 'Inquiry successfully converted to job card'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Error converting inquiry {pk}: {str(e)}")
            return Response(
                {'error': 'Failed to convert inquiry'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class JobCardViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing job cards.
    
    Provides CRUD operations for job card management with advanced filtering.
    """
    queryset = JobCard.objects.select_related('client').all()
    serializer_class = JobCardSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'payment_status']
    search_fields = ['code', 'client__full_name', 'client__mobile', 'service_type']
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]
    
    def get_queryset(self):
        """Return filtered queryset based on request parameters."""
        queryset = super().get_queryset()
        
        # Filter by city
        city = self.request.query_params.get('city', None)
        if city:
            queryset = queryset.filter(client__city__iexact=city)
        
        # Filter by date range
        from_date = self.request.query_params.get('from', None)
        to_date = self.request.query_params.get('to', None)
        
        if from_date:
            queryset = queryset.filter(schedule_date__gte=from_date)
        if to_date:
            queryset = queryset.filter(schedule_date__lte=to_date)
        
        # Filter by status
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Get job card statistics."""
        try:
            total_jobs = JobCard.objects.count()
            completed_jobs = JobCard.objects.filter(status='Done').count()
            pending_jobs = JobCard.objects.filter(status__in=['Enquiry', 'WIP']).count()
            total_revenue = JobCard.objects.filter(payment_status='Paid').aggregate(
                total=Sum('grand_total')
            )['total'] or 0
            
            return Response({
                'total_jobs': total_jobs,
                'completed_jobs': completed_jobs,
                'pending_jobs': pending_jobs,
                'total_revenue': total_revenue,
                'completion_rate': (completed_jobs / total_jobs * 100) if total_jobs > 0 else 0
            })
        except Exception as e:
            logger.error(f"Error getting job card statistics: {str(e)}")
            return Response(
                {'error': 'Failed to get statistics'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RenewalViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing renewals.
    
    Provides CRUD operations for renewal management with upcoming renewal filtering.
    """
    queryset = Renewal.objects.select_related('jobcard__client').all()
    serializer_class = RenewalSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'due_date']
    permission_classes = [IsAuthenticated, IsAdminUserOrReadOnly]
    
    def get_queryset(self):
        """Return filtered queryset based on request parameters."""
        queryset = super().get_queryset()
        
        # Filter renewals due today, overdue, or in the next 30 days
        upcoming = self.request.query_params.get('upcoming', None)
        if upcoming:
            today = date.today()
            thirty_days_later = today + timedelta(days=30)
            queryset = queryset.filter(
                due_date__lte=thirty_days_later, 
                status='Due'
            ).order_by('due_date')
        
        # Filter by overdue renewals
        overdue = self.request.query_params.get('overdue', None)
        if overdue:
            today = date.today()
            queryset = queryset.filter(due_date__lt=today, status='Due')
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def upcoming_summary(self, request):
        """Get summary of upcoming renewals."""
        try:
            today = date.today()
            week_later = today + timedelta(days=7)
            month_later = today + timedelta(days=30)
            
            due_this_week = Renewal.objects.filter(
                due_date__gte=today,
                due_date__lte=week_later,
                status='Due'
            ).count()
            
            due_this_month = Renewal.objects.filter(
                due_date__gte=today,
                due_date__lte=month_later,
                status='Due'
            ).count()
            
            overdue = Renewal.objects.filter(
                due_date__lt=today,
                status='Due'
            ).count()
            
            return Response({
                'due_this_week': due_this_week,
                'due_this_month': due_this_month,
                'overdue': overdue
            })
        except Exception as e:
            logger.error(f"Error getting renewal summary: {str(e)}")
            return Response(
                {'error': 'Failed to get renewal summary'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
