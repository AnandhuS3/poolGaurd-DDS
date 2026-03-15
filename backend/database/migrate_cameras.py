"""
migrate_cameras.py
-------------------
Adds the `cameras` table to the DDS database and seeds a default demo camera.
Run once after the main schema has been applied:
    python -m database.migrate_cameras
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import mysql.connector
from mysql.connector import Error

try:
    from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
except ImportError:
    DB_HOST = "localhost"
    DB_PORT = 3306
    DB_USER = "root"
    DB_PASSWORD = ""
    DB_NAME = "drowning_detection_db"


CAMERAS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS cameras (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    camera_name   VARCHAR(255) NOT NULL,
    pool_location VARCHAR(255) NOT NULL DEFAULT 'Main Pool',
    rtsp_url      VARCHAR(1024) NOT NULL,
    hls_url       VARCHAR(1024) NULL    COMMENT 'Optional HLS URL served by streaming gateway',
    status        ENUM('active', 'inactive', 'maintenance') NOT NULL DEFAULT 'active',
    assigned_guard_id INT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    FOREIGN KEY (assigned_guard_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_status (status),
    INDEX idx_guard  (assigned_guard_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

def run():
    print("[MIGRATE] Connecting to database ...")
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
        )
        cursor = conn.cursor()

        print("[MIGRATE] Creating cameras table ...")
        cursor.execute(CAMERAS_TABLE_SQL)

        conn.commit()
        print("[MIGRATE] ✅ cameras table ready.")

        cursor.close()
        conn.close()
    except Error as e:
        print(f"[MIGRATE] ❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run()
