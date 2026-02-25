"""
Test Welcome Email Functionality
Tests if welcome email is sent correctly to new users
"""
from core.notifications import NotificationService
from core import config

# Create notification service
notification_service = NotificationService(config, use_database=False)

print("=" * 60)
print("  📧 Welcome Email Test - India Edition 🇮🇳")
print("=" * 60)
print()

# Test data
test_user = {
    'name': 'Rajesh Kumar',
    'email': 'anandhushibu64@gmail.com',  # Your registered email
    'role': 'user'
}

print(f"Testing welcome email for:")
print(f"  Name: {test_user['name']}")
print(f"  Email: {test_user['email']}")
print(f"  Role: {test_user['role']}")
print()

print("🔄 Sending welcome email...")
result = notification_service.send_welcome_email(
    test_user['name'],
    test_user['email'],
    test_user['role']
)

print()
if result:
    print("=" * 60)
    print("✅ SUCCESS! Welcome email sent!")
    print("=" * 60)
    print()
    print("📬 Check your inbox:")
    print(f"   {test_user['email']}")
    print()
    print("📋 Email details:")
    print(f"   From: {config.SMTP_USERNAME}")
    print(f"   Subject: Welcome to Drowning Detection System - India 🇮🇳")
    print()
    print("⚠️  If you don't see it, check:")
    print("   • Spam/Junk folder")
    print("   • Promotions tab (Gmail)")
    print()
else:
    print("=" * 60)
    print("❌ FAILED to send welcome email")
    print("=" * 60)
    print()
    print("Please check:")
    print("  • SMTP credentials in config.py")
    print("  • Internet connection")
    print("  • Email address format")
