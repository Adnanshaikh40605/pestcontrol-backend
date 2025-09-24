from django.contrib import admin
from .models import Client, Inquiry, JobCard, Renewal, DeviceToken, NotificationLog


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


@admin.register(DeviceToken)
class DeviceTokenAdmin(admin.ModelAdmin):
    list_display = ('device_name', 'token_short', 'is_active', 'created_at')
    search_fields = ('token', 'device_name')
    list_filter = ('is_active',)
    readonly_fields = ('created_at', 'updated_at')
    
    def token_short(self, obj):
        return f"{obj.token[:20]}..." if obj.token else ""
    token_short.short_description = 'Token (Short)'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'created_at')
    search_fields = ('title', 'body')
    list_filter = ('status',)
    readonly_fields = ('created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('title', 'body', 'status', 'error_message')
        return self.readonly_fields


