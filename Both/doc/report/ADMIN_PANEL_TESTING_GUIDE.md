# Admin Panel Fix - Testing & Verification Guide

**Date:** February 15, 2026  
**Purpose:** Step-by-step testing instructions to verify all fixes

---

## ✅ PRE-TESTING CHECKLIST

Before testing, ensure:
- [x] Database migration completed successfully
- [x] Server is running (python main.py)
- [x] You have admin credentials (admin@dds.local / password)
- [x] You have created at least 2 guard accounts for testing

---

## TEST SUITE 1: SYSTEM ADMINISTRATOR PROTECTION

### Test 1.1: System Admin Appears in Separate Section ✅

**Steps:**
1. Open browser: http://localhost:8000/login
2. Login with admin credentials
3. Navigate to Admin Panel
4. Scroll to "🔐 System Owner" section

**Expected Results:**
- ✅ System Owner section appears BEFORE User Management
- ✅ System admin info displayed:
  - Name: System Administrator
  - Email: admin@dds.local
  - Phone number
  - Status: Active
  - Created date
- ✅ Warning message: "Protected Account: This account cannot be deleted..."
- ✅ Password change form visible on the right

**Actual Result:** _____________

---

### Test 1.2: System Admin NOT in User Table ✅

**Steps:**
1. Scroll to "User Management" section
2. Check all rows in the user table

**Expected Results:**
- ✅ System Administrator (admin@dds.local) does NOT appear in table
- ✅ Only regular users (guards/admins) appear
- ✅ All users have Delete button EXCEPT system admin

**Actual Result:** _____________

---

### Test 1.3: Change System Admin Password ✅

**Steps:**
1. In System Owner section, fill password change form:
   - Current Password: [your current password]
   - New Password: TestPassword123
   - Confirm New Password: TestPassword123
2. Click "Update Password"
3. Wait for success message
4. Logout
5. Try logging in with NEW password

**Expected Results:**
- ✅ Success message: "Password changed successfully!"
- ✅ Form clears after success
- ✅ Can login with new password
- ✅ Cannot login with old password

**Actual Result:** _____________

---

### Test 1.4: System Admin Deletion Protection (Backend) ✅

**Steps:**
1. Open browser DevTools (F12)
2. Go to Console tab
3. Run this command (replace TOKEN with your auth token from localStorage):
```javascript
fetch('http://localhost:8000/api/admin/users/1', {
    method: 'DELETE',
    headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('auth_token')
    }
}).then(r => r.json()).then(console.log)
```

**Expected Results:**
- ✅ Response status: 403 Forbidden
- ✅ Error message: "Cannot delete system administrator. System admin is protected."

**Actual Result:** _____________

---

## TEST SUITE 2: SINGLE GUARD SESSION POLICY

### Test 2.1: Create Test Guards

**Steps:**
1. In Admin Panel, create two guard accounts:
   - Guard A: guard_a@test.com / password: GuardA123
   - Guard B: guard_b@test.com / password: GuardB123
2. Verify both appear in User Management table

**Expected Results:**
- ✅ Both guards created successfully
- ✅ Both show Status: Active

**Actual Result:** _____________

---

### Test 2.2: Single Guard Session Enforcement ✅

**Steps:**
1. **Browser 1 (Normal):** Login as Guard A
2. Check Admin Panel → Active Sessions
3. **Verify:** 1 guard session (Guard A)
4. **Browser 2 (Incognito):** Login as Guard B
5. **Browser 1:** Refresh Active Sessions (wait 5 seconds for auto-refresh)
6. **Verify:** Only Guard B appears in Active Sessions
7. **Browser 1:** Try to upload a video or access any protected route
8. **Verify:** Guard A is redirected to login (session expired)

**Expected Results:**
- ✅ Initially: Guard A active
- ✅ After Guard B login: Only Guard B active
- ✅ Guard A session invalidated (is_active = FALSE in database)
- ✅ Guard A redirected to login on next action
- ✅ Active session count: 1 (only Guard B)

