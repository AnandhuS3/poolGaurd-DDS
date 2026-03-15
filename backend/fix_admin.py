"""Check DB state and ensure everything needed for login works. (PostgreSQL)"""
import sys
sys.path.insert(0, '.')

from core.credentials import DB_USER, DB_PASSWORD
import psycopg2
import psycopg2.extras

conn = psycopg2.connect(
    host='localhost', port=5432,
    user=DB_USER, password=DB_PASSWORD,
    dbname='poolguard_db',
)
conn.autocommit = True
cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

# Check columns on users table
cursor.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'users'
""")
cols = [r['column_name'] for r in cursor.fetchall()]
print("users columns:", cols)

# Check if is_system_admin exists
if 'is_system_admin' not in cols:
    print("MISSING is_system_admin column — adding it now...")
    cursor.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS is_system_admin BOOLEAN NOT NULL DEFAULT FALSE")
    cursor.execute("UPDATE users SET is_system_admin = TRUE WHERE email = 'creagoouon@gmail.com'")
    print("Done — column added and system admin flagged.")
else:
    print("is_system_admin column exists.")
    cursor.execute("SELECT id, name, email, role, is_active, is_system_admin FROM users WHERE email='creagoouon@gmail.com'")
    print("Admin row:", cursor.fetchone())

cursor.close()
conn.close()
