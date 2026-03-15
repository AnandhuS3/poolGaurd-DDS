from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
import uvicorn
import os
import yt_dlp
import cv2
import base64
import asyncio
import json
import re
from core.process_video import process_video_realtime
import logging
import psycopg2
import psycopg2.extras
from psycopg2 import Error

# Import authentication and database modules
from core.database import db, User, Session, Alert, AuditLog
from core.auth import (
    AuthService, LoginRequest, RegisterRequest, UpdateUserRequest,
    AuthResponse, get_current_user, require_admin, require_guard_or_admin,
    authenticate_websocket, get_client_ip, get_user_agent,
    PasswordHasher, get_current_user_from_query_token
)
from core.notifications import initialize_database, NotificationService
from core import config as app_config
from core.paths import UPLOADS_DIR, OUTPUT_DIR, SOUNDS_DIR, get_schema_path_str, ensure_directories, FRONTEND_DIR
from core.credentials import ALLOWED_ORIGINS
# Import config
try:
    from config import (
        SERVER_HOST, SERVER_PORT,
        DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_POOL_SIZE
    )
except ImportError:
    SERVER_HOST = "0.0.0.0"
    SERVER_PORT = 8000
    DB_HOST = "localhost"
    DB_PORT = 3306
    DB_USER = "root"
    DB_PASSWORD = ""
    DB_NAME = "drowning_detection_db"
    DB_POOL_SIZE = 5

# Import centralized logging configuration
from core.logging_config import loggers, log_startup, log_database, log_auth, log_websocket, log_error
logger = loggers['app']
startup_logger = loggers['startup']
db_logger = loggers['database']
auth_logger = loggers['auth']
ws_logger = loggers['websocket']

app = FastAPI(title="Drowning Detection System")

