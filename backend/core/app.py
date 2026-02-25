from fastapi import FastAPI, UploadFile, File, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
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
import mysql.connector
from mysql.connector import Error

# Import authentication and database modules
from core.database import db, User, Session, Alert, AuditLog
from core.auth import (
    AuthService, LoginRequest, RegisterRequest, UpdateUserRequest,
    AuthResponse, get_current_user, require_admin, require_guard_or_admin,
    authenticate_websocket, get_client_ip, get_user_agent,
    PasswordHasher
)
from core.notifications import initialize_database, NotificationService
from core import config as app_config
from core.paths import UPLOADS_DIR, OUTPUT_DIR, SOUNDS_DIR, get_schema_path_str, ensure_directories, FRONTEND_DIR

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

def ensure_database_ready():
    """
    Automatically set up database on startup:
    1. Create database if it doesn't exist
    2. Create tables from schema.sql if they don't exist
    3. Create default admin user if no users exist
    """
    logger.info("[DATABASE] Checking database setup...")
    
    # Step 1: Ensure database exists
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        cursor.execute(f"USE {DB_NAME}")
        conn.commit()
        logger.info(f"[DATABASE] Database '{DB_NAME}' ready")
        
        # Step 2: Check if tables exist
        cursor.execute("SHOW TABLES")
        tables = [table[0] for table in cursor.fetchall()]
        
        if len(tables) < 5:  # We expect 5 tables
            logger.info("[DATABASE] Tables missing, creating from schema.sql...")
            
            # Read and execute schema.sql
            schema_path = get_schema_path_str()
            if os.path.exists(schema_path):
                with open(schema_path, 'r', encoding='utf-8') as f:
                    schema = f.read()
                
                # Execute schema statements
                statements = [s.strip() for s in schema.split(';') if s.strip()]
                for statement in statements:
                    if statement and not statement.startswith('--'):
                        try:
                            cursor.execute(statement)
                        except Error as e:
                            if "already exists" not in str(e).lower():
                                logger.warning(f"[DATABASE] Schema warning: {e}")
                
                conn.commit()
                logger.info("[DATABASE] Tables created successfully")
            else:
                logger.warning("[DATABASE] schema.sql not found, skipping table creation")
        else:
            logger.info(f"[DATABASE] Found {len(tables)} tables")
        
        # Step 3: Check if admin user exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
        admin_count = cursor.fetchone()[0]
        
        if admin_count == 0:
            logger.info("[DATABASE] No admin user found, creating default admin...")
            
            # Create default admin user
            password_hash = PasswordHasher.hash_password("admin123")
            insert_query = """
                INSERT INTO users (username, email, password_hash, role, phone_number, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            cursor.execute(insert_query, ('admin', 'admin@dds.local', password_hash, 'admin', '+00 00000 00000'))
            conn.commit()
            logger.info("[DATABASE] [OK] Default admin created: admin@dds.local / admin123")
        else:
            logger.info(f"[DATABASE] Found {admin_count} admin user(s)")
        
        cursor.close()
        conn.close()
        logger.info("[DATABASE] [OK] Database ready!")
        
    except Error as e:
        logger.error(f"[DATABASE] [ERROR] Setup error: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """Run database checks on startup"""
    ensure_database_ready()

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
    logger.info("[DATABASE] Successfully connected to MySQL")
except Exception as e:
    logger.error(f"[DATABASE] Failed to initialize: {e}")
    logger.warning("[DATABASE] Running without authentication support")

# Create notification service for welcome emails
notification_service = NotificationService(app_config, use_database=True)

# CORS middleware to allow browser access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.post("/api/auth/register", response_model=AuthResponse)
async def register(user_data: RegisterRequest, request: Request):
    """
    Public user registration endpoint
    Anyone can register as a 'guard' role
    """
    ip_address = get_client_ip(request)
    user_agent = get_user_agent(request)
    
    # Force role to 'guard' for public registrations
    user_info = AuthService.register_user(
        name=user_data.name,
        email=user_data.email,
        phone_number=user_data.phone_number,
        password=user_data.password,
        role='guard',  # Public registrations are 'guard' role by default
        created_by=None  # Self-registration
    )
    
    # Send welcome email in background (non-blocking)
    try:
        asyncio.create_task(
            asyncio.to_thread(
                notification_service.send_welcome_email,
                user_data.name,
                user_data.email,
                'guard'
            )
        )
        logger.info(f"[REGISTRATION] Welcome email queued for {user_data.email}")
    except Exception as e:
        logger.error(f"[REGISTRATION] Failed to queue welcome email: {e}")
    
    # Auto-login after registration
    access_token, user_info = AuthService.login(
        user_data.email,
        user_data.password,
        ip_address,
        user_agent
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_info
    }


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

            if not video_path or not os.path.exists(video_path):
                await websocket.send_json({
                    "type": "error",
                    "message": "Video file not found"
                })
                continue

            # Process video and stream frames
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                await websocket.send_json({
                    "type": "error",
                    "message": "Could not open video"
                })
                continue

            # Get video properties
            fps = int(cap.get(cv2.CAP_PROP_FPS))
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            await websocket.send_json({
                "type": "video_info",
                "fps": fps,
                "total_frames": total_frames,
                "width": width,
                "height": height
            })

            # Process with tracking
            await process_video_realtime(video_path, websocket)

            cap.release()

            # Clean up uploaded file
            if os.path.exists(video_path):
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
    print(f"👤 Default admin: admin@dds.local / admin123")
    print(f"⚠️  CHANGE PASSWORD IMMEDIATELY!")
    print(f"\n✨ PoolGaurd - Advanced Pool Safety System\n")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)