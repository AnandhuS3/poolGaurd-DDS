"""
Migration: Auth Hardening — Email Verification & Password Reset
Run once on an existing database to add the new columns.

Usage:
    cd backend
    python database/migrate_auth_hardening.py
"""
import mysql.connector
from mysql.connector import Error
import sys
import os

# Allow running from the backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

MIGRATIONS = [
    # Email verification columns
    (
        "ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT FALSE",
        "email_verified",
    ),
    (
        "ALTER TABLE users ADD COLUMN verification_token VARCHAR(255) NULL",
        "verification_token",
    ),
    (
        "ALTER TABLE users ADD COLUMN verification_token_expiry DATETIME NULL",
        "verification_token_expiry",
    ),
    # Password reset columns
    (
        "ALTER TABLE users ADD COLUMN password_reset_token VARCHAR(255) NULL",
        "password_reset_token",
    ),
    (
        "ALTER TABLE users ADD COLUMN password_reset_expiry DATETIME NULL",
        "password_reset_expiry",
    ),
    # Make phone_number optional (some registrations may omit it)
    (
        "ALTER TABLE users MODIFY COLUMN phone_number VARCHAR(20) NOT NULL DEFAULT ''",
        "phone_number (default '')",
    ),
    # Indexes for token lookups
    (
        "ALTER TABLE users ADD INDEX idx_verification_token (verification_token)",
        "idx_verification_token",
    ),
    (
        "ALTER TABLE users ADD INDEX idx_reset_token (password_reset_token)",
        "idx_reset_token",
    ),
    # Pre-verify existing admin / system accounts so they are not locked out
    (
        "UPDATE users SET email_verified = TRUE WHERE role = 'admin' OR is_system_admin = TRUE",
        "pre-verify existing admins",
    ),
]


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (DB_NAME, table, column),
    )
    return cursor.fetchone()[0] > 0


def index_exists(cursor, table: str, index_name: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.STATISTICS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND INDEX_NAME = %s",
        (DB_NAME, table, index_name),
    )
    return cursor.fetchone()[0] > 0


def run_migrations():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        cursor = conn.cursor()
        print(f"Connected to {DB_NAME} on {DB_HOST}:{DB_PORT}")
        print("=" * 60)

        for sql, description in MIGRATIONS:
            try:
                # Skip ADD COLUMN if column already exists
                upper = sql.upper()
                if "ADD COLUMN" in upper:
                    col = description.split(" ")[0]
                    if column_exists(cursor, "users", col):
                        print(f"  [SKIP] Column already exists: {col}")
                        continue

                # Skip ADD INDEX if index already exists
                if "ADD INDEX" in upper:
                    idx = description
                    if index_exists(cursor, "users", idx):
                        print(f"  [SKIP] Index already exists: {idx}")
                        continue

                cursor.execute(sql)
                conn.commit()
                print(f"  [OK]   {description}")
            except Error as e:
                if "Duplicate column name" in str(e) or "Duplicate key name" in str(e):
                    print(f"  [SKIP] Already applied: {description}")
                else:
                    print(f"  [WARN] {description}: {e}")

        cursor.close()
        conn.close()
        print("=" * 60)
        print("Migration complete.")

    except Error as e:
        print(f"[ERROR] Could not connect to database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_migrations()
