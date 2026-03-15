"""
Migration: Mobile FCM Device Token (PostgreSQL)
Adds fcm_token column to the users table for push notification support.

Usage:
    cd backend
    python database/migrate_mobile_fcm.py
"""
import psycopg2
from psycopg2 import Error
import sys
import os

# Allow running from the backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

MIGRATIONS = [
    (
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS fcm_token VARCHAR(255) NULL",
        "fcm_token",
    ),
]


def run():
    conn = None
    try:
        conn = psycopg2.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            dbname=DB_NAME,
        )
        conn.autocommit = True
        cursor = conn.cursor()
        print(f"[MIGRATION] Connected to '{DB_NAME}'")

        for sql, column in MIGRATIONS:
            try:
                cursor.execute(sql)
                print(f"[MIGRATION] Applied: '{column}'.")
            except Error as e:
                if "already exists" in str(e).lower():
                    print(f"[MIGRATION] Column '{column}' already exists — skipping.")
                else:
                    print(f"[MIGRATION] Error on '{column}': {e}")

        cursor.close()
        print("[MIGRATION] Done.")

    except Error as e:
        print(f"[MIGRATION] Error: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run()
