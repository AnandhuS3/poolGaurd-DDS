import psycopg2
import sys
sys.path.append('.')
from core.auth import PasswordHasher

conn = psycopg2.connect('dbname=poolguard_db user=postgres password=root12 host=localhost')
cursor = conn.cursor()
cursor.execute("SELECT email, password_hash, is_active FROM users WHERE email='creagoouon@gmail.com'")
res = cursor.fetchone()
if res:
    print(f"Email: {res[0]}")
    print(f"is_active: {res[2]}")
    print(f"admin123 valid: {PasswordHasher.verify_password('admin123', res[1])}")
    print(f"Admin1234 valid: {PasswordHasher.verify_password('Admin1234', res[1])}")
else:
    print("User not found")
