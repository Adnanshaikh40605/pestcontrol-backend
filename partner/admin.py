from django.contrib import admin
from .models import CrmPartnerEvent, Partner, PartnerDeviceToken, PartnerNotification, PartnerEarning, PartnerRating


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'full_name', 'mobile', 'role', 'is_active',
        'core_technician', 'created_at'
    ]
    list_filter = ['role', 'is_active']
    search_fields = ['full_name', 'mobile']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ("Basic Info", {
            'fields': ('full_name', 'mobile', 'password', 'role', 'profile_image', 'is_active')
        }),
        ("CRM Link", {
            'fields': ('core_technician',)
        }),
        ("Bank Details", {
            'fields': ('bank_name', 'account_number', 'ifsc_code', 'account_holder_name')
        }),
        ("Push Notifications", {
            'fields': ('fcm_token',)
        }),
        ("Timestamps", {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PartnerEarning)
class PartnerEarningAdmin(admin.ModelAdmin):
    list_display = ['id', 'partner', 'job', 'amount', 'created_at']
    list_filter = ['partner']
    search_fields = ['partner__full_name', 'job__code']


@admin.register(PartnerRating)
class PartnerRatingAdmin(admin.ModelAdmin):
    list_display = ['id', 'partner', 'job', 'rating', 'feedback', 'created_at']
    list_filter = ['rating']
    search_fields = ['partner__full_name']


@admin.register(PartnerDeviceToken)
class PartnerDeviceTokenAdmin(admin.ModelAdmin):
    list_display = ['id', 'partner', 'device_type', 'is_active', 'last_used_at']
    list_filter = ['device_type', 'is_active']
    search_fields = ['partner__full_name', 'fcm_token']


@admin.register(PartnerNotification)
class PartnerNotificationAdmin(admin.ModelAdmin):
    list_display = ['id', 'partner', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read']
    search_fields = ['title', 'partner__full_name']


@admin.register(CrmPartnerEvent)
class CrmPartnerEventAdmin(admin.ModelAdmin):
    list_display = ['id', 'job', 'event_type', 'message', 'is_read', 'created_at']
    list_filter = ['event_type', 'is_read']
    search_fields = ['message', 'job__code']
