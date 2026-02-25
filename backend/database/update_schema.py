"""
Update database schema to support only 'admin' and 'guard' roles
"""
import mysql.connector
from core.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

try:
    conn = mysql.connector.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    cursor = conn.cursor()
    
    print("Updating users table to support only 'admin' and 'guard' roles...")
    
    # Alter the ENUM to only include 'admin' and 'guard' roles
    cursor.execute("""
        ALTER TABLE users 
        MODIFY COLUMN role ENUM('admin', 'guard') NOT NULL DEFAULT 'guard'
    """)
    
    conn.commit()
    print("✅ Successfully updated users table!")
    print("   Roles now supported: admin, guard")
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as e:
    print(f"❌ Error updating schema: {e}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")