@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    """Return 503 when the database pool is not available (e.g. database down at startup)"""
    logger.error(f"[SERVER] RuntimeError on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )

def ensure_database_ready():
    """
    Automatically set up database on startup:
    1. Create database if it doesn't exist
    2. Create tables from schema.sql if they don't exist
    3. Create default admin user if no users exist
    """
    logger.info("[DATABASE] Checking database setup...")
    
    # Step 1: Ensure tables exist in poolguard_db
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            dbname=DB_NAME,
        )
        conn.autocommit = True
        cursor = conn.cursor()
        
        # Step 2: Check if tables exist
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_schema = 'public' AND table_catalog = %s
        """, (DB_NAME,))
        table_count = cursor.fetchone()[0]
        
        if table_count < 5:  # We expect at least 5 tables
            logger.info("[DATABASE] Tables missing, creating from schema.sql...")
            
            # Read and execute schema.sql
            schema_path = get_schema_path_str()
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = f.read()
                
                # Execute schema statements — skip legacy directives
                statements = [s.strip() for s in schema.split(';') if s.strip()]
                for statement in statements:
                    stmt = statement.strip()
                    if not stmt or stmt.startswith('--'):
                        continue
                    # Skip legacy directives
                    upper = stmt.upper()
                    if upper.startswith('DELIMITER') or upper.startswith('USE '):
                        continue
                    try:
                        cursor.execute(stmt)
                    except Exception as e:
                        if "already exists" not in str(e).lower():
                            logger.warning(f"[DATABASE] Schema warning: {e}")
                
                conn.commit()
                logger.info("[DATABASE] Tables created successfully")
            else:
                logger.warning("[DATABASE] schema.sql not found, skipping table creation")
        else:
            logger.info(f"[DATABASE] Found {table_count} tables")
        
        # Step 3: Check if admin user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            logger.info("[DATABASE] No admin user found, creating default admin...")
            
            # Create default admin user
            password_hash = PasswordHasher.hash_password("admin123")
            insert_query = """
                INSERT INTO users (name, email, password_hash, role, phone_number, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_query, ('admin', 'creagoouon@gmail.com', password_hash, 'admin', '+00 00000 00000'))
            conn.commit()
            logger.info("[DATABASE] [OK] Default admin created: creagoouon@gmail.com / admin123")
        else:
            logger.info(f"[DATABASE] Found {admin_count} admin user(s)")
        
        cursor.close()
        conn.close()
        logger.info("[DATABASE] [OK] Database ready!")
        
    except Exception as e:
        logger.error(f"[DATABASE] [ERROR] Setup error: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Run database checks on startup, including cameras table migration."""
    ensure_database_ready()
    _ensure_cameras_table()


def _ensure_cameras_table():
    """Create cameras table if it doesn't exist (idempotent)."""
    try:
        from database.migrate_cameras import run as migrate_cameras
        migrate_cameras()
    except Exception as e:
        logger.warning(f"[CAMERA] Could not auto-migrate cameras table: {e}")

# Initialize database connection
try:
    db.initialize(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        pool_size=DB_POOL_SIZE
    )
    # Initialize notification system with database models
    initialize_database(Session, User, Alert, AuditLog)
    logger.info("[DATABASE] Successfully connected to PostgreSQL")
except Exception as e:
    logger.error(f"[DATABASE] Failed to initialize: {e}")
    logger.warning("[DATABASE] Running without authentication support")

# Create notification service for welcome emails
notification_service = NotificationService(app_config, use_database=True)

# CORS middleware — origins controlled via ALLOWED_ORIGINS in .env
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create directories if not exist
ensure_directories()

# ============================================================================
# AUTHENTICATION ENDPOINTS
# ============================================================================

@app.post("/api/auth/login", response_model=AuthResponse)
async def login(credentials: LoginRequest, request: Request):
    """
    Login endpoint
    Returns JWT token and user info
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    access_token, user_info = AuthService.login(
        credentials.email,
        credentials.password,
        ip_address,
        user_agent
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_info
    }


@app.post("/api/auth/register", status_code=201)
async def register(user_data: RegisterRequest, request: Request):
    """
    Public user registration.
    Creates an active account immediately — no email verification required.
    Sends a welcome email notification to the new user.
    """
    user_info = AuthService.register_user(
        name=user_data.name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        password=user_data.password,
        role='guard',
        created_by=None,
    )

    # Send welcome email (non-blocking, best-effort)
    try:
        asyncio.create_task(
            asyncio.to_thread(
                notification_service.send_welcome_email,
                user_data.name,
                user_data.email,
                'guard',
            )
        )
    except Exception as e:
        logger.error(f"[REGISTRATION] Failed to queue welcome email: {e}")

    return {
        "message": "Registration successful. You can now log in.",
        "email": user_data.email,
    }


@app.get("/api/auth/verify-email")
async def verify_email(token: str):
    """
    Legacy email-verification endpoint kept for backward-compatibility.
    Email verification is no longer required; this always succeeds gracefully.
    """
    user = AuthService.verify_email(token)
    return {
        "message": "Email verified successfully. You can now log in.",
        "name": user.get("name", ""),
        "email": user.get("email", ""),
    }


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@app.post("/api/auth/forgot-password", status_code=202)
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    """
    Request a password-reset email.
    Always returns 202 to prevent user-enumeration (same response whether email exists or not).
    """
    ip_address = get_client_ip(request)
    reset_token = AuthService.request_password_reset(body.email, ip_address)

    if reset_token:
        user = __import__('core.database', fromlist=['User']).User.get_by_email(body.email)
        base_url = getattr(app_config, "APP_BASE_URL", "http://localhost:5173")
        reset_url = f"{base_url}/reset-password?token={reset_token}"

        try:
            asyncio.create_task(
                asyncio.to_thread(
                    notification_service.send_password_reset_email,
                    user['name'] if user else '',
                    body.email,
                    reset_url,
                )
            )
        except Exception as e:
            logger.error(f"[RESET] Failed to queue reset email: {e}")

    return {"message": "If that email is registered, a password-reset link has been sent."}


@app.post("/api/auth/reset-password")
async def reset_password(body: ResetPasswordRequest):
    """
    Consume a password-reset token and set the new password.
    Token is single-use and expires after 30 minutes.
    """
    AuthService.reset_password(body.token, body.new_password)
    return {"message": "Password has been reset successfully. You can now log in."}


@app.post("/api/auth/logout")
async def logout(request: Request, current_user: dict = Depends(get_current_user)):
    """Logout endpoint - deactivates session"""
    ip_address = get_client_ip(request)
    AuthService.logout(current_user['id'], ip_address)
    return {"message": "Logged out successfully"}


@app.get("/api/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current logged-in user info"""
    return current_user


@app.put("/api/auth/profile")
async def update_profile(profile_data: UpdateUserRequest, current_user: dict = Depends(get_current_user)):
    """Update current user's profile"""
    updated_user = AuthService.update_user(current_user['id'], profile_data)
    return updated_user


@app.post("/api/auth/change-password")
async def change_password(password_data: dict, current_user: dict = Depends(get_current_user)):
    """Change current user's password"""
    old_password = password_data.get('old_password')
    new_password = password_data.get('new_password')
    
    if not old_password or not new_password:
        raise HTTPException(status_code=400, detail="Old and new passwords required")
    
    AuthService.change_password(current_user['id'], old_password, new_password)
    return {"message": "Password changed successfully"}


# ============================================================================
# ADMIN ENDPOINTS (Admin only)
# ============================================================================

@app.post("/api/admin/users")
async def create_user(
    user_data: RegisterRequest,
    admin: dict = Depends(require_admin)
):
    """Create new user (Admin only)"""
    user_info = AuthService.register_user(
        name=user_data.name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        password=user_data.password,
        role=user_data.role,
        created_by=admin['id']
    )
    return user_info


@app.get("/api/admin/users")
async def list_users(admin: dict = Depends(require_admin)):
    """Get all users excluding system administrator (Admin only)"""
    users = User.get_all(exclude_system_admin=True)
    return users


@app.patch("/api/admin/users/{user_id}")
async def update_user(
    user_id: int,
    update_data: UpdateUserRequest,
    admin: dict = Depends(require_admin)
):
    """Update user (Admin only)"""
    update_dict = update_data.dict(exclude_unset=True)
    
    # Hash password if provided
    if 'password' in update_dict and update_dict['password']:
        update_dict['password_hash'] = PasswordHasher.hash_password(update_dict.pop('password'))
    
    success = User.update(user_id, **update_dict)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update user")
    
    AuditLog.log("USER_UPDATED", admin['id'], f"Updated user ID {user_id}")
    return {"message": "User updated successfully"}


@app.delete("/api/admin/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: dict = Depends(require_admin)
):
    """Delete user permanently (Admin only)"""
    # Prevent admin from deleting themselves
    if user_id == admin['id']:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Prevent deletion of system administrator
    if User.is_system_admin(user_id):
        raise HTTPException(
            status_code=403, 
            detail="Cannot delete system administrator. System admin is protected."
        )
    
    # Check if user exists
    user = User.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete the user
    success = User.delete(user_id)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete user")
    
    AuditLog.log("USER_DELETED", admin['id'], f"Deleted user ID {user_id} ({user['email']})")
    return {"message": "User deleted successfully"}


@app.get("/api/admin/system-admin")
async def get_system_admin(admin: dict = Depends(require_admin)):
    """Get system administrator information (Admin only)"""
    system_admin = User.get_system_admin()
    if not system_admin:
        raise HTTPException(status_code=404, detail="System administrator not found")
    
    # Remove password_hash from response
    system_admin.pop('password_hash', None)
    return system_admin


class SystemAdminPasswordRequest(BaseModel):
    """Request model for system admin password change"""
    current_password: str
    new_password: str = Field(..., min_length=8)


@app.patch("/api/admin/system-admin/password")
async def change_system_admin_password(
    password_data: SystemAdminPasswordRequest,
    admin: dict = Depends(require_admin)
):
    """Change system administrator password (Admin only)"""
    system_admin = User.get_system_admin()
    if not system_admin:
        raise HTTPException(status_code=404, detail="System administrator not found")
    
    # Verify current password
    if not PasswordHasher.verify_password(password_data.current_password, system_admin['password_hash']):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    
    # Hash new password
    new_password_hash = PasswordHasher.hash_password(password_data.new_password)
    
    # Update password
    success = User.update(system_admin['id'], password_hash=new_password_hash)
    
    if not success:
        raise HTTPException(status_code=500, detail="Failed to update password")
    
    AuditLog.log("PASSWORD_CHANGED", admin['id'], f"Changed system administrator password")
    return {"message": "System administrator password updated successfully"}


@app.get("/api/admin/sessions")
async def list_active_sessions(admin: dict = Depends(require_admin)):
    """Get all active sessions (Admin only)"""
    active_users = Session.get_active_guards()
    # Also get admin sessions
    query = """
        SELECT u.id, u.name, u.email, u.role, s.login_time, s.ip_address
        FROM users u
        INNER JOIN active_sessions s ON u.id = s.user_id
        WHERE u.is_active = TRUE AND s.is_active = TRUE
        ORDER BY s.login_time ASC
    """
    all_sessions = db.execute_query(query)
    return all_sessions


@app.get("/api/admin/alerts")
async def list_alerts(
    limit: int = 100,
    admin: dict = Depends(require_admin)
):
    """Get all alerts (Admin only)"""
    alerts = Alert.get_recent(limit)
    return alerts


class DeleteAlertsRequest(BaseModel):
    alert_ids: List[int]

@app.delete("/api/admin/alerts")
async def delete_alerts(
    request: DeleteAlertsRequest,
    admin: dict = Depends(require_admin)
):
    """Delete multiple alerts (Admin only)"""
    success = Alert.delete_multiple(request.alert_ids)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to delete alerts")
    AuditLog.log("ALERTS_DELETED", admin['id'], f"Deleted {len(request.alert_ids)} alerts")
    return {"message": f"Successfully deleted {len(request.alert_ids)} alerts"}


# ============================================================================
# MOBILE CLIENT ENDPOINTS (Protected - Guard/Admin)
# ============================================================================

class DeviceRegistration(BaseModel):
    fcm_token: str

@app.post("/api/devices/register", status_code=204)
async def register_device(
    body: DeviceRegistration,
    current_user: dict = Depends(require_guard_or_admin)
):
    """Register or update FCM device token for push notifications."""
    user_id = current_user["id"]
    query = "UPDATE users SET fcm_token = %s WHERE id = %s"
    try:
        db.execute_query(query, (body.fcm_token, user_id), fetch=False)
        logger.info(f"[MOBILE] FCM token registered for user {user_id}")
    except Exception as e:
        logger.error(f"[MOBILE] Failed to register device token: {e}")
        raise HTTPException(status_code=500, detail="Failed to register device token.")


@app.get("/api/alerts/active")
async def get_active_alerts(
    current_user: dict = Depends(require_guard_or_admin)
):
    """Return unresolved alerts for the mobile client.

    Maps the DB schema onto the AlertModel fields expected by the Flutter app:
      alert_id, track_id, state, duration, confidence, camera_id, timestamp, acknowledged
    """
    query = """
        SELECT
            id            AS alert_id,
            track_id,
            alert_type    AS state,
            camera_name   AS camera_id,
            triggered_at  AS timestamp,
            resolved_at
        FROM alerts
        WHERE resolved_at IS NULL
        ORDER BY triggered_at DESC
        LIMIT 100
    """
    rows = db.execute_query(query)
    result = []
    for row in rows:
        result.append({
            "alert_id":     row["alert_id"],
            "track_id":     row["track_id"],
            "state":        row["state"],          # 'warning' | 'danger'
            "duration":     0.0,                   # not persisted separately
            "confidence":   None,
            "camera_id":    row["camera_id"] or "main",
            "timestamp":    row["timestamp"].isoformat() if row.get("timestamp") else None,
            "acknowledged": False,
        })
    return result


@app.post("/api/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: int,
    current_user: dict = Depends(require_guard_or_admin)
):
    """Resolve an alert (set resolved_at). Used by the mobile guard client."""
    resolved = Alert.resolve(alert_id)
    if not resolved:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found or already resolved.")
    AuditLog.log(
        action="ALERT_ACKNOWLEDGED",
        user_id=current_user["id"],
        details=f"Alert {alert_id} acknowledged via mobile client",
    )
    logger.info(f"[MOBILE] Alert {alert_id} acknowledged by user {current_user['id']}")
    return {"detail": "Alert acknowledged."}


# ============================================================================
# CAMERA REGISTRY ENDPOINTS
# ============================================================================

class CameraCreate(BaseModel):
    camera_name: str
    pool_location: str = "Main Pool"
    rtsp_url: str
    hls_url: Optional[str] = None
    status: str = "active"
    assigned_guard_id: Optional[int] = None


class CameraUpdate(BaseModel):
    camera_name: Optional[str] = None
    pool_location: Optional[str] = None
    rtsp_url: Optional[str] = None
    hls_url: Optional[str] = None
    status: Optional[str] = None
    assigned_guard_id: Optional[int] = None


@app.get("/api/cameras")
async def list_cameras(
    current_user: dict = Depends(require_guard_or_admin)
):
    """
    Returns all active cameras.
    Guards receive cameras assigned to them OR unassigned ones.
    Admins receive all cameras.
    """
    try:
        if current_user["role"] == "admin":
            rows = db.execute_query(
                "SELECT id, camera_name, pool_location, rtsp_url, hls_url, status, assigned_guard_id "
                "FROM cameras ORDER BY id"
            )
        else:
            rows = db.execute_query(
                "SELECT id, camera_name, pool_location, rtsp_url, hls_url, status, assigned_guard_id "
                "FROM cameras "
                "WHERE status = 'active' AND (assigned_guard_id IS NULL OR assigned_guard_id = %s) "
                "ORDER BY id",
                (current_user["id"],)
            )
        result = []
        for row in rows:
            cam = dict(row)
            # Provide the MJPEG proxy URL the mobile app can consume directly
            cam["stream_url"] = cam.get("hls_url") or \
                f"/api/cameras/{cam['id']}/mjpeg"
            result.append(cam)
        return result
    except Exception as e:
        logger.error(f"[CAMERA] list_cameras error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cameras.")


@app.get("/api/cameras/{camera_id}")
async def get_camera(
    camera_id: int,
    current_user: dict = Depends(require_guard_or_admin)
):
    """Get a single camera by ID."""
    rows = db.execute_query(
        "SELECT id, camera_name, pool_location, rtsp_url, hls_url, status, assigned_guard_id "
        "FROM cameras WHERE id = %s",
        (camera_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Camera not found.")
    cam = dict(rows[0])
    cam["stream_url"] = cam.get("hls_url") or f"/api/cameras/{cam['id']}/mjpeg"
    return cam


@app.get("/api/cameras/{camera_id}/stream")
async def get_camera_stream_url(
    camera_id: int,
    current_user: dict = Depends(require_guard_or_admin)
):
    """Returns the streaming URL for a camera (MJPEG proxy or HLS)."""
    rows = db.execute_query(
        "SELECT id, camera_name, hls_url, rtsp_url, status FROM cameras WHERE id = %s",
        (camera_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Camera not found.")
    cam = rows[0]
    if cam["status"] != "active":
        raise HTTPException(status_code=503, detail="Camera is offline.")
    stream_url = cam["hls_url"] or f"/api/cameras/{camera_id}/mjpeg"
    return {
        "camera_id": camera_id,
        "camera_name": cam["camera_name"],
        "stream_url": stream_url,
        "rtsp_url": cam["rtsp_url"],
        "protocol": "hls" if cam["hls_url"] else "mjpeg",
    }


@app.get("/api/cameras/{camera_id}/mjpeg")
async def mjpeg_stream(
    camera_id: int,
    current_user: dict = Depends(get_current_user_from_query_token)
):
    """
    MJPEG streaming proxy — pushes frames from the continuous AI process
    over HTTP. This lets WebViews display the live feed efficiently.
    """
    rows = db.execute_query(
        "SELECT rtsp_url, status FROM cameras WHERE id = %s",
        (camera_id,)
    )
    if not rows:
        raise HTTPException(status_code=404, detail="Camera not found.")
    cam = rows[0]
    if cam["status"] != "active":
        raise HTTPException(status_code=503, detail="Camera is offline.")

    async def frame_generator():
        last_frame_no = -1
        while True:
            frame_data = BackgroundCameraManager.latest_frames.get(camera_id)
            if frame_data and frame_data.get('type') == 'frame':
                frame_no = frame_data.get('frame_number', -1)
                if frame_no != last_frame_no:
                    try:
                        jpg_bytes = base64.b64decode(frame_data['analysis_frame'])
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" + jpg_bytes + b"\r\n"
                        )
                        last_frame_no = frame_no
                    except Exception as e:
                        logger.error(f"[MJPEG] Error generating frame for camera {camera_id}: {e}")
            # Never break — stay connected even when the backend is reconnecting
            # to the RTSP source. The browser <img> / WebView will resume as soon
            # as new frames arrive, without needing a page reload.
            await asyncio.sleep(0.033)

    return StreamingResponse(
        frame_generator(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )


# ============================================================================
# BACKGROUND CONTINUOUS ANALYSIS (CCTV MANAGER)
# ============================================================================

class HeadlessCameraWebSocket:
    """A mock WebSocket that takes realtime analysis events from the backend ML engine
       and broadcasts them to any connected actual clients, or just silently runs."""
    def __init__(self, camera_id: int):
        self.camera_id = camera_id

    async def send_json(self, data: dict):
        # Never cache or forward 'complete' events — they are meaningless for live
        # CCTV streams and would confuse the frontend into thinking processing ended.
        if data.get('type') == 'complete':
            return

        BackgroundCameraManager.latest_frames[self.camera_id] = data
        
        subs = BackgroundCameraManager.subscribers.get(self.camera_id, [])
        disconnected = []
        for ws in subs:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
                
        for ws in disconnected:
            BackgroundCameraManager.unsubscribe(self.camera_id, ws)

    async def close(self, code=None, reason=None):
        pass


class BackgroundCameraManager:
    tasks: dict[int, asyncio.Task] = {}
    subscribers: dict[int, list[WebSocket]] = {}
    latest_frames: dict[int, dict] = {}

    @classmethod
    async def start_camera(cls, camera_id: int, rtsp_url: str):
        cls.stop_camera(camera_id)
        mock_ws = HeadlessCameraWebSocket(camera_id)
        logger.info(f"[CCTV MANAGER] Starting continuous analysis for Camera ID {camera_id}")
        
        async def run_loop():
            # Retry indefinitely — CCTV must keep running until the camera is
            # explicitly paused or deleted by the admin. Transient RTSP failures
            # (network glitches, camera reboots) are expected and should not
            # permanently disable the stream.
            consecutive_failures = 0
            while True:
                try:
                    await process_video_realtime(rtsp_url, mock_ws)  # This blocks while streaming
                    # If it returns gracefully (stream EOF), treat as a soft fail
                    # and immediately retry (camera may have reconnected).
                    logger.info(f"[CCTV MANAGER] Camera {camera_id} stream ended. Re-connecting…")
                    consecutive_failures = 0
                except asyncio.CancelledError:
                    # Task was explicitly cancelled (stop_camera or shutdown). Exit cleanly.
                    logger.info(f"[CCTV MANAGER] Camera {camera_id} task cancelled.")
                    return
                except Exception as e:
                    consecutive_failures += 1
                    logger.warning(
                        f"[CCTV MANAGER] Camera {camera_id} loop error (attempt {consecutive_failures}): {e}. Retrying in 5 s…"
                    )

                # Back-off: 5 s between reconnect attempts regardless of failure type.
                # The loop never exits on its own — only via CancelledError.
                backoff = min(5 * consecutive_failures, 60)  # cap at 60 s
                await asyncio.sleep(backoff if consecutive_failures > 0 else 2)
                
        cls.tasks[camera_id] = asyncio.create_task(run_loop())

    @classmethod
    def stop_camera(cls, camera_id: int):
        task = cls.tasks.pop(camera_id, None)
        if task:
            task.cancel()
            logger.info(f"[CCTV MANAGER] Stopped analysis for Camera ID {camera_id}")

    @classmethod
    def subscribe(cls, camera_id: int, ws: WebSocket):
        if camera_id not in cls.subscribers:
            cls.subscribers[camera_id] = []
        cls.subscribers[camera_id].append(ws)

    @classmethod
    def unsubscribe(cls, camera_id: int, ws: WebSocket):
        if camera_id in cls.subscribers and ws in cls.subscribers[camera_id]:
            cls.subscribers[camera_id].remove(ws)


@app.on_event("startup")
async def startup_cctv_manager():
    """Startup routine. Sets previously active cameras to inactive so they don't auto-connect."""
    try:
        db.execute_query("UPDATE cameras SET status = 'inactive' WHERE status = 'active'", fetch=False)
        logger.info("[CCTV MANAGER] Set all previously active cameras to inactive. Admin must resume them.")
    except Exception as e:
        logger.error(f"[CCTV MANAGER] Error starting up: {e}")

@app.on_event("shutdown")
async def shutdown_cctv_manager():
    """Gracefully cancel background tasks and mark cameras inactive."""
    for task in BackgroundCameraManager.tasks.values():
        task.cancel()
    try:
        db.execute_query("UPDATE cameras SET status = 'inactive' WHERE status = 'active'", fetch=False)
        logger.info("[CCTV MANAGER] Set all active cameras to inactive on shutdown.")
    except Exception as e:
        pass


@app.post("/api/cameras", status_code=201)
async def create_camera(
    body: CameraCreate,
    admin: dict = Depends(require_admin)
):
    """Register a new camera (Admin only)."""
    try:
        result = db.execute_query(
            "INSERT INTO cameras (camera_name, pool_location, rtsp_url, hls_url, status, assigned_guard_id) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (body.camera_name, body.pool_location, body.rtsp_url,
             body.hls_url, body.status, body.assigned_guard_id),
            fetch=False
        )
        AuditLog.log("CAMERA_CREATED", admin["id"], f"Camera '{body.camera_name}' registered")
        
        # Start background analysis if active
        if body.status == 'active':
            # Retrieve generated ID
            rows = db.execute_query("SELECT id FROM cameras ORDER BY id DESC LIMIT 1")
            if rows:
                new_id = rows[0]['id']
                await BackgroundCameraManager.start_camera(new_id, body.rtsp_url)
                
        return {"message": "Camera registered successfully."}
    except Exception as e:
        logger.error(f"[CAMERA] create error: {e}")
        raise HTTPException(status_code=500, detail="Failed to register camera.")


@app.patch("/api/cameras/{camera_id}")
async def update_camera(
    camera_id: int,
    body: CameraUpdate,
    admin: dict = Depends(require_admin)
):
    """Update camera details (Admin only)."""
    updates = {k: v for k, v in body.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")
    set_clause = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [camera_id]
    db.execute_query(f"UPDATE cameras SET {set_clause} WHERE id = %s", tuple(values), fetch=False)
    AuditLog.log("CAMERA_UPDATED", admin["id"], f"Camera ID {camera_id} updated")
    
    # Sync with background manager
    if 'status' in updates or 'rtsp_url' in updates:
        # fetch latest full row
        updated_row = db.execute_query("SELECT * FROM cameras WHERE id = %s", (camera_id,))
        if updated_row:
            cam = updated_row[0]
            if cam['status'] == 'active':
                await BackgroundCameraManager.start_camera(camera_id, cam['rtsp_url'])
            else:
                BackgroundCameraManager.stop_camera(camera_id)
                
    return {"message": "Camera updated."}


@app.delete("/api/cameras/{camera_id}")
async def delete_camera(
    camera_id: int,
    admin: dict = Depends(require_admin)
):
    """Delete a camera registration (Admin only)."""
    db.execute_query("DELETE FROM cameras WHERE id = %s", (camera_id,), fetch=False)
    AuditLog.log("CAMERA_DELETED", admin["id"], f"Camera ID {camera_id} deleted")
    BackgroundCameraManager.stop_camera(camera_id)
    return {"message": "Camera deleted."}


# ============================================================================
# VIDEO PROCESSING ENDPOINTS (Protected - Guard/Admin only)
# ============================================================================

# Data models
class YouTubeLink(BaseModel):
    url: str

# WebSocket connections list
active_connections = []

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove special characters and limit length"""
    # Get file extension
    name, ext = os.path.splitext(filename)
    # Remove or replace special characters
    name = re.sub(r'[^\w\s-]', '', name)
    # Replace spaces with underscores
    name = re.sub(r'\s+', '_', name)
    # Limit length to 100 characters
    name = name[:100]
    # Add timestamp to ensure uniqueness
    import time
    timestamp = str(int(time.time() * 1000))[-6:]
    return f"{name}_{timestamp}{ext}"

@app.post("/analyze/upload")
async def analyze_upload(file: UploadFile = File(...), current_user: dict = Depends(require_guard_or_admin)):
    """Upload and process video with real-time streaming (Protected)"""
    file_path = None
    try:
        # Sanitize and save uploaded file
        original_filename = file.filename
        safe_filename = sanitize_filename(original_filename)
        file_path = str(UPLOADS_DIR / safe_filename)
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)

        # Return success with video URL for native playback
        return JSONResponse(content={
            "status": "uploaded",
            "filename": safe_filename,
            "original_filename": original_filename,
            "filepath": file_path,
            "video_url": f"/video/{safe_filename}",
            "message": "Video uploaded successfully. Ready for playback and analysis."
        })
    except Exception as e:
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/youtube")
async def analyze_youtube(link: YouTubeLink, current_user: dict = Depends(require_guard_or_admin)):
    """Download and analyze YouTube video (Protected)"""
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Download YouTube video with progress
        logger.info(f"Starting YouTube download: {link.url}")
        
        ydl_opts = {
            'outtmpl': str(UPLOADS_DIR / '%(id)s.%(ext)s'),
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'quiet': False,
            'no_warnings': False,
            'extract_flat': False,
            'merge_output_format': 'mp4'
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link.url, download=True)
            file_path = ydl.prepare_filename(info)
            
            # Verify file actually exists
            if not os.path.exists(file_path):
                # Try with .mp4 extension if not found
                video_id = info.get('id', 'unknown')
                file_path = str(UPLOADS_DIR / f"{video_id}.mp4")
                
                if not os.path.exists(file_path):
                    logger.error(f"Downloaded file not found: {file_path}")
                    raise FileNotFoundError(f"Video file not created: {file_path}")
            
            filename = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            logger.info(f"YouTube download complete: {filename} ({file_size} bytes)")

        return JSONResponse(content={
            "status": "uploaded",
            "filename": filename,
            "filepath": file_path,
            "video_url": f"/video/{filename}",
            "message": f"YouTube video downloaded: {filename}",
            "size": file_size
        })
    except yt_dlp.utils.DownloadError as e:
        logger.error(f"YouTube download error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"YouTube download failed: {str(e)}")
    except FileNotFoundError as e:
        logger.error(f"File not found error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

@app.websocket("/ws/camera/{camera_id}")
async def websocket_continuous_camera(websocket: WebSocket, camera_id: int):
    """
    Connect to a continuous analysis stream.
    Used by the dashboard when 'Analyze with AI' taps into the background CCTV engine.
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
        
    try:
        current_user = await authenticate_websocket(token)
    except HTTPException as e:
        await websocket.close(code=1008, reason=str(e.detail))
        return

    await websocket.accept()
    BackgroundCameraManager.subscribe(camera_id, websocket)
    logger.info(f"[WEBSOCKET] User {current_user['name']} subscribed to Camera {camera_id} stream")
    
    # Send any immediate existing frame instantly so UI loads fast
    if camera_id in BackgroundCameraManager.latest_frames:
        try:
            await websocket.send_json(BackgroundCameraManager.latest_frames[camera_id])
        except:
            pass
            
    try:
        while True:
            # We keep the connection open, while the Headless mock sends the real updates
            message = await websocket.receive_text()
            if message == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        logger.info(f"[WEBSOCKET] User disconnected from Camera {camera_id}")
    finally:
        BackgroundCameraManager.unsubscribe(camera_id, websocket)

@app.websocket("/ws/process")
async def websocket_process_video(websocket: WebSocket):
    """
    WebSocket endpoint for real-time video processing
    Requires JWT authentication via query parameter: ?token=<jwt_token>
    """
    # Extract token from query parameters
    token = websocket.query_params.get("token")
    
    if not token:
        await websocket.close(code=1008, reason="Authentication required")
        return
    
    # Authenticate user
    try:
        current_user = await authenticate_websocket(token)
    except HTTPException as e:
        await websocket.close(code=1008, reason=str(e.detail))
        return
    
    await websocket.accept()
    active_connections.append(websocket)
    
    logger.info(f"[WEBSOCKET] User {current_user['name']} ({current_user['role']}) connected")

    try:
        while True:
            # Receive video path from client
            data = await websocket.receive_json()
            video_path = data.get("video_path")

            if not video_path or (
                not str(video_path).startswith(("rtsp://", "http://", "https://")) and 
                not os.path.exists(video_path)
            ):
                await websocket.send_json({
                    "type": "error",
                    "message": "Video file or stream not found"
                })
                continue

            # Process video and stream frames
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                await websocket.send_json({
                    "type": "error",
                    "message": "Could not open video stream"
                })
                continue

            # Send video info just once based on the original request
            await websocket.send_json({
                "type": "video_info",
                "fps": int(cap.get(cv2.CAP_PROP_FPS)),
                "total_frames": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            })

            # Process with tracking
            await process_video_realtime(video_path, websocket)

            cap.release()

            # Clean up uploaded file only if it's a local file
            if not str(video_path).startswith(("rtsp://", "http://", "https://")) and os.path.exists(video_path):
                os.remove(video_path)

    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"[WEBSOCKET] User {current_user['name']} disconnected")
    except Exception as e:
        logger.error(f"[WEBSOCKET] Error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.get("/download/{filename}")
async def download_annotated(filename: str, current_user: dict = Depends(require_guard_or_admin)):
    """Download processed video (Protected)"""
    file_path = str(OUTPUT_DIR / filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="video/mp4", filename=filename)
    raise HTTPException(status_code=404, detail="File not found")


@app.get("/video/{filename}")
async def stream_video(filename: str, request: Request):
    """Stream video with proper range request support for HTML5 video player"""
    file_path = str(UPLOADS_DIR / filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video not found")
    
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")
    
    if range_header:
        # Parse range header
        byte_range = range_header.replace("bytes=", "").split("-")
        start = int(byte_range[0]) if byte_range[0] else 0
        end = int(byte_range[1]) if len(byte_range) > 1 and byte_range[1] else file_size - 1
        
        # Read the requested chunk
        with open(file_path, "rb") as video_file:
            video_file.seek(start)
            data = video_file.read(end - start + 1)
        
        # Return partial content
        headers = {
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(len(data)),
            "Content-Type": "video/mp4",
        }
        return StreamingResponse(iter([data]), status_code=206, headers=headers)
    
    # Return full file if no range requested
    return FileResponse(file_path, media_type="video/mp4")

# ============================================================================
# FRONTEND PAGE ROUTES (Clean URLs without .html extension)
# ============================================================================
# These must be defined BEFORE the StaticFiles mount to take precedence

@app.get("/login")
async def login_redirect():
    """Redirect /login to /login.html"""
    return RedirectResponse(url="/login.html", status_code=302)

@app.get("/register")
async def register_redirect():
    """Redirect /register to /register.html"""
    return RedirectResponse(url="/register.html", status_code=302)

@app.get("/admin")
async def admin_redirect():
    """Redirect /admin to /admin.html"""
    return RedirectResponse(url="/admin.html", status_code=302)

# Mount uploads folder to serve videos
app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")

# Mount sounds folder to serve alarm audio
app.mount("/sounds", StaticFiles(directory=str(SOUNDS_DIR)), name="sounds")

# Mount frontend folder to serve HTML - MUST BE LAST
# Note: This serves index.html and other static HTML files from frontend/
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

if __name__ == "__main__":
    print("=" * 60)
    print("  🏊 PoolGaurd - Drowning Detection System")
    print("=" * 60)
    print(f"\n🌐 Server: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"🔐 Login: http://localhost:{SERVER_PORT}/login")
    print(f"📝 Register: http://localhost:{SERVER_PORT}/register")
    print(f"👤 Default admin: creagoouon@gmail.com / admin123")
    print(f"⚠️  CHANGE PASSWORD IMMEDIATELY!")
    print(f"\n✨ PoolGaurd - Advanced Pool Safety System\n")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)