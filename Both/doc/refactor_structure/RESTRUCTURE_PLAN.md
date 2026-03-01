# 📁 Project Restructuring Plan

**Goal:** Reorganize the project to match the structure defined in PROJECT_DIARY.md (lines 173-223)

## Current vs Desired Structure

### Current Structure:
```
v4/
├── Core files (app.py, auth.py, etc.) - ✅ Correct location
├── client/ - ❌ Should be removed
│   ├── index.html
│   ├── login.html  
│   ├── register.html
│   └── admin.html
├── Database files (schema.sql, etc.) - ✅ Correct location
├── Test files (test_*.py) - ✅ Correct location
└── doc/ - ✅ Correct location
```

### Desired Structure (from PROJECT_DIARY.md):
```
v4/
├── Core files (app.py, auth.py, etc.) - ✅ Already correct
├── Frontend files (index.html, login.html, etc.) - ❌ Need to move from client/
├── Database files (schema.sql, etc.) - ✅ Already correct
├── Test files (test_*.py) - ✅ Already correct
└── doc/ - ✅ Already correct
```

## Changes Required:

### 1. Move Frontend Files
- Move `client/index.html` → `index.html`
- Move `client/login.html` → `login.html`
- Move `client/register.html` → `register.html`
- Move `client/admin.html` → `admin.html`
- Delete empty `client/` directory

### 2. Update app.py References
- Change `FileResponse("client/login.html")` → `FileResponse("login.html")`
- Change `FileResponse("client/register.html")` → `FileResponse("register.html")`
- Change `FileResponse("client/admin.html")` → `FileResponse("admin.html")`
- Change `StaticFiles(directory="client")` → `StaticFiles(directory=".")`

### 3. Update paths.py
- Add CLIENT_* paths for HTML files at root level
- Remove client directory references

## Risk Assessment:

**Low Risk** - Simple file moves with clear path updates
- All changes are straightforward
- Easy to test
- Easy to rollback if needed

## Implementation Steps:

1. ✅ Create this plan document
2. ⏳ Move HTML files from client/ to root
3. ⏳ Update app.py file paths
4. ⏳ Update paths.py module
5. ⏳ Delete empty client/ directory
6. ⏳ Test application startup
7. ⏳ Verify all pages load correctly

**Status:** Ready to implement
