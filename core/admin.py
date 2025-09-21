from django.contrib import admin
from .models import Client, Inquiry, JobCard, Renewal, DeviceToken, NotificationLog, NotificationSubscription


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
    list_display = ('device_type', 'token_short', 'is_active', 'last_used', 'created_at')
    search_fields = ('token', 'user_agent')
    list_filter = ('device_type', 'is_active')
    readonly_fields = ('last_used', 'created_at', 'updated_at')
    
    def token_short(self, obj):
        return f"{obj.token[:20]}..." if obj.token else ""
    token_short.short_description = 'Token (Short)'


@admin.register(NotificationLog)
class NotificationLogAdmin(admin.ModelAdmin):
    list_display = ('title', 'notification_type', 'status', 'success_count', 'failure_count', 'created_at')
    search_fields = ('title', 'body', 'topic')
    list_filter = ('notification_type', 'status', 'topic')
    readonly_fields = ('success_count', 'failure_count', 'error_message', 'firebase_message_id', 'created_at', 'updated_at')
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # editing an existing object
            return self.readonly_fields + ('title', 'body', 'notification_type', 'target_tokens', 'topic', 'data_payload')
        return self.readonly_fields


@admin.register(NotificationSubscription)
class NotificationSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('device_token_short', 'topic', 'is_active', 'created_at')
    search_fields = ('topic', 'device_token__token')
    list_filter = ('topic', 'is_active', 'device_token__device_type')
    readonly_fields = ('created_at', 'updated_at')
    
    def device_token_short(self, obj):
        return f"{obj.device_token.token[:20]}..." if obj.device_token and obj.device_token.token else ""
    device_token_short.short_description = 'Device Token (Short)'


