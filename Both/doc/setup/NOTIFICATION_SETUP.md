# 🚨 Notification System Setup Guide

## Overview

The drowning detection system includes a safety-critical notification system that alerts responsible personnel when a DANGER state is detected, even if the web UI is closed.

## Features

✅ **Per-Person State Machine**: SAFE → WARNING → DANGER  
✅ **Frame-Based Timing**: Accurate detection based on video frames (not wall-clock time)  
✅ **No State Flapping**: Once DANGER, stays DANGER until manual reset  
✅ **Local Audio Alerts**: Plays alarm sound in browser  
✅ **Remote Notifications**: Email, SMS, or WhatsApp alerts  
✅ **Non-Blocking**: Notifications don't impact processing speed  
✅ **Failure-Safe**: Processing continues even if notifications fail  

---

## State Machine Behavior

### States

1. **SAFE** (Green) - Person swimming normally
2. **WARNING** (Orange) - Distress detected for ≥2 seconds - **⚠️ ALARM & NOTIFICATION TRIGGERED**
3. **DANGER** (Red) - Sustained distress for ≥5 seconds - **🚨 ALARM & NOTIFICATION TRIGGERED**

### Transitions

```
SAFE → WARNING (distress detected, ≥2 seconds) → 🔊 ALARM + 📧 NOTIFICATION
WARNING → DANGER (sustained distress, ≥5 seconds) → 🔊 ALARM + 📧 NOTIFICATION
WARNING → SAFE (recovery after 3 seconds without distress)
DANGER → [STICKY] (never auto-recovers, requires manual reset)
```

### Notification Behavior

- **WARNING state**: Alarm plays + notification sent (once per person)
- **DANGER state**: Alarm plays again + separate notification sent
- **Each state triggers independently**: You get 2 alerts total (WARNING + DANGER)
- **No repeated alerts**: Each person triggers alarm once per state

### Design Rationale

- **Alerts on WARNING**: Early intervention - notify staff immediately when distress detected
- **Alerts on DANGER**: Critical escalation - person needs immediate rescue
- **Separate alerts per state**: Two opportunities to respond (2s and 5s thresholds)
- **No DANGER→WARNING/SAFE**: Once critical state reached, human intervention required
- **Frame-based timing**: Immune to processing delays or frame skipping
- **3-second recovery grace**: Prevents false alarms from brief splashing

---

## Audio Alert Setup

### Automatic Configuration

The audio alert system is **already configured** and requires no setup:

1. Audio file: `/sounds/alarm.mp3` ✅ (already present)
2. HTML audio element ✅ (automatically added)
3. Play on DANGER ✅ (implemented)
4. One alert per person ✅ (no repeats)

### Browser Compatibility

**Important**: Modern browsers block autoplay of audio. Users must interact with the page first (click Start Analysis).

If audio doesn't play:
- Check browser console for autoplay errors
- Ensure user has clicked something on the page
- Visual alert will show: "🔊 ALARM: Enable sound for audio alerts!"

---

## Remote Notification Setup

### Step 1: Choose Notification Type

Edit `config.py`:

```python
# Enable notifications
NOTIFICATION_ENABLED = True

# Choose one: "email", "sms", or "whatsapp"
NOTIFICATION_TYPE = "email"

# Camera identifier for alerts
CAMERA_NAME = "Main Pool Camera"
```

### Step 2: Configure Notification Channel

Choose ONE of the following:

---

### Option A: Email Notifications (RECOMMENDED)

**Easiest to set up, no additional dependencies**

#### Gmail Configuration

1. **Enable 2-Step Verification** in your Google Account
2. **Generate App Password**:
   - Go to: https://myaccount.google.com/apppasswords
   - Select "Mail" and "Other"
   - Name it "PoolGuard"
   - Copy the 16-character password

3. **Update config.py**:

```python
NOTIFICATION_TYPE = "email"

# Email Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your-email@gmail.com"
SMTP_PASSWORD = "your-16-char-app-password"  # NOT your regular password
SMTP_FROM_EMAIL = "your-email@gmail.com"

# Recipients
NOTIFICATION_RECIPIENTS = [
    "lifeguard1@example.com",
    "manager@example.com"
]
```

