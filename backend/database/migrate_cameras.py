"""
migrate_cameras.py (PostgreSQL)
-------------------
Adds the `cameras` table to the poolguard_db database and seeds a default demo camera.
Run once after the main schema has been applied:
    python -m database.migrate_cameras
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2 import Error

try:
    from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
except ImportError:
    DB_HOST = "localhost"
    DB_PORT = 5432
    DB_USER = "postgres"
    DB_PASSWORD = "root12"
    DB_NAME = "poolguard_db"


CAMERAS_TABLE_SQL = """
DO $$ BEGIN
    CREATE TYPE camera_status_enum AS ENUM ('active', 'inactive', 'maintenance');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

CREATE TABLE IF NOT EXISTS cameras (
    id                SERIAL PRIMARY KEY,
    camera_name       VARCHAR(255)       NOT NULL,
    pool_location     VARCHAR(255)       NOT NULL DEFAULT 'Main Pool',
    rtsp_url          VARCHAR(1024)      NOT NULL,
    hls_url           VARCHAR(1024)      NULL,
    status            camera_status_enum NOT NULL DEFAULT 'active',
    assigned_guard_id INTEGER            NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at        TIMESTAMP          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP          NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras(status);
CREATE INDEX IF NOT EXISTS idx_cameras_guard  ON cameras(assigned_guard_id);
"""


def run():
    print("[MIGRATE] Connecting to PostgreSQL database ...")
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

        print("[MIGRATE] Creating cameras table ...")
        cursor.execute(CAMERAS_TABLE_SQL)

        print("[MIGRATE] ✅ cameras table ready.")
        cursor.close()
    except Error as e:
        print(f"[MIGRATE] ❌ Error: {e}")
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    run()
