"""Test admin login credentials (PostgreSQL)"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.auth import PasswordHasher
import psycopg2
from core.credentials import DB_USER, DB_PASSWORD

# Connect to database
conn = psycopg2.connect(
    host='localhost',
    port=5432,
    user=DB_USER,
    password=DB_PASSWORD,
    dbname='poolguard_db'
)
conn.autocommit = True
cursor = conn.cursor()

# Get admin user
cursor.execute('SELECT name, email, password_hash FROM users WHERE email = %s', ('creagoouon@gmail.com',))
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
        cursor.execute('UPDATE users SET password_hash = %s WHERE email = %s', (new_hash, 'creagoouon@gmail.com'))
        print("✅ Password reset to: admin123")
else:
    print("❌ No admin user found!")

cursor.close()
conn.close()
