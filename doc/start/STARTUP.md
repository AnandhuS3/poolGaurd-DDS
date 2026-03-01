# PoolGuard — Drowning Detection System
## Complete Startup Guide

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Prerequisites](#2-prerequisites)
3. [Project Structure](#3-project-structure)
4. [First-Time Setup](#4-first-time-setup)
5. [Configuration](#5-configuration)
6. [Starting the System](#6-starting-the-system)
7. [Accessing the Application](#7-accessing-the-application)
8. [Default Credentials](#8-default-credentials)
9. [Frontend Development Mode](#9-frontend-development-mode)
10. [Production Deployment](#10-production-deployment)
11. [Troubleshooting](#11-troubleshooting)
12. [Quick Reference](#12-quick-reference)

---

## 1. System Overview

PoolGuard is a real-time AI-powered drowning detection system using:

- **YOLOv8** — person detection and bounding boxes
- **YOLOv8-Pose** — skeletal keypoint estimation
- **LSTM classifier** — temporal behavior risk scoring
- **DeepSORT** — multi-person tracking across frames
- **FastAPI + WebSocket** — real-time streaming backend
- **React + Vite** — modern surveillance dashboard frontend
- **MySQL** — user management, sessions, and alert history

### Architecture at a glance

```
Browser (React SPA)
      │  HTTP REST /api/*
      │  WebSocket /ws/process
      ▼
FastAPI Backend (port 8000)
      │
      ├── MySQL Database  (auth, sessions, alerts)
      ├── YOLOv8 Models   (assets/weights/)
      └── Media Files     (assets/uploads/, assets/output/)
```

---

## 2. Prerequisites

Make sure the following are installed before proceeding.

| Requirement | Minimum Version | Check command |
|---|---|---|
| Python | 3.10+ | `python --version` |
| pip | 23+ | `pip --version` |
| Node.js | 18+ | `node --version` |
| npm | 9+ | `npm --version` |
| MySQL Server | 8.0+ | `mysql --version` |
| Git | any | `git --version` |

> **GPU (optional but recommended):** CUDA-compatible GPU greatly speeds up YOLOv8 inference. Without it, detection runs on CPU.

---

## 3. Project Structure

```
v5-poss/
├── backend/
│   ├── main.py                  ← Entry point  (run this)
│   ├── config/
│   │   ├── requirements.txt     ← Python dependencies
│   │   └── .env                 ← Secrets file  (create from .env.example)
│   ├── core/
│   │   ├── app.py               ← FastAPI application + all routes
│   │   ├── auth.py              ← JWT auth, RBAC
│   │   ├── database.py          ← MySQL ORM helpers
│   │   ├── config.py            ← App configuration
│   │   ├── credentials.py       ← .env loader
│   │   ├── process_video.py     ← YOLOv8 + pose + LSTM pipeline
│   │   └── notifications.py     ← Email / SMS / WhatsApp alerts
│   └── database/
│       └── schema.sql           ← DB schema (auto-applied on first run)
├── frontend/
│   ├── package.json
│   ├── vite.config.ts           ← Dev proxy → localhost:8000
│   └── src/
│       ├── App.tsx
│       ├── pages/               ← Dashboard, Upload, Admin, Profile …
│       ├── context/AuthContext.tsx
│       └── services/api.ts
├── assets/
│   ├── weights/
│   │   ├── best.pt              ← Primary YOLOv8 detection model
│   │   ├── best1.pt             ← Secondary model (ensemble)
│   │   └── yolov8n-pose.pt      ← Pose estimation model
│   ├── uploads/                 ← Uploaded / downloaded videos
│   └── output/                  ← Processed annotated videos
└── doc/
    └── start/
        └── STARTUP.md           ← This file
```

---

## 4. First-Time Setup

### Step 1 — Clone / Navigate to project

```bash
cd v5-poss
```

### Step 2 — Create Python virtual environment

```bash
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### Step 3 — Install Python dependencies

```bash
pip install -r backend/config/requirements.txt
```

> If you have a CUDA GPU, replace `torch==2.1.2` in requirements.txt with the
> appropriate CUDA wheel from https://pytorch.org/get-started/locally/ before running pip install.

### Step 4 — Install frontend dependencies

```bash
cd frontend
npm install
cd ..
```

### Step 5 — Set up MySQL

1. Start your MySQL server.
2. Make sure a user exists (default config uses `root` with no password).
3. The database and tables are **created automatically** on first backend startup. You do not need to run any SQL manually.

### Step 6 — Create credentials file

```bash
# Navigate to backend config folder
cd backend/config

# Copy the example file
copy .env.example .env        # Windows
cp .env.example .env          # macOS/Linux
```

Edit `backend/config/.env` and fill in your values (see [Section 5](#5-configuration)).

---

## 5. Configuration

All secrets live in `backend/config/.env`. The app runs with defaults even if this file is missing, but notifications will not work.

```ini
# ── Database ─────────────────────────────────────────
DB_USER=root
DB_PASSWORD=your_mysql_password

# ── Email Alerts (Gmail recommended) ─────────────────
# Use a Gmail App Password, not your account password.
# Get one at: https://myaccount.google.com/apppasswords
SMTP_USERNAME=you@gmail.com
SMTP_PASSWORD=your_app_password

# ── SMS / WhatsApp (Twilio) ───────────────────────────
# Get credentials at: https://www.twilio.com/console
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1xxxxxxxxxx
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# ── Notification Recipients ───────────────────────────
# Comma-separated email addresses or phone numbers
NOTIFICATION_RECIPIENTS=guard@example.com,+91xxxxxxxxxx
```

### Key settings in `backend/core/config.py`

| Setting | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_NAME` | `drowning_detection_db` | Database name (auto-created) |
| `PORT` | `8000` | Backend server port |
| `CONFIDENCE_THRESHOLD` | `0.5` | YOLO detection threshold (0–1) |
| `USE_ENSEMBLE` | `False` | Use both `best.pt` + `best1.pt` |
| `MODEL_PATH` | `assets/weights/best.pt` | Primary detection model |

---

## 6. Starting the System

### Backend (required)

```bash
# From project root, with virtual environment activated
cd backend
python main.py
```

Expected output:
```
============================================================
   PoolGaurd - Drowning Detection System
============================================================

 Server: http://0.0.0.0:8000
 Login:  http://localhost:8000/login
 Register: http://localhost:8000/register
 Default admin: admin@dds.local / admin123
  CHANGE PASSWORD IMMEDIATELY!
```

The backend will automatically:
- Create the MySQL database if it does not exist
- Apply `schema.sql` if tables are missing
- Create a default system admin account if no users exist
- Serve the built React frontend at `http://localhost:8000`

### Frontend (development mode only — optional)

The backend already serves the built frontend. Only run the dev server if you are actively developing the UI:

```bash
cd frontend
npm run dev
```

This starts Vite on `http://localhost:5173` with hot-module reload and proxies all `/api`, `/analyze`, `/video`, and `/ws` requests to the backend on `localhost:8000`.

---

## 7. Accessing the Application

| URL | Description |
|---|---|
| `http://localhost:8000` | Main application (served by backend) |
| `http://localhost:8000/login` | Login page |
| `http://localhost:8000/register` | Self-registration (creates `guard` role) |
| `http://localhost:8000/docs` | FastAPI interactive API docs (Swagger UI) |
| `http://localhost:8000/redoc` | FastAPI ReDoc API docs |
| `http://localhost:5173` | Vite dev server (only when `npm run dev` is running) |

### Application pages

| Route | Role required | Description |
|---|---|---|
| `/` | Any | Detection dashboard — live video + alerts |
| `/upload` | Any | Upload video file or YouTube URL |
| `/live` | Any | Live camera feed (future expansion) |
| `/profile` | Any | Edit name / email / phone |
| `/profile/change-password` | Any | Change own password |
| `/admin` | Admin only | Admin dashboard overview |
| `/admin/users` | Admin only | Create, edit, activate, delete users |
| `/admin/system-admin` | Admin only | System admin password control |
| `/admin/sessions` | Admin only | View currently active sessions |
| `/admin/alerts` | Admin only | Paginated alert history |

---

## 8. Default Credentials

> ⚠️ Change these immediately after first login.

| Account | Email | Password | Role |
|---|---|---|---|
| System Admin | `admin@dds.local` | `admin123` | admin |

The system admin account is **protected** — it cannot be deleted through the admin panel.

### Password requirements (for all users)

- Minimum 8 characters
- At least one uppercase letter
- At least one digit

---

## 9. Frontend Development Mode

When running `npm run dev`, the Vite proxy config in `frontend/vite.config.ts` forwards all backend traffic automatically:

| Prefix | Forwarded to |
|---|---|
| `/api/*` | `http://localhost:8000` |
| `/analyze/*` | `http://localhost:8000` |
| `/video/*` | `http://localhost:8000` |
| `/ws/*` | `ws://localhost:8000` (WebSocket) |

### Build for production

```bash
cd frontend
npm run build
```

Output goes to `frontend/dist/`. The backend serves this folder as static files — so after rebuilding the frontend, simply restart the backend to pick up changes.

---

## 10. Production Deployment

For production, recommend the following changes:

### 1. Change the JWT secret

In `backend/core/auth.py`, replace:
```python
JWT_SECRET_KEY = "your-secret-key-change-in-production-use-env-variable"
```
with a long random string, or load it from `.env`:
```python
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-only-for-dev")
```

### 2. Build the frontend

```bash
cd frontend && npm run build
```

### 3. Run with a process manager

```bash
# Using uvicorn directly with workers
uvicorn core.app:app --host 0.0.0.0 --port 8000 --workers 2

# Or via main.py
python main.py
```

### 4. Use a reverse proxy (Nginx recommended)

Place Nginx in front of uvicorn to handle HTTPS, compression, and static asset caching. Example Nginx snippet:

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
}
```

The `Upgrade` and `Connection` headers are required for WebSocket (`/ws/process`) to work through Nginx.

---

## 11. Troubleshooting

### `ModuleNotFoundError: No module named 'core'`
Run from inside `backend/`:
```bash
cd backend
python main.py
```

### `mysql.connector.errors.DatabaseError: 2003 Can't connect to MySQL`
- Ensure MySQL service is running: `net start MySQL80` (Windows) or `sudo systemctl start mysql`
- Check `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` in `backend/config/.env`

### `FileNotFoundError: weights/best.pt not found`
Model weights must exist in `assets/weights/`. If missing, download or train them.
See [TRAINING_GUIDE.md](../TRAINING_GUIDE.md).

### WebSocket disconnects immediately
- The WS endpoint requires a JWT token as a query parameter: `?token=<jwt>`
- Make sure the frontend is logged in and `localStorage` contains `dds_token`
- Check browser DevTools → Network → WS tab for the close code

### Frontend shows blank page after build
- Run `npm run build` again from the `frontend/` folder
- Confirm `frontend/dist/index.html` exists
- Restart the backend so it picks up the new build

### YouTube download fails
- `yt-dlp` must be installed: `pip install yt-dlp`
- The URL must be a public video (age-restricted or private videos will fail)
- Check backend logs for the detailed `yt-dlp` error

### Port 8000 already in use
```bash
# Windows — find and kill the process
netstat -ano | findstr :8000
taskkill /PID <pid> /F

# Linux / macOS
lsof -ti:8000 | xargs kill
```

---

## 12. Quick Reference

### Startup checklist

```
[ ] MySQL service is running
[ ] Virtual environment is activated (.venv)
[ ] backend/config/.env exists (DB credentials at minimum)
[ ] assets/weights/best.pt exists
[ ] cd backend && python main.py
[ ] Open http://localhost:8000
[ ] Login with admin@dds.local / admin123
[ ] Change default password immediately
```

### One-liner startup (Windows PowerShell)

```powershell
# From project root
.venv\Scripts\Activate.ps1
cd backend
python main.py
```

### One-liner startup (macOS / Linux bash)

```bash
# From project root
source .venv/bin/activate && cd backend && python main.py
```

### Key API endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| POST | `/api/auth/login` | Public | Login → returns JWT |
| POST | `/api/auth/register` | Public | Self-register as guard |
| GET | `/api/auth/me` | Bearer | Get current user |
| PUT | `/api/auth/profile` | Bearer | Update profile |
| POST | `/api/auth/change-password` | Bearer | Change password |
| POST | `/analyze/upload` | Bearer | Upload video file |
| POST | `/analyze/youtube` | Bearer | Download YouTube video |
| WS | `/ws/process?token=<jwt>` | Token | Real-time processing stream |
| GET | `/download/{filename}` | Bearer | Download processed video |
| GET | `/api/admin/users` | Admin | List all users |
| POST | `/api/admin/users` | Admin | Create user |
| PATCH | `/api/admin/users/{id}` | Admin | Edit user |
| DELETE | `/api/admin/users/{id}` | Admin | Delete user |
| GET | `/api/admin/sessions` | Admin | Active sessions |
| GET | `/api/admin/alerts` | Admin | Alert history |

---

*PoolGuard DDS v5 — Documentation generated March 2026*
