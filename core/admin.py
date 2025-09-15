from django.contrib import admin
from .models import Client, Inquiry, JobCard, Renewal


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile', 'city', 'is_active', 'created_at')
    search_fields = ('full_name', 'mobile', 'email', 'city')
    list_filter = ('city', 'is_active')


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile', 'city', 'status', 'created_at')
    search_fields = ('name', 'mobile', 'email', 'service_interest')
    list_filter = ('status', 'city')


@admin.register(JobCard)
class JobCardAdmin(admin.ModelAdmin):
    list_display = ('code', 'client', 'status', 'payment_status', 'price', 'schedule_date')
    search_fields = ('code', 'client__full_name', 'client__mobile')
    list_filter = ('status', 'payment_status')


@admin.register(Renewal)
class RenewalAdmin(admin.ModelAdmin):
    list_display = ('jobcard', 'due_date', 'status')
    search_fields = ('jobcard__code', 'jobcard__client__full_name')
    list_filter = ('status',)