#### Other Email Providers

**Outlook/Office365**:
```python
SMTP_SERVER = "smtp-mail.outlook.com"
SMTP_PORT = 587
```

**Yahoo Mail**:
```python
SMTP_SERVER = "smtp.mail.yahoo.com"
SMTP_PORT = 587
```

**Custom SMTP**:
```python
SMTP_SERVER = "your-smtp-server.com"
SMTP_PORT = 587  # or 465 for SSL
```

---

### Option B: SMS Notifications

**Requires Twilio account and paid credits**

1. **Install Twilio SDK**:
```bash
pip install twilio
```

2. **Sign up for Twilio**:
   - Go to: https://www.twilio.com/try-twilio
   - Get $15 free trial credit
   - Buy a phone number ($1-2/month)

3. **Get Credentials**:
   - Account SID: Dashboard → Account Info
   - Auth Token: Dashboard → Account Info
   - Phone Number: Phone Numbers → Manage Numbers

4. **Update config.py**:

```python
NOTIFICATION_TYPE = "sms"

# Twilio Configuration
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_auth_token"
TWILIO_FROM_NUMBER = "+1234567890"  # Your Twilio number

# Recipients (include country code)
NOTIFICATION_RECIPIENTS = [
    "+1234567890",  # Lifeguard
    "+0987654321"   # Manager
]
```

---

### Option C: WhatsApp Notifications

**Requires Twilio account with WhatsApp enabled**

1. **Install Twilio SDK** (if not done):
```bash
pip install twilio
```

2. **Enable WhatsApp** in Twilio:
   - Go to Twilio Console → Messaging → Try it out → Send a WhatsApp message
   - Follow sandbox setup instructions
   - Have recipients send "join <your-sandbox-code>" to +1 415 523 8886

3. **Update config.py**:

```python
NOTIFICATION_TYPE = "whatsapp"

# Twilio Configuration
TWILIO_ACCOUNT_SID = "ACxxxxxxxxxxxxxxxxxxxxx"
TWILIO_AUTH_TOKEN = "your_auth_token"
TWILIO_WHATSAPP_FROM = "whatsapp:+14155238886"  # Twilio sandbox

# Recipients (will be auto-prefixed with whatsapp:)
NOTIFICATION_RECIPIENTS = [
    "+1234567890",
    "+0987654321"
]
```

**Note**: Twilio sandbox has limitations. For production, apply for WhatsApp Business API access.

---

## Step 3: Test Notifications

### Test Script

Create `test_notification.py`:

```python
from notifications import create_notification_service
from config import *
import asyncio

async def test():
    config = {
        "NOTIFICATION_ENABLED": NOTIFICATION_ENABLED,
        "NOTIFICATION_TYPE": NOTIFICATION_TYPE,
        "CAMERA_NAME": CAMERA_NAME,
        "NOTIFICATION_RECIPIENTS": NOTIFICATION_RECIPIENTS,
        "SMTP_SERVER": SMTP_SERVER,
        "SMTP_PORT": SMTP_PORT,
        "SMTP_USERNAME": SMTP_USERNAME,
        "SMTP_PASSWORD": SMTP_PASSWORD,
        "SMTP_FROM_EMAIL": SMTP_FROM_EMAIL,
    }
    
    service = create_notification_service(config)
    await service.send_alert(
        track_id=999,
        severity="DANGER",
        camera_name="Test Camera"
    )
    print("✓ Test notification sent!")

asyncio.run(test())
```

Run:
```bash
python test_notification.py
```

---

## Troubleshooting

### Audio Doesn't Play

**Problem**: No sound when DANGER detected  
**Solutions**:
- Click anywhere on the page before starting analysis (browser autoplay policy)
- Check browser console for errors
- Verify `/sounds/alarm.mp3` exists
- Try different browser (Chrome/Firefox recommended)

### Email Notifications Fail

**Problem**: "Authentication failed" error  
**Solutions**:
- Gmail: Use App Password, not regular password
- Enable "Less secure app access" (if available)
- Check SMTP server and port
- Verify email/password in config.py

