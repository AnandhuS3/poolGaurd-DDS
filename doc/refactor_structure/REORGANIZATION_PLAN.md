# 📁 Project Reorganization Plan

**Goal:** Organize files into categorized subdirectories as specified

## Desired Structure:

```
v4/
├── core/                         # Core application files
│   ├── app.py
│   ├── process_video.py
│   ├── auth.py
│   ├── database.py
│   ├── notifications.py
│   ├── config.py
│   ├── credentials.py
│   ├── paths.py
│   └── india_utils.py
│
├── database/                     # Database scripts
│   ├── schema.sql
│   ├── init_database.py
│   ├── create_user.py
│   └── update_schema.py
│
├── frontend/                     # Frontend HTML files
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   └── admin.html
│
├── tests/                        # Test files
│   ├── test_analysis.py
│   ├── test_email.py
│   ├── test_login.py
│   └── test_welcome_email.py
│
├── config/                       # Configuration files
│   ├── .env.example
│   ├── .env
│   └── requirements.txt
│
├── doc/                          # Documentation (already exists)
│   └── ... (existing docs)
│
├── uploads/                      # Runtime (already exists)
├── output/                       # Runtime (already exists)
├── sounds/                       # Runtime (already exists)
├── weights/                      # Runtime (already exists)
│
├── README.md                     # Root level
├── .gitignore                    # Root level
└── drowning_detection.log        # Root level
```

## Changes Required:

### 1. Create New Directories:
- `core/`
- `database/`
- `frontend/`
- `tests/`
- `config/`

### 2. Move Files:

**To core/:**
- app.py
- process_video.py
- auth.py
- database.py (the Python file)
- notifications.py
- config.py
- credentials.py
- paths.py
- india_utils.py

**To database/:**
- schema.sql
- init_database.py
- create_user.py
- update_schema.py

**To frontend/:**
- index.html
- login.html
- register.html
- admin.html

**To tests/:**
- test_analysis.py
- test_email.py
- test_login.py
- test_welcome_email.py

**To config/:**
- .env.example
- .env
- requirements.txt

### 3. Update Import Paths:

This is CRITICAL - all Python imports will need to be updated:
- `from auth import ...` → `from core.auth import ...`
- `from database import ...` → `from core.database import ...`
- etc.

### 4. Update File Paths:

- Schema path references
- HTML file paths in app.py
- Model paths
- etc.

## Risk Assessment:

**HIGH RISK** - This is a major restructuring that will:
- Break all imports
- Require extensive code changes
- Need Python package setup (__init__.py files)
- Require careful testing

## Recommendation:

This requires creating a proper Python package structure with __init__.py files and updating all imports throughout the codebase.

**Proceed?**
