"""
Region-Based Utilities for Drowning Detection System
Supports international phone numbers and timezone handling
"""
import os
from datetime import datetime
import pytz

# Default timezone (can be configured via environment variable)
DEFAULT_TIMEZONE = os.getenv('SYSTEM_TIMEZONE', 'Asia/Kolkata')
SYSTEM_TZ = pytz.timezone(DEFAULT_TIMEZONE)

def get_system_time():
    """Get current time in system timezone"""
    return datetime.now(SYSTEM_TZ)

def format_datetime(dt=None, tz=None):
    """
    Format datetime in specified timezone
    
    Args:
        dt: datetime object (defaults to current time)
        tz: timezone string (defaults to system timezone)
    
    Returns:
        Formatted datetime string
    """
    if tz:
        target_tz = pytz.timezone(tz)
    else:
        target_tz = SYSTEM_TZ
    
    if dt is None:
        dt = get_system_time()
    elif dt.tzinfo is None:
        # If naive datetime, assume UTC and convert to target timezone
        dt = pytz.UTC.localize(dt).astimezone(target_tz)
    
    return dt.strftime("%d-%m-%Y %I:%M:%S %p %Z")

# International phone number validation
# E.164 format: +[country code][number]
def validate_phone_number(phone: str) -> bool:
    """
    Validate international phone number in E.164 format
    
    Args:
        phone: Phone number string
    
    Returns:
        True if valid E.164 format, False otherwise
    """
    import re
    # E.164: + followed by 1-15 digits
    pattern = r'^\+[1-9]\d{1,14}$'
    return bool(re.match(pattern, phone.replace(' ', '').replace('-', '')))

def format_phone_number(phone: str, country_code: str = None) -> str:
    """
    Format phone number to E.164 standard
    
    Args:
        phone: Phone number (with or without country code)
        country_code: Country code to prepend if not present (e.g., '+91', '+1')
    
    Returns:
        Formatted phone number in E.164 format
    """
    # Remove all non-digit characters except +
    cleaned = ''.join(c for c in phone if c.isdigit() or c == '+')
    
    # If already has +, return as is (after cleaning)
    if cleaned.startswith('+'):
        return cleaned
    
    # If country code provided, prepend it
    if country_code:
        if not country_code.startswith('+'):
            country_code = '+' + country_code
        return country_code + cleaned
    
    # Return as is if no country code
    return '+' + cleaned if not cleaned.startswith('+') else cleaned

# Common country codes for dropdown
COUNTRY_CODES = [
    {'code': '+91', 'name': 'India', 'flag': '🇮🇳', 'pattern': r'^[6-9]\d{9}$'},
    {'code': '+1', 'name': 'USA/Canada', 'flag': '🇺🇸', 'pattern': r'^\d{10}$'},
    {'code': '+44', 'name': 'United Kingdom', 'flag': '🇬🇧', 'pattern': r'^\d{10}$'},
    {'code': '+61', 'name': 'Australia', 'flag': '🇦🇺', 'pattern': r'^\d{9}$'},
    {'code': '+81', 'name': 'Japan', 'flag': '🇯🇵', 'pattern': r'^\d{10}$'},
    {'code': '+86', 'name': 'China', 'flag': '🇨🇳', 'pattern': r'^\d{11}$'},
    {'code': '+33', 'name': 'France', 'flag': '🇫🇷', 'pattern': r'^\d{9}$'},
    {'code': '+49', 'name': 'Germany', 'flag': '🇩🇪', 'pattern': r'^\d{10,11}$'},
    {'code': '+971', 'name': 'UAE', 'flag': '🇦🇪', 'pattern': r'^\d{9}$'},
    {'code': '+65', 'name': 'Singapore', 'flag': '🇸🇬', 'pattern': r'^\d{8}$'},
]

print(f"Region utilities loaded - Timezone: {DEFAULT_TIMEZONE}")
