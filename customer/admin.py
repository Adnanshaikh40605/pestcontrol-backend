from django.contrib import admin

from .models import CustomerAccount, CustomerRevokedJti


@admin.register(CustomerAccount)
class CustomerAccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'full_name', 'mobile', 'client', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['full_name', 'mobile', 'email']
    raw_id_fields = ['client']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(CustomerRevokedJti)
class CustomerRevokedJtiAdmin(admin.ModelAdmin):
    list_display = ['jti', 'expires_at', 'created_at']
    search_fields = ['jti']
