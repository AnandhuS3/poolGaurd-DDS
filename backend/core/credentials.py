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
# APP CONFIGURATION
# ============================================================================
# Base URL used for verification and reset links in emails
APP_BASE_URL = os.getenv('APP_BASE_URL', 'http://localhost:5173')

# ============================================================================
# SECURITY / JWT
# ============================================================================
# Generate a strong secret with: python -c "import secrets; print(secrets.token_hex(64))"
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', '')

# ============================================================================
# CORS
# ============================================================================
# Comma-separated list of allowed frontend origins
# Example: http://localhost:5173,https://your-domain.com
_origins_str = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173')
ALLOWED_ORIGINS = [o.strip() for o in _origins_str.split(',') if o.strip()]

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

    # JWT secret (critical)
    if not JWT_SECRET_KEY:
        warnings.append("[CRITICAL] JWT_SECRET_KEY not set - using insecure fallback! Set this in .env")

    # Email credentials (optional but recommended)
    if not SMTP_USERNAME:
        warnings.append("[WARNING] SMTP_USERNAME not set - email notifications disabled")
    if not SMTP_PASSWORD:
        warnings.append("[WARNING] SMTP_PASSWORD not set - email notifications disabled")
    
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
