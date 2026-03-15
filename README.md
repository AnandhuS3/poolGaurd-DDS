# PoolGuard — Drowning Detection System

> AI-powered real-time drowning detection with multi-person tracking, pose-driven behavior analysis, automated alerts, and role-based access control.

---

## Overview

PoolGuard is a production-ready aquatic safety system that combines computer vision, deep learning, and real-time communication to detect drowning events and dispatch alerts before they escalate. The system is designed for continuous unattended operation and supports concurrent monitoring of multiple individuals in a single video feed.

---

## Key Features

| Category | Capabilities |
|---|---|
| **Detection** | YOLOv8 person detection with configurable confidence thresholds |
| **Tracking** | DeepSORT persistent multi-person ID tracking across frames |
| **Pose Analysis** | YOLOv8-Pose skeleton estimation for body-state inference |
| **Behavior Classification** | LSTM temporal classifier over pose sequences for drowning pattern recognition |
| **State Engine** | Per-person state machine — Safe → Warning → Danger — with frame-based timing |
| **Alerting** | Email notifications; SMS/WhatsApp infrastructure in place |
| **Authentication** | JWT (HS256, 8-hour expiry) + bcrypt password hashing (cost 12) |
| **Authorization** | Role-based access control: Admin, Guard, User |
| **Session Management** | Single active session per user; audit log for all auth events |
| **Video Input** | File upload or YouTube URL ingestion |
| **Live Stream** | Annotated frames delivered to the browser over WebSocket |
| **Frontend** | React 19 + TypeScript SPA with Tailwind CSS, served via Vite |

---

## Architecture

The system is split into a FastAPI backend and a React SPA frontend. All communication goes through a REST API secured with JWT Bearer tokens, plus a WebSocket channel for the real-time annotated video stream. The backend orchestrates detection, tracking, pose estimation, and behavior classification in a sequential per-frame pipeline.

### Processing Pipeline

1. **Ingestion** — Video file or YouTube URL is received and stored temporarily.
2. **Frame Extraction** — Frames are decoded and dispatched to the detection pipeline.
3. **Detection & Tracking** — YOLO locates persons; DeepSORT assigns persistent IDs.
4. **Pose Estimation** — YOLOv8-Pose extracts 17-keypoint skeletons per tracked person.
5. **Behavior Classification** — LSTM model evaluates pose sequences over a sliding temporal window.
6. **State Transition** — Each person's state is updated; thresholds trigger Warning then Danger.
7. **Alert Dispatch** — On Danger, notifications are sent to active Guards, escalating to Admin if none are logged in.
8. **Stream Output** — Annotated frames with bounding boxes, IDs, and state overlays are streamed to the frontend canvas in real time.

---

## Technology Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| Computer vision | OpenCV, Ultralytics YOLOv8 |
| Pose estimation | YOLOv8-Pose (`yolov8n-pose.pt`) |
| Object tracking | DeepSORT Realtime |
| Behavior model | PyTorch LSTM |
| Video ingestion | yt-dlp |
| Database | PostgreSQL 14+ with connection pooling |
| Authentication | PyJWT, bcrypt, python-jose |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, Axios |
| Real-time comms | WebSockets (native FastAPI) |
| Environment config | python-dotenv, pytz |

---

## Project Structure

```
v5-poss/
├── backend/
│   ├── main.py                      # Entry point — starts Uvicorn
│   ├── core/
│   │   ├── app.py                   # FastAPI application & all routes
│   │   ├── auth.py                  # JWT, bcrypt, RBAC middleware
│   │   ├── database.py              # PostgreSQL connection pool & models
│   │   ├── process_video.py         # Detection & tracking pipeline
│   │   ├── pose_driven_processor.py # Pose + LSTM behavior pipeline
│   │   ├── pose_estimation/         # YOLOv8-Pose utilities
│   │   ├── behavior/                # Behavior model definitions
│   │   ├── behavior_classification/ # LSTM classifier & feature extraction
│   │   ├── notifications.py         # Alert dispatch (email/SMS)
│   │   ├── config.py                # Runtime configuration constants
│   │   ├── credentials.py           # Secure .env credential loader
│   │   ├── paths.py                 # Centralised path definitions
│   │   ├── logging_config.py        # Structured logging setup
│   │   └── region_utils.py          # Detection region helpers
│   ├── database/
│   │   ├── schema.sql               # Full PostgreSQL schema
│   │   ├── init_database.py         # Database initialisation script
│   │   └── create_user.py           # CLI user creation utility
│   └── config/
│       └── requirements.txt         # Python dependencies
├── frontend/
│   └── src/                         # React + TypeScript SPA
├── assets/
│   ├── weights/                     # YOLO & LSTM model files
│   ├── uploads/                     # Incoming video staging
│   ├── output/                      # Processed video output
│   └── sounds/                      # Alert audio assets
└── dlogs/                           # Structured application logs
```

---

## User Roles

| Role | Permissions |
|---|---|
| **Admin** | Full access — manage users, view sessions & alerts, process video |
| **Guard** | Process video, receive drowning alerts, view own session |
| **User** | Register, manage own profile, receive alert notifications |

