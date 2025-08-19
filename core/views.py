from django.http import JsonResponse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets, filters, permissions, decorators, response
from rest_framework.authentication import SessionAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from .models import Client, Inquiry, JobCard, Renewal
from .serializers import ClientSerializer, InquirySerializer, JobCardSerializer, RenewalSerializer


def health_check(request):
    return JsonResponse({'status': 'ok'})


class DefaultPermission(permissions.IsAuthenticated):
    pass


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all().order_by('-created_at')
    serializer_class = ClientSerializer
    permission_classes = [DefaultPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['city', 'is_active']
    search_fields = ['full_name', 'mobile', 'email']


class InquiryViewSet(viewsets.ModelViewSet):
    queryset = Inquiry.objects.all().order_by('-created_at')
    serializer_class = InquirySerializer
    permission_classes = [DefaultPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'city']
    search_fields = ['name', 'mobile', 'email', 'service_interest']

    def get_permissions(self):
        # Allow unauthenticated public creation of inquiries
        action = getattr(self, 'action', None)
        if action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_authenticators(self):
        # Do not enforce Session/JWT auth on public create endpoint (avoids CSRF)
        action = getattr(self, 'action', None)
        if action == 'create':
            return []
        return super().get_authenticators()

    @decorators.action(detail=True, methods=['post'])
    def convert(self, request, pk=None):
        inquiry = self.get_object()
        # Minimal conversion: create a JobCard with info from inquiry
        jobcard = JobCard.objects.create(
            client=Client.objects.create(
                full_name=inquiry.name,
                mobile=inquiry.mobile,
                email=inquiry.email,
                city=inquiry.city,
            ),
            status=JobCard.JobStatus.ENQUIRY,
            service_type=inquiry.service_interest,
            schedule_date=request.data.get('schedule_date') or inquiry.created_at.date(),
            technician_name=request.data.get('technician_name', ''),
            price_subtotal=request.data.get('price_subtotal', 0),
            tax_percent=request.data.get('tax_percent', 18),
            payment_status=JobCard.PaymentStatus.UNPAID,
        )
        serializer = JobCardSerializer(jobcard)
        return response.Response(serializer.data)


class JobCardViewSet(viewsets.ModelViewSet):
    queryset = JobCard.objects.select_related('client').all().order_by('-created_at')
    serializer_class = JobCardSerializer
    permission_classes = [DefaultPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status', 'payment_status', 'client__city']
    search_fields = ['code', 'client__full_name', 'client__mobile', 'service_type']

    def get_queryset(self):
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
        return qs

    @decorators.action(detail=False, methods=['get'])
    def statistics(self, request):
        qs = self.get_queryset()
        data = {
            'total_jobs': qs.count(),
            'completed_jobs': qs.filter(status=JobCard.JobStatus.DONE).count(),
            'pending_jobs': qs.exclude(status=JobCard.JobStatus.DONE).count(),
            'total_revenue': str(sum((j.grand_total for j in qs), 0)),
            'completion_rate': (qs.filter(status=JobCard.JobStatus.DONE).count() / qs.count() * 100) if qs.exists() else 0,
        }
        return response.Response(data)


class RenewalViewSet(viewsets.ModelViewSet):
    queryset = Renewal.objects.select_related('jobcard', 'jobcard__client').all().order_by('due_date')
    serializer_class = RenewalSerializer
    permission_classes = [DefaultPermission]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['status']
    search_fields = ['jobcard__code', 'jobcard__client__full_name']

    def get_queryset(self):
        qs = super().get_queryset()
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
        return qs

    @decorators.action(detail=False, methods=['get'])
    def upcoming_summary(self, request):
        from django.utils import timezone
        from datetime import timedelta
        now = timezone.now()
        week = now + timedelta(days=7)
        month = now + timedelta(days=30)
        qs = self.get_queryset()
        data = {
            'due_this_week': qs.filter(due_date__lte=week, due_date__gte=now).count(),
            'due_this_month': qs.filter(due_date__lte=month, due_date__gte=now).count(),
            'overdue': qs.filter(due_date__lt=now).count(),
        }
        return response.Response(data)



