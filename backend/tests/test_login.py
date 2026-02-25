"""Test admin login credentials"""
from core.auth import PasswordHasher
import mysql.connector

# Connect to database
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='1234@1234qQ',
    database='drowning_detection_db'
)
cursor = conn.cursor()

# Get admin user
cursor.execute('SELECT name, email, password_hash FROM users WHERE email = %s', ('admin@dds.local',))
result = cursor.fetchone()

if result:
    name, email, stored_hash = result
    print(f"Found user: {name} ({email})")
    print(f"Stored hash: {stored_hash[:60]}...")
    
    # Test password
    test_password = 'admin123'
    is_valid = PasswordHasher.verify_password(test_password, stored_hash)
    
    print(f"\nPassword test:")
    print(f"  Testing: '{test_password}'")
    print(f"  Result: {'✅ VALID' if is_valid else '❌ INVALID'}")
    
    if not is_valid:
        print("\n⚠️  Password mismatch! Creating new hash...")
        new_hash = PasswordHasher.hash_password('admin123')
        cursor.execute('UPDATE users SET password_hash = %s WHERE email = %s', (new_hash, 'admin@dds.local'))
        conn.commit()
        print("✅ Password reset to: admin123")
else:
    print("❌ No admin user found!")

cursor.close()
conn.close()
