"""
Custom validators for the pest control application.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_mobile_number(value):
    """
    Validate that the mobile number is exactly 10 digits.
    """
    if not value:
        return
    
    # Remove any spaces or dashes
    cleaned_value = re.sub(r'[\s\-\(\)]', '', value)
    
    # Check if it's exactly 10 digits
    if not re.match(r'^\d{10}$', cleaned_value):
        raise ValidationError(
            _('Mobile number must be exactly 10 digits.'),
            code='invalid_mobile'
        )


def validate_positive_decimal(value):
    """
    Validate that a decimal value is positive.
    """
    if value is not None and value < 0:
        raise ValidationError(
            _('Value must be positive.'),
            code='negative_value'
        )


def validate_non_negative_decimal(value):
    """
    Validate that a decimal value is non-negative (>= 0).
    This allows zero values, which is useful for society job cards.
    """
    if value is not None and value < 0:
        raise ValidationError(
            _('Value must be zero or positive.'),
            code='negative_value'
        )


def validate_tax_percent(value):
    """
    Validate tax percentage (0-100).
    """
    if value is not None and (value < 0 or value > 100):
        raise ValidationError(
            _('Tax percentage must be between 0 and 100.'),
            code='invalid_tax_percent'
        )


def validate_job_code(value):
    """
    Validate job code format (JC-XXXX).
    """
    if not value:
        return
    
    if not re.match(r'^JC-\d{4,}$', value):
        raise ValidationError(
            _('Job code must be in format JC-XXXX where X is a digit.'),
            code='invalid_job_code'
        )
