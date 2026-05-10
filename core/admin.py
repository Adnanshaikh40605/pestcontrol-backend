from django.contrib import admin
from .models import Client, Inquiry, JobCard, Renewal


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile', 'city', 'is_active', 'created_at')
    search_fields = ('full_name', 'mobile', 'email', 'city')
    list_filter = ('city', 'is_active')


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile', 'premise_type', 'premise_size', 'estimated_price', 'status', 'created_at')
    search_fields = ('name', 'mobile', 'email', 'service_interest', 'message')
    list_filter = ('status', 'premise_type', 'city', 'created_at')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Customer Info', {
            'fields': ('name', 'mobile', 'email', 'city', 'state')
        }),
        ('Quote Details', {
            'fields': ('premise_type', 'premise_size', 'pest_problems', 'estimated_price', 'is_inspection_required', 'service_frequency', 'service_interest')
        }),
        ('Status & Management', {
            'fields': ('status', 'is_read', 'message', 'reminder_date', 'reminder_time', 'reminder_note', 'is_reminder_done')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(JobCard)
class JobCardAdmin(admin.ModelAdmin):
    list_display = ('code', 'client', 'status', 'payment_status', 'price', 'schedule_datetime')
    search_fields = ('code', 'client__full_name', 'client__mobile')
    list_filter = ('status', 'payment_status')


@admin.register(Renewal)
class RenewalAdmin(admin.ModelAdmin):
    list_display = ('jobcard', 'due_date', 'status')
    search_fields = ('jobcard__code', 'jobcard__client__full_name')
    list_filter = ('status',)


