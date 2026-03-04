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
# Railway MySQL plugin injects MYSQLUSER / MYSQLHOST / MYSQLPASSWORD /
# MYSQLDATABASE / MYSQLPORT automatically — we fall back to the Railway vars
# if the generic ones are not set, so the same .env.example works everywhere.
DB_USER     = os.getenv('DB_USER')     or os.getenv('MYSQLUSER',     'root')
DB_PASSWORD = os.getenv('DB_PASSWORD') or os.getenv('MYSQLPASSWORD', '')
DB_HOST     = os.getenv('DB_HOST')     or os.getenv('MYSQLHOST',     'localhost')
DB_PORT     = int(os.getenv('DB_PORT') or os.getenv('MYSQLPORT',     '3306'))
DB_NAME     = os.getenv('DB_NAME')     or os.getenv('MYSQLDATABASE', 'drowning_detection_db')

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
# Example: ALLOWED_ORIGINS=http://localhost:5173,https://your-frontend.up.railway.app
# Convenience single-URL alias (Railway: set FRONTEND_URL on the backend service)
_origins_str = os.getenv('ALLOWED_ORIGINS', 'http://localhost:5173')
ALLOWED_ORIGINS = [o.strip() for o in _origins_str.split(',') if o.strip()]

# FRONTEND_URL is a single-value convenience alias for Railway deployments.
# If set and not already in the list, it is appended automatically.
_frontend_url = os.getenv('FRONTEND_URL', '').strip().rstrip('/')
if _frontend_url and _frontend_url not in ALLOWED_ORIGINS:
    ALLOWED_ORIGINS.append(_frontend_url)

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
