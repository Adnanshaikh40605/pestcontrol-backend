from django.contrib import admin
from .models import Partner, PartnerEarning, PartnerRating


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
