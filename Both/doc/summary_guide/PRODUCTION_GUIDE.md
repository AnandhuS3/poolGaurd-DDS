# Production-Ready Features Guide - India Edition 🇮🇳

## 🚀 New Features Implemented

### 1. **Public User Registration**
- Users can now register themselves without admin intervention
- Registration page accessible at: `http://localhost:8000/register`
- Auto-login after successful registration
- Password strength requirements:
  - Minimum 8 characters
  - At least one uppercase letter
  - At least one digit

### 2. **User Roles**
The system now supports three roles:
- **Admin**: Full system access, can manage users
- **Guard**: Monitoring personnel, receives alerts
- **User**: Regular users who want to receive drowning alerts

### 3. **Broadcast Notifications**
- All logged-in users receive drowning alerts simultaneously
- Notifications sent via email to registered email addresses
- Future support for SMS/WhatsApp (infrastructure in place)

### 4. **Profile Management**
- Users can update their profile information
- Change password functionality
- Secure password hashing with bcrypt

## 📋 How It Works

### For End Users:

1. **Register an Account**
   - Go to `http://localhost:8000/register`
   - Fill in your details:
     - Full Name
     - Email (for receiving alerts)
     - Phone Number (for future SMS alerts)
     - Secure Password
   - Click "Create Account"
   - You'll be automatically logged in

2. **Receive Alerts**
   - Once registered and logged in, you'll automatically receive drowning alerts
   - Alerts are sent to your registered email
   - All logged-in users receive alerts simultaneously

3. **Monitor Video Feed**
   - After logging in, access the main dashboard
   - View live video processing
   - See real-time drowning detection

### For System Administrators:

1. **Initial Setup**
   ```bash
   # Update database schema
   python update_schema.py
   
   # Start the server
   python app.py
   ```

2. **Configure Email Notifications**
   Add to `config.py`:
   ```python
   # Email Notification Configuration
   NOTIFICATION_ENABLED = True
   NOTIFICATION_TYPE = "email"  # Options: email, sms, whatsapp
   
   # SMTP Settings (for Gmail)
   SMTP_SERVER = "smtp.gmail.com"
   SMTP_PORT = 587
   SMTP_USER = "your-email@gmail.com"
   SMTP_PASSWORD = "your-app-password"  # Use App Password, not regular password
   SENDER_EMAIL = "your-email@gmail.com"
   ```

3. **Manage Users**
   - Login as admin: `admin@dds.local` / `admin123`
   - Access admin panel at `/admin`
   - View all registered users
   - Activate/deactivate user accounts

## 🔐 Security Features

1. **Password Security**
   - Bcrypt hashing for password storage
   - Never stored in plain text
   - Strong password requirements enforced

2. **Session Management**
   - JWT-based authentication
   - 8-hour session expiration
   - One active session per user
   - Secure logout functionality

3. **Data Validation**
   - Email format validation
   - Phone number validation
   - Input sanitization
   - SQL injection prevention

## 📧 Email Notification Setup

### Gmail Setup (Recommended for India):

1. **Enable 2-Factor Authentication** on your Gmail account

2. **Generate App Password**:
   - Go to Google Account Settings
   - Security → 2-Step Verification → App passwords
   - Generate password for "Mail" application
   - Copy the 16-character password

3. **Update config.py**:
   ```python
   SMTP_USER = "your-email@gmail.com"
   SMTP_PASSWORD = "xxxx xxxx xxxx xxxx"  # App password
   ```

### SMS Setup for India:

**Popular Indian SMS Services:**
- **MSG91**: https://msg91.com/ (Indian company)
- **Kaleyra**: https://www.kaleyra.com/ (Good for bulk SMS)
- **Twilio India**: https://www.twilio.com/docs/usage/india-a2p-10dlc
- **Fast2SMS**: https://www.fast2sms.com/ (Budget option)

**WhatsApp Business API for India:**
- **Gupshup**: https://www.gupshup.io/
- **Interakt**: https://www.interakt.shop/
- **AiSensy**: https://aisensy.com/

### Production SMTP Services:
- **SendGrid**: Up to 100 emails/day free
- **Mailgun**: 5,000 emails/month free
- **Amazon SES**: Pay-as-you-go, very affordable

## 🔄 User Workflow Example

```
1. User visits website
   ↓
2. Clicks "Create Account"
   ↓
3. Fills registration form
   ↓
4. System validates & creates account
   ↓
5. Auto-login → Main dashboard
   ↓
6. System starts monitoring
   ↓
7. Drowning detected →  Alert sent to ALL logged-in users via email
   ↓
8. Users receive immediate notification
```

## 🛠️ API Endpoints

### Public Endpoints (No Authentication Required):
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login
- `GET /register` - Registration page
- `GET /login` - Login page

### Protected Endpoints (Authentication Required):
- `GET /api/auth/me` - Get current user info
- `PUT /api/auth/profile` - Update profile
- `POST /api/auth/change-password` - Change password
- `POST /api/auth/logout` - Logout
- `GET /` - Main dashboard (video monitoring)

### Admin Endpoints:
- `GET /admin` - Admin panel
- `POST /api/admin/users` - Create user (admin-only)
- `GET /api/admin/users` - List all users
- `PUT /api/admin/users/:id` - Update user
- `DELETE /api/admin/users/:id` - Deactivate user

## 📊 Database Schema Updates

The `users` table now supports three roles:
```sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(255),
    email VARCHAR(255) UNIQUE,
    phone_number VARCHAR(20),
    password_hash VARCHAR(255),
    role ENUM('admin', 'guard', 'user'),  -- NEW: added 'user' role
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## 🎯 Production Deployment Checklist

- [ ] Update `JWT_SECRET_KEY` in auth.py
- [ ] Configure email/SMS credentials
- [ ] Change default admin password
- [ ] Set up HTTPS/SSL certificate
- [ ] Configure firewall rules
- [ ] Set up database backups
- [ ] Enable logging and monitoring
- [ ] Test notification delivery
- [ ] Document emergency procedures
- [ ] Train users on system usage

## 🐛 Troubleshooting

### Users not receiving emails:
1. Check SMTP credentials in config.py
2. Verify email address is correct
3. Check spam folder
4. Ensure user is logged in
5. Check server logs for errors

### Registration fails:
1. Verify database is running
2. Check password meets requirements
3. Ensure email is not already registered
4. Check network connectivity

### Login issues:
1. Verify credentials are correct
2. Check if account is active
3. Clear browser cache/localStorage
4. Try different browser

## 📞 Support

For issues or questions:
1. Check logs in terminal
2. Review `doc/` folder for detailed documentation
3. Contact system administrator

---

**System Version**: v3.0 Production Ready - India Edition 🇮🇳
**Last Updated**: February 6, 2026
**Region**: India | **Timezone**: IST (GMT+5:30)
**Language**: English | **Phone Format**: +91 XXXXX XXXXX
