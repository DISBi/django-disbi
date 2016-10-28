"""
This file collects field validators that are common to the domain
of systems biology.
"""
# standard library
import re

# Django
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.utils.translation import ugettext_lazy as _

# This would be the correct pattern, allows only EC numbers like 1.1.-.-
EC_PATTERN = re.compile(r'''(
                        (^[1-6]\.[1-9]\d*\.[1-9]\d*\.[Bnm]?[1-9]\d*$)|
                        (^[1-6]\.[1-9]\d*\.[1-9]\d*\.-$)|
                        (^[1-6]\.[1-9]\d*\.-\.-$)|
                        (^[1-6]\.-\.-\.-$)
                        )''', re.VERBOSE)
# This allows for shortened imcomplete EC numbers as well like 1.1.-
SHORTENED_EC_PATTERN = re.compile(r'''(
                        (^[1-6]\.[1-9]\d*\.[1-9]\d*\.[Bnm]?[1-9]\d*$)|
                        (^[1-6]\.[1-9]\d*\.[1-9]\d*\.-$)|
                        (^[1-6]\.[1-9]\d*\.-$)|
                        (^[1-6]\.-$)
                        )''', re.VERBOSE)

ec_err_msg = 'Invalid EC number'

ec_validator = RegexValidator(regex=EC_PATTERN, message=ec_err_msg)
"""Validator for normal EC numbers."""
short_ec_validator = RegexValidator(regex=SHORTENED_EC_PATTERN, message=ec_err_msg)
"""Validator for stunted EC numbers like '1.1.-'."""

def validate_probabilty(value):
    """Validate that a value is in [0, 1]."""
    if not 0 <= value <= 1:
        raise ValidationError(
            _('P-value %(value)s is not between 0 and 1'),
            params={'value': value}
        )
        
def validate_flux(value):
    """Validate that a value is in [-1000, 1000]."""
    if not -1000 <= value <= 1000:
        raise ValidationError(
            _('Flux with value %(value)s is not between -1000 and 1000'),
            params={'value': value}
        )
