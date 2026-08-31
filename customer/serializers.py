from decimal import Decimal, InvalidOperation

from django.db import transaction
from rest_framework import serializers

from core.models import Client, Feedback, JobCard, PricingRate
from core.staff_partner_sync import normalize_mobile

from .models import CustomerAccount


class CustomerRegisterSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255)
    mobile = serializers.CharField(max_length=15)
    # Optional — passwordless OTP register uses an unusable password.
    password = serializers.CharField(min_length=6, write_only=True, required=False, allow_blank=True, default='')
    email = serializers.EmailField(required=False, allow_blank=True, default='')

    def validate_mobile(self, value):
        value = normalize_mobile(value)
        if CustomerAccount.objects.filter(mobile=value).exists():
            raise serializers.ValidationError('An account with this mobile already exists.')
        return value

    @transaction.atomic
    def create(self, validated_data):
        mobile = validated_data['mobile']
        name = validated_data['full_name'].strip()
        email = (validated_data.get('email') or '').strip()

        client, _ = Client.objects.get_or_create(
            mobile=mobile,
            defaults={
                'full_name': name,
                'email': email,
                'is_active': True,
            },
        )
        if client.full_name != name or (email and client.email != email):
            client.full_name = name or client.full_name
            if email:
                client.email = email
            client.save(update_fields=['full_name', 'email', 'updated_at'])

        account = CustomerAccount(
            client=client,
            mobile=mobile,
            full_name=name,
            email=email,
            is_active=True,
        )
        raw_password = (validated_data.get('password') or '').strip()
        account.set_password(raw_password or None)
        account.save()
        return account


class CustomerLoginSerializer(serializers.Serializer):
    mobile = serializers.CharField()
    password = serializers.CharField(write_only=True)


class CustomerOTPSendSerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    purpose = serializers.ChoiceField(choices=['login', 'register'])
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def validate(self, attrs):
        attrs['mobile'] = normalize_mobile(attrs['mobile'])
        purpose = attrs['purpose']
        name = (attrs.get('full_name') or '').strip()
        if purpose == 'register' and len(name) < 2:
            raise serializers.ValidationError({'full_name': 'Name is required to create an account.'})
        attrs['full_name'] = name
        return attrs


class CustomerOTPVerifySerializer(serializers.Serializer):
    mobile = serializers.CharField(max_length=15)
    otp = serializers.CharField(min_length=4, max_length=4)
    purpose = serializers.ChoiceField(choices=['login', 'register'])
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')

    def validate_otp(self, value):
        value = (value or '').strip()
        if not value.isdigit() or len(value) != 4:
            raise serializers.ValidationError('Enter the 4-digit OTP.')
        return value

    def validate(self, attrs):
        attrs['mobile'] = normalize_mobile(attrs['mobile'])
        attrs['full_name'] = (attrs.get('full_name') or '').strip()
        return attrs


class CustomerRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


class CustomerProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomerAccount
        fields = [
            'id', 'client_id', 'full_name', 'mobile', 'email',
            'is_active', 'created_at',
        ]
        read_only_fields = fields


class CustomerProfileUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=255, required=False)
    email = serializers.EmailField(required=False, allow_blank=True)


class CatalogRateSerializer(serializers.ModelSerializer):
    region_slug = serializers.CharField(source='region.slug', read_only=True)
    region_name = serializers.CharField(source='region.name', read_only=True)
    package_tiers = serializers.SerializerMethodField()

    class Meta:
        model = PricingRate
        fields = [
            'id', 'region_slug', 'region_name', 'service_package', 'plan_type',
            'area_key', 'property_category', 'amount', 'package_tiers',
        ]

    def get_package_tiers(self, obj):
        # Standard/Premium are booking tiers; catalog exposes both with same base rate for MVP.
        # Premium can be marked +15% display hint for UI (CRM can refine later).
        base = obj.amount
        try:
            premium = (base * Decimal('1.15')).quantize(Decimal('0.01'))
        except (InvalidOperation, TypeError):
            premium = base
        return {
            'standard': str(base),
            'premium': str(premium),
        }


class CustomerBookSerializer(serializers.Serializer):
    service_type = serializers.CharField(max_length=500, required=False, allow_blank=True, default='')
    plan_type = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    package_tier = serializers.ChoiceField(
        choices=['standard', 'premium'],
        default='standard',
    )
    property_type = serializers.CharField(max_length=50, required=False, allow_blank=True, default='Home / Flat')
    bhk_size = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    address = serializers.CharField(max_length=1000)
    city = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')
    area = serializers.CharField(max_length=255, required=False, allow_blank=True, default='')
    schedule_datetime = serializers.DateTimeField(required=False, allow_null=True)
    time_slot = serializers.CharField(max_length=50, required=False, allow_blank=True, default='')
    pricing_rate_id = serializers.IntegerField(required=False, allow_null=True)
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, default='')
    booking_type = serializers.ChoiceField(
        choices=['one_time', 'amc', 'contractual'],
        default='one_time',
        required=False,
    )
    price_confirmation_pending = serializers.BooleanField(required=False, default=False)


class CustomerBookingSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.full_name', read_only=True)
    can_rate = serializers.SerializerMethodField()
    my_rating = serializers.SerializerMethodField()
    invoice_amount = serializers.SerializerMethodField()
    amc_parent_id = serializers.IntegerField(source='parent_job_id', read_only=True, allow_null=True)
    price_confirmation_pending = serializers.SerializerMethodField()
    technician_name = serializers.SerializerMethodField()
    technician_mobile = serializers.SerializerMethodField()
    technician_photo_url = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = JobCard
        fields = [
            'id', 'code', 'service_type', 'booking_type', 'package_tier',
            'property_type', 'bhk_size', 'client_name', 'client_address',
            'city', 'schedule_datetime', 'time_slot',
            'status', 'partner_status', 'payment_status', 'payment_mode',
            'price', 'total_amount', 'invoice_amount', 'is_price_estimated',
            'price_confirmation_pending',
            'technician_name', 'technician_mobile', 'technician_photo_url',
            'can_cancel',
            'notes', 'completed_at', 'created_at',
            'can_rate', 'my_rating', 'amc_parent_id', 'service_cycle', 'max_cycle',
        ]

    def get_invoice_amount(self, obj):
        if obj.total_amount is not None:
            return str(obj.total_amount)
        return obj.price

    def get_price_confirmation_pending(self, obj):
        if getattr(obj, 'is_price_estimated', False):
            return True
        note = (obj.notes or '').lower()
        return 'price confirmation pending' in note

    def _assigned_technician(self, obj):
        tech = getattr(obj, 'technician', None)
        if tech:
            return tech
        partner = getattr(obj, 'partner', None)
        if partner:
            return getattr(partner, 'core_technician', None)
        return None

    def get_technician_name(self, obj):
        # Only reveal after partner has accepted the job.
        if (obj.partner_status or '') not in (
            JobCard.PartnerStatus.ACCEPTED,
            JobCard.PartnerStatus.IN_SERVICE,
            JobCard.PartnerStatus.COMPLETED,
        ):
            return None
        tech = self._assigned_technician(obj)
        if tech and tech.name:
            return tech.name
        partner = getattr(obj, 'partner', None)
        if partner and partner.full_name:
            return partner.full_name
        return None

    def get_technician_mobile(self, obj):
        if (obj.partner_status or '') not in (
            JobCard.PartnerStatus.ACCEPTED,
            JobCard.PartnerStatus.IN_SERVICE,
            JobCard.PartnerStatus.COMPLETED,
        ):
            return None
        tech = self._assigned_technician(obj)
        if tech and tech.mobile:
            return tech.mobile
        partner = getattr(obj, 'partner', None)
        if partner and partner.mobile:
            return partner.mobile
        return None

    def get_technician_photo_url(self, obj):
        if (obj.partner_status or '') not in (
            JobCard.PartnerStatus.ACCEPTED,
            JobCard.PartnerStatus.IN_SERVICE,
            JobCard.PartnerStatus.COMPLETED,
        ):
            return None
        request = self.context.get('request')
        partner = getattr(obj, 'partner', None)
        image = None
        if partner and partner.profile_image:
            image = partner.profile_image.url
        else:
            tech = self._assigned_technician(obj)
            if tech and getattr(tech, 'photo', None):
                try:
                    image = tech.photo.url
                except ValueError:
                    image = None
        if not image:
            return None
        if request and not str(image).startswith('http'):
            return request.build_absolute_uri(image)
        return image

    def get_can_cancel(self, obj):
        if obj.status in (JobCard.JobStatus.CANCELLED, JobCard.JobStatus.DONE):
            return False
        if (obj.partner_status or '') in (
            JobCard.PartnerStatus.IN_SERVICE,
            JobCard.PartnerStatus.COMPLETED,
        ):
            return False
        return True

    def get_can_rate(self, obj):
        if obj.status != JobCard.JobStatus.DONE:
            return False
        return not Feedback.objects.filter(booking=obj, rating__gt=0).exists()

    def get_my_rating(self, obj):
        fb = Feedback.objects.filter(booking=obj, rating__gt=0).order_by('-created_at').first()
        if not fb:
            return None
        return {
            'rating': fb.rating,
            'remark': fb.remark,
            'technician_behavior': fb.technician_behavior,
        }


class CustomerCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, min_length=4)


class CustomerRateSerializer(serializers.Serializer):
    rating = serializers.IntegerField(min_value=1, max_value=5)
    remark = serializers.CharField(required=False, allow_blank=True, default='')
    technician_behavior = serializers.ChoiceField(
        choices=['excellent', 'good', 'average', 'poor'],
        required=False,
        allow_blank=True,
        default='good',
    )


class CustomerPaymentConfirmSerializer(serializers.Serializer):
    """Gateway confirm — disabled in production until Razorpay (etc.) is wired."""
    payment_reference = serializers.CharField(max_length=100, required=False, allow_blank=True, default='')


class CustomerComplaintSerializer(serializers.Serializer):
    complaint_type = serializers.CharField(max_length=100)
    note = serializers.CharField(max_length=2000)
    booking_id = serializers.IntegerField(required=False, allow_null=True)
    priority = serializers.ChoiceField(
        choices=['Low', 'Medium', 'High'],
        required=False,
        default='Medium',
    )


class CustomerDeleteAccountSerializer(serializers.Serializer):
    confirm = serializers.BooleanField()

    def validate_confirm(self, value):
        if value is not True:
            raise serializers.ValidationError('You must confirm account deletion.')
        return value
