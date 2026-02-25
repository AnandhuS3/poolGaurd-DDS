# Admin Panel Architecture - Root Cause Analysis

**Date:** February 15, 2026  
**Analysis Type:** Pre-Implementation Root Cause Investigation

---

## IDENTIFIED ISSUES

### Issue 1: System Administrator in Regular User List ❌

**Current Behavior:**
- System Administrator appears in regular user management table
- Has Delete button like normal users
- No protection against deletion
- Mixed with guard/admin users

**Root Causes:**
1. **No DB-level distinction:** `users` table has no `is_system_admin` flag
2. **No backend filtering:** `GET /api/admin/users` returns ALL users including system admin
3. **No frontend separation:** admin.html renders all users in single table
4. **No deletion protection:** Backend allows deletion of any user except self

**Evidence:**
- `database/schema.sql:119` - System Administrator created as regular admin
- `core/app.py:304-308` - `list_users()` returns `User.get_all()` without filtering
- `frontend/admin.html:434-454` - Single table for all users
- `core/app.py:339-341` - Only checks `user_id == admin['id']`, not system admin status

---

### Issue 2: Multiple Guards Can Be Active Simultaneously ❌

**Current Behavior:**
- Guard A logs in → active session created
- Guard B logs in → NEW active session created
- Guard A's session remains active
- Both guards show in "Active Sessions" table

**Root Causes:**
1. **Session.create() only logs out SAME user:** `Session.logout_user(user_id)` at line 245
2. **No role-based session enforcement:** No logic to logout other guards
3. **No single-guard-policy:** System allows unlimited concurrent guard sessions

**Evidence:**
- `core/database.py:244-245` - Only deactivates sessions for SAME user_id
- `core/auth.py:279` - Calls `Session.create()` without role checks
- No code exists to enforce "one guard at a time" policy

**Expected Behavior:**
- When Guard B logs in, Guard A's session should be invalidated
- Only ONE guard session active at any time
- Admin sessions unaffected (can have multiple admins logged in)

---

### Issue 3: Delete Button Not Working ⚠️

**Current Behavior:**
- Click Delete → confirmation dialog → API call → ERROR or no response

**Root Cause Investigation:**

**Frontend (admin.html:534-556):**
```javascript
async function deleteUser(userId, userEmail) {
    const response = await fetch(`${API_BASE}/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${authToken}` }
    });
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.detail || 'Failed to delete user');
    }
}
```
✅ Frontend code is CORRECT

**Backend (core/app.py:333-356):**
```python
@app.delete("/api/admin/users/{user_id}")
async def delete_user(user_id: int, admin: dict = Depends(require_admin)):
    if user_id == admin['id']:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    user = User.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    success = User.delete(user_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete user")
    
    AuditLog.log("USER_DELETED", admin['id'], f"Deleted user ID {user_id} ({user['email']})")
    return {"message": "User deleted successfully"}
```
✅ Backend endpoint is CORRECT

**Database (core/database.py:208-217):**
```python
@staticmethod
def delete(user_id: int) -> bool:
    query = "DELETE FROM users WHERE id = %s"
    try:
        db.execute_query(query, (user_id,), fetch=False)
        logger.info(f"[DATABASE] User deleted: ID {user_id}")
        return True
    except Error as e:
        logger.error(f"[DATABASE] Failed to delete user: {e}")
        return False
```
✅ Database method is CORRECT

**Potential Issues:**
1. **Foreign Key Constraints:** `active_sessions.user_id` has `ON DELETE CASCADE`
2. **Alerts table:** `alerts.user_id` has `ON DELETE SET NULL`
3. **Audit logs:** `audit_logs.user_id` has `ON DELETE SET NULL`

**Most Likely Cause:**
- Delete IS working, but UI not updating properly
- OR: Trying to delete currently logged-in user (blocked by self-check)
- OR: Database constraint error not being caught

**Verification Needed:**
- Check browser console for errors
- Check server logs for database errors
- Test deleting a user that has no sessions/alerts

---

## DATABASE SCHEMA ANALYSIS

### Current Schema Issues

**users table:**
```sql
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'guard') NOT NULL DEFAULT 'guard',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

**Missing:**
- No `is_system_admin` flag
- No unique constraint on system admin
- No protection mechanism

**active_sessions table:**
```sql
CREATE TABLE active_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

**Missing:**
- No role-based session constraints
- No mechanism to enforce single-guard policy

---

## REQUIRED CHANGES SUMMARY

### 1. Database Schema Migration

**Add to users table:**
```sql
ALTER TABLE users ADD COLUMN is_system_admin BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE users ADD UNIQUE INDEX idx_system_admin (is_system_admin) WHERE is_system_admin = TRUE;
UPDATE users SET is_system_admin = TRUE WHERE email = 'admin@dds.local';
```

### 2. Backend Changes

**core/database.py:**
- Add `User.get_system_admin()` method
- Add `User.is_system_admin(user_id)` method
- Modify `Session.create()` to enforce single-guard policy

**core/app.py:**
- Modify `list_users()` to exclude system admin
- Add `GET /api/admin/system-admin` endpoint
- Add `PATCH /api/admin/system-admin/password` endpoint
- Add system admin deletion protection

**core/auth.py:**
- Add system admin validation in `register_user()`

### 3. Frontend Changes

**frontend/admin.html:**
- Add separate "System Owner" section
- Remove system admin from user table
- Add "Change Password" form for system admin
- Update delete confirmation logic

---

## IMPLEMENTATION PLAN

### Phase 1: Database Migration (CRITICAL)
1. Create migration script
2. Add `is_system_admin` column
3. Add unique constraint
4. Update existing system admin

### Phase 2: Backend Logic (CRITICAL)
1. Update User model methods
2. Update Session.create() for guard policy
3. Add system admin endpoints
4. Add deletion protection

### Phase 3: Frontend Updates (CRITICAL)
1. Separate system admin display
2. Add password change form
3. Update user list filtering
4. Fix delete button (if needed)

### Phase 4: Testing (CRITICAL)
1. Test system admin protection
2. Test guard session switching
3. Test delete functionality
4. Test active session updates

---

**End of Root Cause Analysis**
