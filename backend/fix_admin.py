"""Check DB state and ensure everything needed for login works."""
import sys
sys.path.insert(0, '.')

from core.credentials import DB_USER, DB_PASSWORD
import mysql.connector

conn = mysql.connector.connect(
    host='localhost', user=DB_USER, password=DB_PASSWORD,
    database='drowning_detection_db'
)
cursor = conn.cursor(dictionary=True)

# Check columns on users table
cursor.execute("SHOW COLUMNS FROM users")
cols = [['Field'] for r in cursor.fetchall()]
print("users columns:", cols)

# Check if is_system_admin exists
if 'is_system_admin' not in cols:
    print("MISSING is_system_admin column — adding it now...")
    cursor.execute("ALTER TABLE users ADD COLUMN is_system_admin BOOLEAN NOT NULL DEFAULT FALSE")
    cursor.execute("UPDATE users SET is_system_admin = TRUE WHERE email = 'admin@dds.local'")
    conn.commit()
    print("Done — column added and system admin flagged.")
else:
    print("is_system_admin column exists.")
    cursor.execute("SELECT id, name, email, role, is_active, is_system_admin FROM users WHERE email='admin@dds.local'")
    print("Admin row:", cursor.fetchone())

cursor.close()
conn.close()