---

## API Reference

### Authentication — Public

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/register` | Self-register a new account |
| POST | `/api/auth/login` | Authenticate; returns JWT |

### Authentication — Authenticated Users

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/auth/logout` | Terminate active session |
| GET | `/api/auth/me` | Current user info |
| PUT | `/api/auth/profile` | Update profile |
| POST | `/api/auth/change-password` | Change password |

### Video Processing — Guard / Admin

| Method | Endpoint | Description |
|---|---|---|
| POST | `/analyze/upload` | Upload a video file for analysis |
| POST | `/analyze/youtube` | Ingest a YouTube URL |
| WS | `/ws/process?token=<jwt>` | Real-time annotated frame stream |
| GET | `/download/{filename}` | Download processed video |
| GET | `/video/{filename}` | Stream video (range requests) |

### Administration — Admin Only

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/admin/users` | Create a user |
| GET | `/api/admin/users` | List all users |
| PATCH | `/api/admin/users/{id}` | Update a user |
| DELETE | `/api/admin/users/{id}` | Delete a user |
| GET | `/api/admin/sessions` | Active sessions |
| GET | `/api/admin/alerts` | Full alert history |
| GET | `/api/admin/system-admin` | System administrator info |
| POST | `/api/admin/system-admin/password` | Change system admin password |

---

## Setup

### Prerequisites

- Python 3.8 or higher
- Node.js 18 or higher
- PostgreSQL 14.0 or higher
- GPU with CUDA support (recommended for real-time performance)
- Model weights placed in `assets/weights/` — `best.pt`, `best1.pt`, `yolov8n-pose.pt`

### Backend

1. Create and activate a Python virtual environment.
2. Install dependencies from `backend/config/requirements.txt`.
3. Copy `config/.env.example` to `config/.env` and populate database credentials, SMTP settings, JWT secret, and timezone.
4. Run `backend/database/init_database.py` to initialise the PostgreSQL schema.
5. Start the server with `python main.py` from the `backend/` directory.

### Frontend

1. From the `frontend/` directory, install Node dependencies.
2. Start the Vite development server (`npm run dev`).
3. For production, build the SPA (`npm run build`) and serve the `dist/` output.

### Access Points

| Interface | URL |
|---|---|
| Frontend SPA | `http://localhost:5173` (dev) |
| Backend API | `http://localhost:8000` |
| API Docs (Swagger) | `http://localhost:8000/docs` |

### Default Credentials

> **Change immediately after first login.**

- Email: `creagoouon@gmail.com`
- Password: `admin123`

---

## Configuration

Key parameters in `backend/core/config.py`:

| Parameter | Default | Description |
|---|---|---|
| `CONFIDENCE_THRESHOLD` | 0.4 | YOLO detection confidence cutoff |
| `WARNING_DURATION` | 90 frames | Frames of reduced motion before Warning state |
| `DANGER_DURATION` | 150 frames | Frames before Danger state and alert dispatch |
| `MOTION_THRESHOLD` | — | Movement sensitivity for state transitions |
| `MAX_AGE` | 30 frames | Frames to retain a lost track |
| `N_INIT` | 3 frames | Frames required to confirm a new track |
| `FRAME_SKIP` | — | Frames to skip per cycle (reduces CPU/GPU load) |

---

## Security

- Passwords hashed with bcrypt at cost factor 12; no plain-text storage.
- JWT tokens signed with HS256, expire after 8 hours.
- One active session per user; logout immediately invalidates the session.
- All authentication events (login, logout, failures, user changes) written to the audit log.
- WebSocket connections authenticate via token query parameter before the handshake is accepted.
- Admin and Guard/Admin route guards enforced server-side via FastAPI dependency injection.

---

## Troubleshooting

| Symptom | Resolution |
|---|---|
| Import or package errors | Re-install from `requirements.txt` with `--upgrade` |
| Database connection failure | Verify PostgreSQL is running; check `.env` credentials |
| Model file not found | Confirm weight files exist under `assets/weights/` |
| Slow or dropped frames | Enable CUDA GPU, increase `FRAME_SKIP`, lower JPEG quality |
| WebSocket disconnects | Verify port availability and that a valid JWT is being passed |
| 401 on all requests | Token may have expired — log out and log in again |

---

## Documentation

Extended documentation is available in `doc/`:

| Document | Path |
|---|---|
| System Architecture | `doc/arc/ARCHITECTURE.md` |
| Authentication Guide | `doc/auth/AUTH_DOCUMENTATION.md` |
| Pose & LSTM Integration | `doc/pose/COMPLETE_INTEGRATION_SUMMARY.md` |
| Startup & Deployment | `doc/start/STARTUP.md` |
| Production Guide | `doc/summary_guide/PRODUCTION_GUIDE.md` |
| API & Implementation | `doc/summary_guide/IMPLEMENTATION_SUMMARY.md` |

---

## Built With

FastAPI · Ultralytics YOLOv8 · PyTorch · DeepSORT · OpenCV · PostgreSQL · WebSockets · React · TypeScript · Tailwind CSS · Vite
