"""
Credentials Loader for Drowning Detection System
Loads sensitive credentials from .env file using python-dotenv

SECURITY NOTE:
- This file is safe to commit to Git (no secrets here)
- Actual secrets are stored in .env file (which is gitignored)
- Copy .env.example to .env and fill in your credentials
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in config/ directory
# Get project root (parent of core/ directory)
project_root = Path(__file__).parent.parent
env_path = project_root / "config" / ".env"
load_dotenv(dotenv_path=env_path)

# ============================================================================
# DATABASE CREDENTIALS
# ============================================================================
DB_USER = os.getenv('DB_USER', 'root')
DB_PASSWORD = os.getenv('DB_PASSWORD', '')

# ============================================================================
# EMAIL CREDENTIALS (SMTP)
# ============================================================================
# For Gmail, use App Password (not regular password)
# Get it from: https://myaccount.google.com/apppasswords
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

# ============================================================================
# SMS/WHATSAPP CREDENTIALS (Twilio)
# ============================================================================
# Get your credentials from: https://www.twilio.com/console
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID', '')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN', '')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER', '')
TWILIO_WHATSAPP_FROM = os.getenv('TWILIO_WHATSAPP_FROM', 'whatsapp:+14155238886')

# ============================================================================
# NOTIFICATION RECIPIENTS
# ============================================================================
# Comma-separated list of email addresses or phone numbers
# Example: user1@example.com,user2@example.com
_recipients_str = os.getenv('NOTIFICATION_RECIPIENTS', '')
NOTIFICATION_RECIPIENTS = [r.strip() for r in _recipients_str.split(',') if r.strip()]

# ============================================================================
# VALIDATION
# ============================================================================
def validate_credentials():
    """
    Validate that required credentials are set.
    Prints warnings for missing credentials but doesn't crash the app.
    """
    warnings = []
    
    # Database credentials (required)
    if not DB_USER:
        warnings.append("[WARNING] DB_USER not set in .env file")
    if not DB_PASSWORD:
        warnings.append("[WARNING] DB_PASSWORD not set in .env file (using empty password)")
    
    # Email credentials (optional but recommended)
    if not SMTP_USERNAME:
        warnings.append("[WARNING] SMTP_USERNAME not set - email notifications disabled")
    if not SMTP_PASSWORD:
        warnings.append("[WARNING] SMTP_PASSWORD not set - email notifications disabled")
    
    # Twilio credentials (optional)
    if not TWILIO_ACCOUNT_SID and not TWILIO_AUTH_TOKEN:
        # Only warn if notification type is SMS/WhatsApp
        pass  # Silent - SMS/WhatsApp is optional
    
    # Print warnings
    if warnings:
        print("\n" + "=" * 60)
        print("  CREDENTIAL WARNINGS")
        print("=" * 60)
        for warning in warnings:
            print(warning)
        print("\n[INFO] To fix: Copy .env.example to .env and fill in your credentials")
        print("=" * 60 + "\n")
    else:
        print("[OK] All credentials loaded successfully from .env")

# Run validation on import (non-blocking)
validate_credentials()