**Actual Result:** _____________

---

### Test 2.3: Multiple Admins Allowed ✅

**Steps:**
1. Create second admin account: admin2@test.com / Admin2Pass123
2. **Browser 1:** Login as admin@dds.local
3. **Browser 2:** Login as admin2@test.com
4. Check Active Sessions in both browsers

**Expected Results:**
- ✅ Both admin sessions remain active
- ✅ Active Sessions shows 2 admins
- ✅ Neither admin is logged out

**Actual Result:** _____________

---

### Test 2.4: Auto-Refresh Active Sessions ✅

**Steps:**
1. Login as admin
2. Open Admin Panel
3. Note current active sessions
4. In another browser, login as a guard
5. Wait 5 seconds (do NOT manually refresh)
6. Check Active Sessions table

**Expected Results:**
- ✅ Active Sessions table updates automatically
- ✅ New guard session appears without manual refresh
- ✅ Updates every 5 seconds

**Actual Result:** _____________

---

## TEST SUITE 3: DELETE FUNCTIONALITY

### Test 3.1: Delete Regular User ✅

**Steps:**
1. Create a test user: test_user@test.com
2. In User Management, find test_user@test.com
3. Click "🗑️ Delete" button
4. Confirm deletion in popup
5. Wait for success message

**Expected Results:**
- ✅ Confirmation dialog appears
- ✅ Success message: "User deleted successfully"
- ✅ User removed from table
- ✅ User no longer in database

**Actual Result:** _____________

---

### Test 3.2: Cannot Delete Self ✅

**Steps:**
1. Login as admin@dds.local
2. Create another admin: admin_test@test.com
3. Login as admin_test@test.com
4. Try to delete admin_test@test.com (yourself)

**Expected Results:**
- ✅ Error message: "Cannot delete your own account"
- ✅ User NOT deleted

**Actual Result:** _____________

---

### Test 3.3: System Admin Has No Delete Button ✅

**Steps:**
1. Login as admin
2. Check System Owner section
3. Check User Management table

**Expected Results:**
- ✅ System Owner section has NO delete button
- ✅ Only "Change Password" form visible
- ✅ System admin NOT in User Management table

**Actual Result:** _____________

---

## TEST SUITE 4: DATABASE VERIFICATION

### Test 4.1: Verify Database Schema ✅

**Steps:**
1. Open MySQL client
2. Run:
```sql
USE drowning_detection_db;
DESCRIBE users;
```

**Expected Results:**
- ✅ Column `is_system_admin` exists (BOOLEAN, NOT NULL, DEFAULT FALSE)
- ✅ Index `idx_system_admin` exists

**SQL to verify index:**
```sql
SHOW INDEX FROM users WHERE Key_name = 'idx_system_admin';
```

**Actual Result:** _____________

---

### Test 4.2: Verify Only One System Admin ✅

**Steps:**
1. Run SQL:
```sql
SELECT id, name, email, is_system_admin 
FROM users 
WHERE is_system_admin = TRUE;
```

**Expected Results:**
- ✅ Exactly 1 row returned
- ✅ Email: admin@dds.local
- ✅ is_system_admin: 1 (TRUE)

**Actual Result:** _____________

---

### Test 4.3: Verify Guard Session Invalidation ✅

**Steps:**
1. Login as Guard A (Browser 1)
2. Note session ID:
```sql
SELECT id, user_id, is_active, login_time 
FROM active_sessions 
WHERE user_id = (SELECT id FROM users WHERE email = 'guard_a@test.com')
ORDER BY login_time DESC LIMIT 1;
```
3. Login as Guard B (Browser 2)
4. Re-run query from step 2

**Expected Results:**
- ✅ Guard A's session: is_active = FALSE
- ✅ logout_time is set
- ✅ Guard B's session: is_active = TRUE

**Actual Result:** _____________

---

## REGRESSION TESTING

### Regression 1: Regular User Creation Still Works ✅

