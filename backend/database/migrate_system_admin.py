"""
Database Migration: Add System Administrator Protection
Date: 2026-02-15
Description: Adds is_system_admin flag and enforces single system admin constraint
"""

import mysql.connector
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.credentials import DB_USER, DB_PASSWORD

def run_migration():
    """Execute database migration"""
    try:
        # Connect to database
        conn = mysql.connector.connect(
            host='localhost',
            user=DB_USER,
            password=DB_PASSWORD,
            database='drowning_detection_db'
        )
        cursor = conn.cursor()
        
        print("=" * 60)
        print("  DATABASE MIGRATION: System Admin Protection")
        print("=" * 60)
        
        # Step 1: Add is_system_admin column
        print("\n[1/4] Adding is_system_admin column...")
        try:
            cursor.execute("""
                ALTER TABLE users 
                ADD COLUMN is_system_admin BOOLEAN NOT NULL DEFAULT FALSE
            """)
            print("✓ Column added successfully")
        except mysql.connector.Error as e:
            if "Duplicate column name" in str(e):
                print("⚠ Column already exists, skipping...")
            else:
                raise
        
        # Step 2: Mark existing system administrator
        print("\n[2/4] Marking system administrator...")
        cursor.execute("""
            UPDATE users 
            SET is_system_admin = TRUE 
            WHERE email = 'creagoouon@gmail.com' AND role = 'admin'
            LIMIT 1
        """)
        affected = cursor.rowcount
        if affected > 0:
            print(f"✓ Marked {affected} user as system administrator")
        else:
            print("⚠ No user found with email 'creagoouon@gmail.com'")
        
        # Step 3: Ensure only ONE system admin exists
        print("\n[3/4] Enforcing single system admin constraint...")
        cursor.execute("""
            SELECT COUNT(*) as count 
            FROM users 
            WHERE is_system_admin = TRUE
        """)
        count = cursor.fetchone()[0]
        
        if count > 1:
            print(f"⚠ WARNING: Found {count} system admins! Keeping only the first one...")
            cursor.execute("""
                UPDATE users 
                SET is_system_admin = FALSE 
                WHERE is_system_admin = TRUE 
                AND id NOT IN (
                    SELECT id FROM (
                        SELECT id FROM users 
                        WHERE is_system_admin = TRUE 
                        ORDER BY created_at ASC 
                        LIMIT 1
                    ) as temp
                )
            """)
            print(f"✓ Reset {cursor.rowcount} duplicate system admins")
        elif count == 1:
            print("✓ Exactly one system admin exists")
        else:
            print("⚠ WARNING: No system admin found!")
        
        # Step 4: Add index for performance
        print("\n[4/4] Adding index on is_system_admin...")
        try:
            cursor.execute("""
                CREATE INDEX idx_system_admin ON users(is_system_admin)
            """)
            print("✓ Index created successfully")
        except mysql.connector.Error as e:
            if "Duplicate key name" in str(e):
                print("⚠ Index already exists, skipping...")
            else:
                raise
        
        # Commit changes
        conn.commit()
        
        # Verify migration
        print("\n" + "=" * 60)
        print("  VERIFICATION")
        print("=" * 60)
        
        cursor.execute("""
            SELECT id, name, email, role, is_system_admin, created_at
            FROM users
            WHERE is_system_admin = TRUE
        """)
        system_admin = cursor.fetchone()
        
        if system_admin:
            print(f"\n✓ System Administrator:")
            print(f"  ID: {system_admin[0]}")
            print(f"  Name: {system_admin[1]}")
            print(f"  Email: {system_admin[2]}")
            print(f"  Role: {system_admin[3]}")
            print(f"  Created: {system_admin[5]}")
        else:
            print("\n⚠ WARNING: No system administrator found!")
        
        print("\n" + "=" * 60)
        print("  MIGRATION COMPLETED SUCCESSFULLY")
        print("=" * 60 + "\n")
        
        cursor.close()
        conn.close()
        
        return True
        
    except mysql.connector.Error as e:
        print(f"\n❌ DATABASE ERROR: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
