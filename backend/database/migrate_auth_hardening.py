"""
Migration: Auth Hardening — Email Verification & Password Reset (PostgreSQL)
Run once on an existing database to add the new columns.

Usage:
    cd backend
    python database/migrate_auth_hardening.py
"""
import psycopg2
from psycopg2 import Error
import sys
import os

# Allow running from the backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

# PostgreSQL supports IF NOT EXISTS in ALTER TABLE ADD COLUMN — much simpler
MIGRATIONS = [
    (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified            BOOLEAN NOT NULL DEFAULT FALSE",
        "email_verified",
    ),
    (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token        VARCHAR(255) NULL",
        "verification_token",
    ),
    (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS verification_token_expiry TIMESTAMP NULL",
        "verification_token_expiry",
    ),
    (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_token      VARCHAR(255) NULL",
        "password_reset_token",
    ),
    (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_reset_expiry     TIMESTAMP NULL",
        "password_reset_expiry",
    ),
    # Indexes — PostgreSQL uses CREATE INDEX IF NOT EXISTS
    (
        "CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token)",
        "idx_users_verification_token",
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_users_reset_token ON users(password_reset_token)",
        "idx_users_reset_token",
    ),
    # Pre-verify existing admins so they are not locked out
    (
        "UPDATE users SET email_verified = TRUE WHERE role = 'admin' OR is_system_admin = TRUE",
        "pre-verify existing admins",
    ),
]


def run_migrations():
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
        )
        conn.autocommit = True
        cursor = conn.cursor()
        print(f"Connected to {DB_NAME} on {DB_HOST}:{DB_PORT}")
        print("=" * 60)

        for sql, description in MIGRATIONS:
            try:
                cursor.execute(sql)
                print(f"  [OK]   {description}")
            except Error as e:
                print(f"  [WARN] {description}: {e}")

        cursor.close()
        print("=" * 60)
        print("Migration complete.")

    except Error as e:
        print(f"[ERROR] Could not connect to database: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run_migrations()
