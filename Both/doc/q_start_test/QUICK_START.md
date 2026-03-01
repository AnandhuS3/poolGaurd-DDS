# Quick Start Guide - Authentication System

## Prerequisites
- Python 3.8+
- MySQL 8.0+
- All dependencies installed

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Database

Run the initialization script:

```bash
python init_database.py
```

Enter your MySQL credentials when prompted:
- Host: localhost (or your MySQL server)
- Port: 3306 (default)
- Username: root (or your MySQL user)
- Password: (your MySQL password)

The script will:
- Create `drowning_detection_db` database
- Create all required tables
- Set up indexes and constraints
- Create default admin user
- Display credentials

## Step 3: Update Configuration

Edit `config.py` and update the database section:

```python
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "root"          # Your MySQL username
DB_PASSWORD = "yourpass"  # Your MySQL password
DB_NAME = "drowning_detection_db"
```

## Step 4: Start the Application

```bash
python app.py
```

You should see:
```
============================================================
  🏊 Drowning Detection System with Authentication
============================================================

🌐 Server: http://0.0.0.0:8000
🔐 Login: http://localhost:8000/login
👤 Default admin: admin@dds.local / admin123
⚠️  CHANGE PASSWORD IMMEDIATELY!
```

## Step 5: First Login

1. Open browser: http://localhost:8000/login
2. Login with default credentials:
   - Email: `admin@dds.local`
   - Password: `admin123`

## Step 6: Change Admin Password

**IMPORTANT: Do this immediately!**

Option A - Via Admin Panel:
1. Go to http://localhost:8000/admin
2. Update your user profile with new password

Option B - Via Database:
```python
from auth import PasswordHasher
from database import db, User

# Generate new password hash
new_hash = PasswordHasher.hash_password("your_new_secure_password")

# Update in database
User.update(1, password_hash=new_hash)
```

## Step 7: Create Guard Users

1. Go to Admin Panel: http://localhost:8000/admin
2. Fill out "Create New User" form:
   - Name: Guard's full name
   - Email: guard@example.com
   - Phone: +1234567890
   - Role: Guard
   - Password: temporary_password (guard should change)
3. Click "Create User"
4. Provide credentials to the guard

## Step 8: Configure Notifications

Edit `config.py`:

```python
# Enable notifications
NOTIFICATION_ENABLED = True
NOTIFICATION_TYPE = "email"  # or "sms" or "whatsapp"

# Email configuration (for Gmail)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USERNAME = "your-email@gmail.com"
SMTP_PASSWORD = "your-app-password"  # Use App Password, not account password

# For Gmail App Password:
# 1. Go to Google Account settings
# 2. Security → 2-Step Verification (enable it)
# 3. Security → App passwords
# 4. Generate password for "Mail"
# 5. Use that 16-character password here
```

## Step 9: Test the System

### Test Login:
1. Logout if logged in
2. Login as admin
3. Verify you see admin panel link

### Test User Creation:
1. Create a test guard user
2. Logout
3. Login as the guard
4. Verify you DON'T see admin panel link

### Test Video Processing:
1. Upload a test video
2. Verify video processes
3. Check if you receive notifications (if configured)

### Test WebSocket:
1. Upload video via WebSocket
2. Should work with authentication token
3. Monitor console for any errors

## Common Issues

### "Database connection failed"
```bash
# Check MySQL is running
mysql --version

# Test connection manually
mysql -u root -p -h localhost

# If connection works, verify config.py credentials
```

### "Module not found" errors
```bash
# Reinstall dependencies
pip install -r requirements.txt --upgrade
```

### "Cannot access admin panel"
- Verify you're logged in as admin role
- Check browser console for errors
- Verify token in localStorage

### Notifications not working
- Check SMTP credentials
- Verify email/phone in user profile
- Ensure user is logged in when alert triggers
- Check notification logs in console

## Default Credentials

**Admin Account:**
- Email: admin@dds.local
- Password: admin123
- ⚠️ **CHANGE IMMEDIATELY IN PRODUCTION**

## URLs

- **Login Page:** http://localhost:8000/login
- **Main Monitoring:** http://localhost:8000/
- **Admin Panel:** http://localhost:8000/admin (admin only)
- **API Docs:** http://localhost:8000/docs (FastAPI auto-generated)

## Next Steps

1. ✅ Change default admin password
2. ✅ Create guard users
3. ✅ Configure notification settings
4. ✅ Test end-to-end workflow
5. ✅ Set up regular database backups
6. ✅ Review security settings for production

## Production Deployment

Before deploying to production:

1. **Environment Variables:** Move secrets to environment variables
2. **HTTPS:** Enable SSL/TLS
3. **CORS:** Restrict to production domain
4. **Backups:** Set up automated database backups
5. **Monitoring:** Enable application monitoring
6. **Logging:** Configure production logging
7. **Firewall:** Restrict database access

## Support

For detailed documentation, see:
- `AUTH_DOCUMENTATION.md` - Complete authentication system documentation
- `schema.sql` - Database schema with comments
- `README.md` - General system documentation

## Troubleshooting Commands

```bash
# Check Python version
python --version

# Check installed packages
pip list | grep -i "fastapi\|mysql\|jwt\|bcrypt"

# Test MySQL connection
python -c "import mysql.connector; print('MySQL module OK')"

# Test database connection
python -c "from database import db; print('Database module OK')"

# View logs
# (Application prints to console by default)

# Reset database (CAUTION: deletes all data)
mysql -u root -p -e "DROP DATABASE IF EXISTS drowning_detection_db;"
python init_database.py
```

---

**You're now ready to use the Drowning Detection System with secure authentication!**