**Problem**: "Connection refused"  
**Solutions**:
- Check firewall allows outbound SMTP (port 587/465)
- Try different SMTP port
- Verify SMTP_SERVER address

### SMS/WhatsApp Notifications Fail

**Problem**: "Twilio not installed"  
**Solution**: `pip install twilio`

**Problem**: "Invalid credentials"  
**Solutions**:
- Verify Account SID and Auth Token
- Check they're copied correctly (no extra spaces)
- Regenerate Auth Token if needed

**Problem**: "Invalid phone number"  
**Solutions**:
- Include country code (+1 for US)
- Use E.164 format: +[country][number]
- Verify number is SMS-capable

### Notifications Not Sending

**Problem**: No errors, but no notifications received  
**Solutions**:
- Check `NOTIFICATION_ENABLED = True` in config.py
- Verify recipients list is not empty
- Check spam/junk folder (email)
- Verify phone number is correct (SMS/WhatsApp)
- Check Twilio account has credits

### Processing Slow After Enabling Notifications

**This should NEVER happen** - notifications are non-blocking.

If it does:
- Check logs for repeated notification failures
- Verify SMTP server responds quickly
- Consider switching to async-capable SMTP server

---

## Security Best Practices

### 1. Protect Credentials

**Never commit credentials to git**:

```bash
# Add to .gitignore
config.py
*.env
```

Use environment variables:

```python
import os

SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
```

### 2. Email Security

- Use App Passwords instead of main password
- Enable 2FA on email account
- Limit SMTP access to specific IPs if possible

### 3. Twilio Security

- Rotate Auth Tokens periodically
- Set up usage alerts
- Use webhook authentication for callbacks

---

## Production Deployment

### Recommended Setup

1. **Email for primary alerts** (reliable, free, easy)
2. **SMS for critical escalation** (immediate, hard to miss)
3. **WhatsApp for teams** (group notifications, rich media)

### Multiple Recipients

```python
NOTIFICATION_RECIPIENTS = [
    "on-duty-lifeguard@pool.com",  # Primary
    "supervisor@pool.com",          # Backup
    "emergency-contact@pool.com"    # Escalation
]
```

### Load Testing

Before production, test with:
- Multiple simultaneous DANGER states
- Rapid state transitions
- Network disconnections
- SMTP server downtime

Verify:
- Processing continues uninterrupted
- No duplicate notifications
- Failures logged but not crashing

---

## Monitoring & Logs

### Log Locations

- **Application log**: `drowning_detection.log`
- **Notification events**: Search for `[NOTIFICATION]`
- **State changes**: Search for `[WARNING SYSTEM]`

### Key Log Patterns

**Successful notification**:
```
[NOTIFICATION] ✓ Sent DANGER alert for Person #3 via email
```

**Failed notification** (safe):
```
[NOTIFICATION] ✗ Failed to send alert: Connection refused
```

**State transitions**:
```
[WARNING SYSTEM] Person #3: SAFE → WARNING
[WARNING SYSTEM] Person #3: WARNING → DANGER
```

---

## FAQ

**Q: Can I use multiple notification types simultaneously?**  
A: Not in current version. Choose one primary type. Contact us for multi-channel support.

**Q: What happens if notification fails?**  
A: Error is logged, processing continues. Alert is NOT retried (prevents spam).

**Q: Can I customize alert messages?**  
A: Yes, edit `_format_message()` in `notifications.py`.

**Q: How do I add more recipients?**  
A: Add to `NOTIFICATION_RECIPIENTS` list in config.py.

**Q: Does this work with IP cameras?**  
A: Not yet. Currently only uploaded videos. Live camera support coming soon.

**Q: Can I test without triggering real notifications?**  
A: Set `NOTIFICATION_ENABLED = False` in config.py.

---

## Support

For issues:
1. Check logs in `drowning_detection.log`
2. Review this guide
3. Test with `test_notification.py`
4. Check Twilio/email provider status pages

**Emergency Support**: If notifications aren't working in production, immediately:
1. Disable notifications: `NOTIFICATION_ENABLED = False`
2. Ensure audio alerts still work
3. Post lifeguard to monitor UI directly
4. Debug offline

**System is designed to fail safe**: Detection works even if notifications are broken.