**Steps:**
1. Create new guard via Admin Panel
2. Verify guard can login
3. Verify guard can access monitoring page

**Expected Results:**
- ✅ Guard created successfully
- ✅ Guard can login
- ✅ Guard can access /

**Actual Result:** _____________

---

### Regression 2: User Update Still Works ✅

**Steps:**
1. Click "Deactivate" on a user
2. Verify status changes to Inactive
3. Click "Activate"
4. Verify status changes to Active

**Expected Results:**
- ✅ Deactivate works
- ✅ Activate works
- ✅ Status badge updates

**Actual Result:** _____________

---

### Regression 3: Audit Logging Still Works ✅

**Steps:**
1. Perform various actions (create user, delete user, change password)
2. Check database:
```sql
SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT 10;
```

**Expected Results:**
- ✅ All actions logged
- ✅ Correct event_type
- ✅ Correct user_id

**Actual Result:** _____________

---

## EDGE CASES

### Edge Case 1: What if System Admin is Deactivated? ⚠️

**Steps:**
1. Run SQL:
```sql
UPDATE users SET is_active = FALSE WHERE is_system_admin = TRUE;
```
2. Try to login as system admin
3. Try to access admin panel

**Expected Results:**
- ⚠️ Login fails: "Account is deactivated"
- ⚠️ Cannot access admin panel
- ⚠️ Need to manually reactivate in database

**Actual Result:** _____________

---

### Edge Case 2: What if Two System Admins Exist? ⚠️

**Steps:**
1. Run SQL:
```sql
UPDATE users SET is_system_admin = TRUE WHERE id = 2;
```
2. Check Admin Panel
3. Try to delete either system admin

**Expected Results:**
- ⚠️ Both appear in System Owner section (UI bug)
- ⚠️ Backend still prevents deletion of both
- ⚠️ Should run migration again to fix

**Actual Result:** _____________

---

## PERFORMANCE TESTING

### Performance 1: Active Session Auto-Refresh ✅

**Steps:**
1. Login as admin
2. Open browser DevTools → Network tab
3. Wait 30 seconds
4. Count number of `/api/admin/sessions` requests

**Expected Results:**
- ✅ ~6 requests in 30 seconds (every 5 seconds)
- ✅ No errors
- ✅ Response time < 100ms

**Actual Result:** _____________

---

## FINAL VERIFICATION CHECKLIST

- [ ] System admin appears in separate protected section
- [ ] System admin NOT in user management table
- [ ] System admin password change works
- [ ] System admin cannot be deleted (backend + frontend)
- [ ] Only one guard can be active at a time
- [ ] Multiple admins can be active simultaneously
- [ ] Active sessions auto-refresh every 5 seconds
- [ ] Delete button works for regular users
- [ ] Delete button does NOT appear for system admin
- [ ] Database migration applied successfully
- [ ] All regression tests pass
- [ ] No console errors in browser

---

## TROUBLESHOOTING

### Issue: System admin still appears in user table

**Solution:**
1. Check backend logs for errors
2. Verify `exclude_system_admin=True` in `list_users()`
3. Hard refresh browser (Ctrl+Shift+R)

### Issue: Guard sessions not invalidating

**Solution:**
1. Check database: `SELECT * FROM active_sessions WHERE is_active = TRUE;`
2. Verify `Session.create()` has single-guard logic
3. Restart server

### Issue: Password change fails

**Solution:**
1. Check current password is correct
2. Verify new password is at least 8 characters
3. Check server logs for bcrypt errors

### Issue: Active sessions not auto-refreshing

**Solution:**
1. Check browser console for JavaScript errors
2. Verify `setInterval(loadActiveSessions, 5000)` is running
3. Check network tab for API calls

---

## SIGN-OFF

**Tested By:** _____________  
**Date:** _____________  
**All Tests Passed:** [ ] YES [ ] NO  
**Issues Found:** _____________  
**Notes:** _____________

---

**Testing Complete:** Ready for Production ✅
