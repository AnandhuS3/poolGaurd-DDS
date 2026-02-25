"""
Create User Script
Utility to create users from command line
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.database import db, User
from core.auth import PasswordHasher
from core.config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_POOL_SIZE

def create_user():
    """Interactive user creation"""
    print("=" * 60)
    print("  Create New User - Drowning Detection System")
    print("=" * 60)
    print()
    
    # Initialize database
    try:
        db.initialize(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            pool_size=DB_POOL_SIZE
        )
        print("✅ Connected to database\n")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    # Get user details
    print("Enter user details:")
    name = input("Full Name: ").strip()
    email = input("Email: ").strip()
    phone = input("Phone Number (e.g., +1234567890): ").strip()
    
    # Role selection
    print("\nSelect Role:")
    print("1. Guard")
    print("2. Admin")
    role_choice = input("Choice [1]: ").strip() or "1"
    role = "admin" if role_choice == "2" else "guard"
    
    # Password
    password = input("Password (min 8 chars): ").strip()
    if len(password) < 8:
        print("❌ Password must be at least 8 characters!")
        return
    
    # Confirm
    print(f"\n📝 User Details:")
    print(f"   Name: {name}")
    print(f"   Email: {email}")
    print(f"   Phone: {phone}")
    print(f"   Role: {role.upper()}")
    
    confirm = input("\nCreate this user? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("❌ Cancelled")
        return
    
    # Check if email exists
    existing = User.get_by_email(email)
    if existing:
        print(f"❌ User with email '{email}' already exists!")
        return
    
    # Hash password
    print("\n🔄 Hashing password...")
    password_hash = PasswordHasher.hash_password(password)
    
    # Create user
    print("🔄 Creating user...")
    user_id = User.create(
        name=name,
        email=email,
        phone_number=phone,
        password_hash=password_hash,
        role=role,
        is_active=True
    )
    
    if user_id:
        print(f"\n✅ User created successfully!")
        print(f"   User ID: {user_id}")
        print(f"\n📧 Login Credentials:")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"\n⚠️  Provide these credentials to the user securely.")
    else:
        print("\n❌ Failed to create user!")

if __name__ == "__main__":
    try:
        create_user()
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
