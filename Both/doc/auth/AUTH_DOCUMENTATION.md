# Authentication System Documentation
# Drowning Detection System

## Overview

This document describes the secure, role-based authentication system for the Drowning Detection System. The system uses JWT-based authentication backed by MySQL to manage users, sessions, and alert notifications.

---

## Architecture

### Components

1. **Database Layer** (`database.py`)
   - MySQL connection pooling
   - Data models: User, Session, Alert, AuditLog
   - CRUD operations with transactions

2. **Authentication Layer** (`auth.py`)
   - JWT token generation and validation
   - bcrypt password hashing
   - Role-based access control (RBAC)
   - Authentication middleware

3. **Notification Layer** (`notifications.py`)
   - Authentication-aware notifications
   - Sends alerts only to logged-in users
   - Escalates to admin if no guard is active

4. **API Layer** (`app.py`)
   - Protected endpoints (requires authentication)
   - Admin-only endpoints
   - WebSocket authentication

5. **Frontend Layer** (`client/`)
   - Login page (`login.html`)
   - Admin panel (`admin.html`)
   - Main monitoring interface (`index.html`)

---

## System Roles

### Admin
**Capabilities:**
- Create, update, and deactivate users
- Assign roles (Admin/Guard)
- View all alerts and history
- Access admin panel
- Monitor all active sessions
- Configure system settings

**Access:**
- All monitoring features
- User management panel
- System configuration
- Full audit logs

### Guard
**Capabilities:**
- Log in to operate the monitoring system
- Process and monitor video feeds
- Receive drowning alerts (only when logged in)

**Access:**
- Video upload and processing
- Real-time monitoring
- Alert viewing (their own alerts only)

---

## Data Flow

### 1. Login Flow
```
User enters credentials
  ↓
POST /api/auth/login
  ↓
Verify email & password (bcrypt)
  ↓
Check user is_active status
  ↓
Create session in active_sessions table
  ↓
Generate JWT token (expires in 8 hours)
  ↓
Return token + user info
  ↓
Frontend stores token in localStorage
  ↓
Log audit event (LOGIN_SUCCESS)
```

### 2. Monitoring Flow
```
User accesses monitoring page
  ↓
Frontend checks for auth_token in localStorage
  ↓
No token → Redirect to /login
  ↓
Has token → Include in Authorization header
  ↓
Backend: Validate JWT token
  ↓
Backend: Check active session exists
  ↓
Token valid → Allow access
  ↓
Token invalid/expired → Return 401 Unauthorized
  ↓
Frontend: Clear token, redirect to login
```

### 3. Alert Notification Flow
```
Drowning detected by AI model
  ↓
Query active_sessions for logged-in guards
  ↓
Active guard found?
  ├─ YES → Send alert to guard
  │         Create alert record (user_id = guard_id)
  │         Send via email/SMS to guard's contact
  │         Log in database
  │
  └─ NO  → Escalate to admin
            Find first active admin
            Create alert record (escalated_to_admin = TRUE)
            Send via email/SMS to admin's contact
            Log escalation event
  ↓
Continue monitoring (non-blocking)
```

### 4. WebSocket Authentication Flow
```
Client connects to ws://server/ws/process?token=<JWT>
  ↓
Server extracts token from query parameter
  ↓
Validate JWT token
  ↓
Check user has active session
  ↓
Check user role (guard or admin)
  ↓
Token valid → Accept WebSocket connection
  ↓
Token invalid → Close connection (code 1008)
  ↓
Process video stream with authenticated context
```

### 5. Logout Flow
```
User clicks logout
  ↓
POST /api/auth/logout (with token)
  ↓
Backend validates token
  ↓
Deactivate all active sessions for user
  ↓
Set logout_time in active_sessions
  ↓
Log audit event (LOGOUT)
  ↓
Frontend clears localStorage
  ↓
Redirect to /login
```

---

## Database Schema

### users
Stores all system users (Admin and Guard)

| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | User ID |
| name | VARCHAR(255) | Full name |
| email | VARCHAR(255) UNIQUE | Email address (login) |
| phone_number | VARCHAR(20) | Contact number |
| password_hash | VARCHAR(255) | bcrypt hashed password |
| role | ENUM('admin', 'guard') | User role |
| is_active | BOOLEAN | Account status |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### active_sessions
Tracks currently logged-in users

| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Session ID |
| user_id | INT (FK) | User ID |
| login_time | TIMESTAMP | Login timestamp |
| logout_time | TIMESTAMP | Logout timestamp (NULL if active) |
| is_active | BOOLEAN | Session status |
| ip_address | VARCHAR(45) | Client IP address |
| user_agent | TEXT | Client user agent |

**Business Rules:**
- Only ONE active session per user at a time
- Old sessions are auto-deactivated on new login
- Sessions expire after 8 hours (JWT expiration)

### alerts
Records all drowning detection events

| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Alert ID |
| user_id | INT (FK) | Assigned user ID (nullable) |
| track_id | INT | Person tracking ID |
| alert_type | ENUM('warning', 'danger') | Alert severity |
| triggered_at | TIMESTAMP | Alert timestamp |
| resolved_at | TIMESTAMP | Resolution timestamp |
| notification_sent | BOOLEAN | Notification status |
| notification_method | VARCHAR(50) | email/sms/whatsapp |
| escalated_to_admin | BOOLEAN | Escalation flag |
| camera_name | VARCHAR(255) | Camera identifier |

### audit_logs
Security and compliance logging

| Column | Type | Description |
|--------|------|-------------|
| id | INT (PK) | Log ID |
| user_id | INT (FK) | User ID (nullable) |
| action | VARCHAR(100) | Action type |
| details | TEXT | Additional details |
| ip_address | VARCHAR(45) | Client IP |
| created_at | TIMESTAMP | Event timestamp |

**Logged Actions:**
- LOGIN_SUCCESS, LOGIN_FAILED
- LOGOUT
- USER_CREATED, USER_UPDATED
- ALERT_SENT
- NOTIFICATION_FAILED

---

## API Endpoints

### Authentication Endpoints

#### POST /api/auth/login
Login and receive JWT token

**Request:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "name": "John Doe",
    "email": "user@example.com",
    "phone_number": "+1234567890",
    "role": "guard",
    "is_active": true
  }
}
```

#### POST /api/auth/logout
Logout and deactivate session

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Logged out successfully"
}
```

#### GET /api/auth/me
Get current user information

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 1,
  "name": "John Doe",
  "email": "user@example.com",
  "phone_number": "+1234567890",
  "role": "guard",
  "is_active": true
}
```

### Admin Endpoints (Admin Only)

#### POST /api/admin/users
Create new user

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Request:**
```json
{
  "name": "Jane Smith",
  "email": "jane@example.com",
  "phone_number": "+0987654321",
  "password": "secure_password123",
  "role": "guard"
}
```

#### GET /api/admin/users
List all users

**Headers:**
```
Authorization: Bearer <admin_token>
```

#### PATCH /api/admin/users/{user_id}
Update user

**Headers:**
```
Authorization: Bearer <admin_token>
```

**Request:**
```json
{
  "name": "Updated Name",
  "is_active": false
}
```

#### GET /api/admin/sessions
List active sessions

**Headers:**
```
Authorization: Bearer <admin_token>
```

#### GET /api/admin/alerts?limit=100
List all alerts

**Headers:**
```
Authorization: Bearer <admin_token>
```

### Protected Endpoints (Guard/Admin)

All existing video processing endpoints now require authentication:

- POST /analyze/upload
- POST /analyze/youtube
- GET /video/{filename}
- GET /download/{filename}
- WS /ws/process?token=<jwt>

---

## Security Features

### Password Security
- **Hashing:** bcrypt with cost factor 12
- **Minimum length:** 8 characters
- **Storage:** Only hashed passwords stored
- **Validation:** Constant-time comparison

### JWT Security
- **Algorithm:** HS256 (HMAC with SHA-256)
- **Expiration:** 8 hours
- **Claims:**
  - `sub`: User ID
  - `email`: User email
  - `role`: User role
  - `exp`: Expiration timestamp
  - `iat`: Issued at timestamp

### Session Management
- **Single session:** Only one active session per user
- **Auto-cleanup:** Old sessions removed after 30 days
- **Session tracking:** IP address and user agent logged
- **Logout:** Immediately deactivates all user sessions

### API Protection
- **Authentication required:** All video processing endpoints
- **Role-based access:** Admin endpoints restricted
- **WebSocket auth:** Token validation before connection
- **CORS:** Configured for web access
- **Error handling:** No sensitive data in error messages

---

## Frontend Integration

### localStorage Usage

```javascript
// Store after login
localStorage.setItem('auth_token', data.access_token);
localStorage.setItem('user_info', JSON.stringify(data.user));

// Retrieve for API calls
const token = localStorage.getItem('auth_token');
const headers = {
    'Authorization': `Bearer ${token}`
};

// Clear on logout
localStorage.removeItem('auth_token');
localStorage.removeItem('user_info');
```

### API Call Example

```javascript
async function uploadVideo(file) {
    const token = localStorage.getItem('auth_token');
    
    if (!token) {
        window.location.href = '/login';
        return;
    }
    
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch('/analyze/upload', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        },
        body: formData
    });
    
    if (response.status === 401) {
        // Token expired or invalid
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
        return;
    }
    
    const data = await response.json();
    // Process response...
}
```

### WebSocket Connection

```javascript
const token = localStorage.getItem('auth_token');
const ws = new WebSocket(`ws://localhost:8000/ws/process?token=${token}`);

ws.onopen = () => {
    console.log('Connected to video processing');
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    // May indicate authentication failure
};
```

---

## Installation & Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install MySQL

Ensure MySQL 8.0+ is installed and running.

### 3. Initialize Database

```bash
python init_database.py
```

Follow the prompts to enter MySQL credentials.

### 4. Update Configuration

Edit `config.py`:

```python
# Database Configuration
DB_HOST = "localhost"
DB_PORT = 3306
DB_USER = "your_mysql_user"
DB_PASSWORD = "your_mysql_password"
DB_NAME = "drowning_detection_db"
DB_POOL_SIZE = 5
```

### 5. Change Default Admin Password

1. Login with default credentials:
   - Email: `admin@dds.local`
   - Password: `admin123`

2. Immediately change via admin panel or directly in database:

```python
from auth import PasswordHasher

