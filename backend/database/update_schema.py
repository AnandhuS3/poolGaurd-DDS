"""
Update database schema to support only 'admin' and 'guard' roles (PostgreSQL).
Note: In PostgreSQL, ENUM types are separate objects. To change values, we recreate
the type or use a DO block. Since the schema already has the correct type, this
script just verifies the state.
"""
import psycopg2
import sys
sys.path.insert(0, '.')

from core.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

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

    # Verify the user_role enum type has the right values
    cursor.execute("""
        SELECT e.enumlabel
        FROM pg_type t
        JOIN pg_enum e ON t.oid = e.enumtypid
        WHERE t.typname = 'user_role'
        ORDER BY e.enumsortorder
    """)
    roles = [r[0] for r in cursor.fetchall()]
    print(f"Current user_role enum values: {roles}")

    if set(roles) == {'admin', 'guard'}:
        print("✅ user_role enum is correct: admin, guard")
    else:
        print("⚠️  Unexpected roles found. The schema.sql should be re-applied.")

    cursor.close()
    conn.close()

except psycopg2.Error as e:
    print(f"❌ Error: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
