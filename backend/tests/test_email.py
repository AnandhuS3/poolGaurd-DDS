"""
Email Notification Test Script
Tests if your SMTP configuration can send real emails
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Import from config
from core.config import (
    SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, 
    NOTIFICATION_RECIPIENTS
)

def test_email_notification():
    """Test sending a real email notification"""
    
    print("=" * 60)
    print("  📧 Email Notification Test - PoolGaurd")
    print("=" * 60)
    print()
    
    # Check configuration
    print("Configuration Check:")
    print(f"  SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
    print(f"  From Email: {SMTP_USERNAME}")
    print(f"  Test Recipients: {NOTIFICATION_RECIPIENTS}")
    print()
    
    if not SMTP_USERNAME or not SMTP_PASSWORD:
        print("❌ ERROR: SMTP credentials not configured!")
        print("   Please update SMTP_USERNAME and SMTP_PASSWORD in config.py")
        return False
    
    # Create test email
    try:
        print("🔄 Connecting to SMTP server...")
        
        msg = MIMEMultipart()
        msg['From'] = SMTP_USERNAME
        msg['To'] = ', '.join(NOTIFICATION_RECIPIENTS)
        msg['Subject'] = "🏊 Test Alert - PoolGaurd Drowning Detection System"
        
        # Create HTML email body
        timestamp = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p IST")
        
        html_body = f"""
        <html>
            <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin-bottom: 20px;">
                    <h2 style="color: #1976d2; margin: 0;">✅ Email Test Successful!</h2>
                </div>
                
                <p><strong>This is a test message from your Drowning Detection System.</strong></p>
                
                <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p><strong>Test Details:</strong></p>
                    <ul>
                        <li>🕐 Time: {timestamp}</li>
                        <li>📍 System: PoolGaurd</li>
                        <li>📧 SMTP: {SMTP_SERVER}</li>
                        <li>📤 From: {SMTP_USERNAME}</li>
                        <li>📥 To: {', '.join(NOTIFICATION_RECIPIENTS)}</li>
                    </ul>
                </div>
                
                <p><strong>✨ Your email notifications are working!</strong></p>
                <p>When drowning is detected, alerts will be sent to all logged-in users automatically.</p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #ddd;">
                
                <p style="color: #666; font-size: 12px;">
                    This is an automated test from the Drowning Detection System<br>
                    PoolGaurd - Drowning Detection System
                </p>
            </body>
        </html>
        """
        
        msg.attach(MIMEText(html_body, 'html'))
        
        # Send email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=10) as server:
            server.starttls()
            print(f"🔐 Authenticating as {SMTP_USERNAME}...")
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            print("📤 Sending test email...")
            server.send_message(msg)
        
        print()
        print("=" * 60)
        print("✅ SUCCESS! Test email sent successfully!")
        print("=" * 60)
        print()
        print("📬 Check your inbox:")
        for email in NOTIFICATION_RECIPIENTS:
            print(f"   • {email}")
        print()
        print("⚠️  If you don't see it, check your:")
        print("   • Spam/Junk folder")
        print("   • Promotions tab (Gmail)")
        print("   • Email filters")
        print()
        print("🎉 Your drowning detection alerts will work!")
        print("   When users are logged in and drowning is detected,")
        print("   they will receive alerts just like this test email.")
        print()
        
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print()
        print("❌ AUTHENTICATION FAILED!")
        print()
        print("Possible issues:")
        print("  1. Wrong password - check SMTP_PASSWORD in config.py")
        print("  2. Need to enable 'Less secure app access' (old Gmail)")
        print("  3. Need to generate 'App Password' (recommended)")
        print()
        print("📘 How to fix (Gmail):")
        print("  1. Go to Google Account Settings")
        print("  2. Security → 2-Step Verification")
        print("  3. Generate 'App Password' for Mail")
        print("  4. Copy the 16-character password")
        print("  5. Update SMTP_PASSWORD in config.py")
        print()
        print(f"Error details: {e}")
        return False
        
    except smtplib.SMTPException as e:
        print()
        print(f"❌ SMTP ERROR: {e}")
        print()
        print("Check your:")
        print("  • SMTP server address and port")
        print("  • Internet connection")
        print("  • Firewall settings")
        return False
        
    except Exception as e:
        print()
        print(f"❌ UNEXPECTED ERROR: {e}")
        print()
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_email_notification()
