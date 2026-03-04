"""
Migration: Mobile FCM Device Token
Adds fcm_token column to the users table for push notification support.

Usage:
    cd backend
    python database/migrate_mobile_fcm.py
"""
import mysql.connector
from mysql.connector import Error
import sys
import os

# Allow running from the backend/ directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

MIGRATIONS = [
    (
        "ALTER TABLE users ADD COLUMN fcm_token VARCHAR(255) NULL",
        "fcm_token",
    ),
]


def column_exists(cursor, table: str, column: str) -> bool:
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (DB_NAME, table, column),
    )
    return cursor.fetchone()[0] > 0


def run():
    try:
        conn = mysql.connector.connect(
            host=DB_HOST, port=DB_PORT,
            user=DB_USER, password=DB_PASSWORD,
            database=DB_NAME,
        )
        cursor = conn.cursor()
        print(f"[MIGRATION] Connected to '{DB_NAME}'")

        for sql, column in MIGRATIONS:
            if column_exists(cursor, "users", column):
                print(f"[MIGRATION] Column '{column}' already exists — skipping.")
            else:
                cursor.execute(sql)
                conn.commit()
                print(f"[MIGRATION] Added column '{column}'.")

        cursor.close()
        conn.close()
        print("[MIGRATION] Done.")

    except Error as e:
        print(f"[MIGRATION] Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
