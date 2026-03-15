"""
Migration: Promote creagoouon@gmail.com to system admin (PostgreSQL).
The old admin@dds.local row has its system-admin flag cleared.
Run once after deployment.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.credentials import DB_USER, DB_PASSWORD
import psycopg2

NEW_ADMIN_EMAIL = 'creagoouon@gmail.com'
OLD_ADMIN_EMAIL = 'admin@dds.local'


def run():
    conn = psycopg2.connect(
        host='localhost', port=5432,
        user=DB_USER, password=DB_PASSWORD,
        dbname='poolguard_db',
    )
    conn.autocommit = False
    cursor = conn.cursor()

    # Check current state
    cursor.execute(
        "SELECT id, name, email, role, is_system_admin FROM users WHERE email = %s",
        (NEW_ADMIN_EMAIL,)
    )
    new_admin = cursor.fetchone()

    if not new_admin:
        print(f"ERROR: No user found with email '{NEW_ADMIN_EMAIL}'")
        conn.close()
        return

    # Promote new admin
    cursor.execute(
        "UPDATE users SET role='admin', is_system_admin=TRUE WHERE email=%s",
        (NEW_ADMIN_EMAIL,)
    )
    # Demote the old system admin row
    cursor.execute(
        "UPDATE users SET is_system_admin=FALSE WHERE email=%s",
        (OLD_ADMIN_EMAIL,)
    )
    conn.commit()
    print(f"Promoted '{NEW_ADMIN_EMAIL}' to admin / is_system_admin=TRUE")
    print(f"Cleared is_system_admin from '{OLD_ADMIN_EMAIL}'")

    # Show final state
    cursor.execute("SELECT id, name, email, role, is_active, is_system_admin FROM users ORDER BY id")
    for row in cursor.fetchall():
        print(row)

    cursor.close()
    conn.close()


if __name__ == '__main__':
    run()
