from django.contrib import admin
from .models import Client, Inquiry, JobCard, Renewal


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'mobile', 'email', 'city', 'is_active')
    list_filter = ('is_active', 'city')
    search_fields = ('full_name', 'mobile', 'email', 'city')


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'mobile', 'service_interest', 'city', 'status', 'created_at')
    list_filter = ('status', 'service_interest', 'city', 'created_at')
    search_fields = ('name', 'mobile', 'email', 'service_interest')
    actions = ['mark_as_contacted', 'mark_as_converted', 'mark_as_closed']
    
    def mark_as_contacted(self, request, queryset):
        queryset.update(status='Contacted')
    mark_as_contacted.short_description = "Mark selected inquiries as Contacted"
    
    def mark_as_converted(self, request, queryset):
        queryset.update(status='Converted')
    mark_as_converted.short_description = "Mark selected inquiries as Converted"
    
    def mark_as_closed(self, request, queryset):
        queryset.update(status='Closed')
    mark_as_closed.short_description = "Mark selected inquiries as Closed"


@admin.register(JobCard)
class JobCardAdmin(admin.ModelAdmin):
    list_display = ('code', 'client_name', 'client_mobile', 'client_city', 'service_type', 'status', 'schedule_date', 'grand_total')
    list_filter = ('status', 'schedule_date', 'payment_status')
    search_fields = ('code', 'client__full_name', 'client__mobile', 'service_type')
    readonly_fields = ('code', 'created_at', 'updated_at')
    
    def client_name(self, obj):
        return obj.client.full_name
    client_name.short_description = 'Client Name'
    
    def client_mobile(self, obj):
        return obj.client.mobile
    client_mobile.short_description = 'Mobile'
    
    def client_city(self, obj):
        return obj.client.city
    client_city.short_description = 'City'


@admin.register(Renewal)
class RenewalAdmin(admin.ModelAdmin):
    list_display = ('jobcard', 'due_date', 'status')
    list_filter = ('status', 'due_date')
    search_fields = ('jobcard__code', 'jobcard__client__full_name')
    actions = ['mark_as_completed']
    
    def mark_as_completed(self, request, queryset):
        queryset.update(status='Completed')
    mark_as_completed.short_description = "Mark selected renewals as Completed"