new_password_hash = PasswordHasher.hash_password("your_secure_password")
# Update in database
```

### 6. Start Application

```bash
python app.py
```

Access at:
- Login: http://localhost:8000/login
- Admin Panel: http://localhost:8000/admin
- Monitoring: http://localhost:8000/

---

## Usage Workflows

### For Administrators

1. **Login** at `/login` with admin credentials
2. **Create Users** via Admin Panel (`/admin`)
   - Enter name, email, phone, password, role
   - Users receive credentials to log in
3. **Manage Users**
   - Activate/Deactivate accounts
   - Update user information
   - View active sessions
4. **Monitor Alerts**
   - View all alerts across all users
   - Check escalated alerts (no guard logged in)
   - Review audit logs

### For Guards

1. **Login** at `/login` with provided credentials
2. **Access Monitoring** at `/`
   - Upload video or YouTube link
   - Monitor real-time detection
3. **Receive Alerts**
   - Alerts sent to registered email/phone
   - Only while logged in and active
4. **Logout** when shift ends
   - Alerts will escalate to admin

---

## Notification Logic

The system sends notifications ONLY to currently logged-in users:

### Scenario 1: Guard is Logged In
```
Drowning detected
  ↓
Check active_sessions for guards
  ↓
Guard found (John Doe, logged in 2 hours ago)
  ↓
Send email to: john.doe@example.com
Send SMS to: +1234567890
  ↓
Create alert record:
  - user_id: 5 (John Doe)
  - escalated_to_admin: FALSE
```

### Scenario 2: No Guard Logged In
```
Drowning detected
  ↓
Check active_sessions for guards
  ↓
No guards found
  ↓
Escalate to admin
  ↓
Find first active admin (Admin A)
  ↓
Send email to: admin@dds.local
Send SMS to: +9876543210
  ↓
Create alert record:
  - user_id: 1 (Admin A)
  - escalated_to_admin: TRUE
```

### Scenario 3: Multiple Guards Logged In
```
Uses FIFO (First In First Out)
  ↓
Guard who logged in first receives alert
  ↓
Ensures fair distribution
```

---

## Troubleshooting

### "Database connection failed"
- Verify MySQL is running
- Check credentials in `config.py`
- Ensure database exists: `drowning_detection_db`
- Check firewall allows MySQL port 3306

### "401 Unauthorized"
- Token may have expired (8-hour limit)
- User may have been logged out by admin
- Clear localStorage and login again

### "No active session"
- User was logged out
- Another login from different location
- Only one session per user allowed

### "Notification not received"
- Verify email/SMS credentials in `config.py`
- Check user's email/phone in database
- Ensure user was logged in when alert triggered
- Check audit_logs for notification failures

### "Cannot access admin panel"
- User role must be 'admin'
- Check user role in database
- Login with correct admin credentials

---

## Best Practices

### Security
1. **Change default admin password immediately**
2. **Use strong passwords** (minimum 12 characters, mixed case, numbers, symbols)
3. **Store JWT_SECRET_KEY in environment variable** (not in code)
4. **Use HTTPS in production**
5. **Regularly review audit logs**
6. **Deactivate users** when they leave (don't delete)

### Operations
1. **Guards must logout** after shift ends
2. **Admin should monitor active sessions** regularly
3. **Review escalated alerts** to ensure coverage
4. **Regular database backups**
5. **Clean up old sessions** periodically (automated in schema)

### Database
1. **Use connection pooling** (already configured)
2. **Index frequently queried fields** (already configured)
3. **Regular backups** of drowning_detection_db
4. **Monitor query performance**
5. **Archive old alerts** after 90 days (configurable)

---

## Production Deployment Checklist

- [ ] Change default admin password
- [ ] Move JWT_SECRET_KEY to environment variable
- [ ] Configure SMTP credentials for email notifications
- [ ] Set up SMS provider (Twilio) if using SMS
- [ ] Enable HTTPS (SSL/TLS)
- [ ] Configure CORS for production domain only
- [ ] Set up database backups
- [ ] Configure firewall rules
- [ ] Set session timeout appropriately
- [ ] Enable logging to file
- [ ] Set up monitoring/alerting for system health
- [ ] Document user credentials securely
- [ ] Train users on login/logout procedures

---

## Support & Maintenance

For issues or questions:
1. Check audit_logs table for error details
2. Review application logs
3. Verify database connectivity
4. Check user permissions and roles
5. Ensure sessions are active

---

## Version History

- **v3.0** (2026-02-06): Added authentication, role-based access, MySQL integration
- **v2.0**: Real-time video processing with WebSocket
- **v1.0**: Initial drowning detection system

---

End of Documentation
