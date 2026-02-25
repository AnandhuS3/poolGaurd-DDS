"""
Centralized Logging Configuration for Drowning Detection System
Splits logs by module/function into organized log files in dlogs/ directory
"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import os

# Create dlogs directory structure
LOGS_DIR = Path(__file__).parent.parent / "dlogs"
LOGS_DIR.mkdir(exist_ok=True)

# Create subdirectories for different log categories
(LOGS_DIR / "app").mkdir(exist_ok=True)
(LOGS_DIR / "database").mkdir(exist_ok=True)
(LOGS_DIR / "video_processing").mkdir(exist_ok=True)
(LOGS_DIR / "notifications").mkdir(exist_ok=True)
(LOGS_DIR / "auth").mkdir(exist_ok=True)
(LOGS_DIR / "tracking").mkdir(exist_ok=True)
(LOGS_DIR / "errors").mkdir(exist_ok=True)
(LOGS_DIR / "websocket").mkdir(exist_ok=True)

# Log file paths
LOG_FILES = {
    # Application logs
    "app": LOGS_DIR / "app" / "application.log",
    "startup": LOGS_DIR / "app" / "startup.log",
    
    # Database logs
    "database": LOGS_DIR / "database" / "database.log",
    "database_errors": LOGS_DIR / "database" / "errors.log",
    
    # Video processing logs
    "video_processing": LOGS_DIR / "video_processing" / "processing.log",
    "model_loading": LOGS_DIR / "video_processing" / "model_loading.log",
    "detection": LOGS_DIR / "video_processing" / "detection.log",
    
    # Tracking logs
    "tracking": LOGS_DIR / "tracking" / "deepsort.log",
    "person_tracking": LOGS_DIR / "tracking" / "person_tracking.log",
    "state_changes": LOGS_DIR / "tracking" / "state_changes.log",
    
    # Notification logs
    "notifications": LOGS_DIR / "notifications" / "notifications.log",
    "alerts": LOGS_DIR / "notifications" / "alerts.log",
    
    # Authentication logs
    "auth": LOGS_DIR / "auth" / "authentication.log",
    "sessions": LOGS_DIR / "auth" / "sessions.log",
    
    # WebSocket logs
    "websocket": LOGS_DIR / "websocket" / "connections.log",
    "websocket_errors": LOGS_DIR / "websocket" / "errors.log",
    
    # Error logs
    "errors": LOGS_DIR / "errors" / "all_errors.log",
    "critical": LOGS_DIR / "errors" / "critical.log",
}

# Logging format
DETAILED_FORMAT = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

SIMPLE_FORMAT = logging.Formatter(
    '%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_rotating_handler(log_file, max_bytes=10*1024*1024, backup_count=5, formatter=DETAILED_FORMAT):
    """Create a rotating file handler"""
    handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding='utf-8'
    )
    handler.setFormatter(formatter)
    return handler

def setup_logger(name, log_file, level=logging.INFO, formatter=DETAILED_FORMAT, console=False):
    """Setup a logger with file and optional console output"""
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.propagate = False  # Prevent duplicate logs
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Add file handler
    file_handler = get_rotating_handler(log_file, formatter=formatter)
    logger.addHandler(file_handler)
    
    # Add console handler if requested
    if console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(SIMPLE_FORMAT)
        logger.addHandler(console_handler)
    
    return logger

# Initialize all loggers
def init_logging():
    """Initialize all logging handlers"""
    
    # Application loggers
    app_logger = setup_logger('core.app', LOG_FILES['app'], console=True)
    startup_logger = setup_logger('core.startup', LOG_FILES['startup'], console=True)
    
    # Database loggers
    db_logger = setup_logger('core.database', LOG_FILES['database'])
    db_error_logger = setup_logger('core.database.errors', LOG_FILES['database_errors'], level=logging.ERROR)
    
    # Video processing loggers
    video_logger = setup_logger('core.process_video', LOG_FILES['video_processing'], console=True)
    model_logger = setup_logger('core.process_video.models', LOG_FILES['model_loading'])
    detection_logger = setup_logger('core.process_video.detection', LOG_FILES['detection'])
    
    # Tracking loggers
    tracking_logger = setup_logger('deep_sort_realtime', LOG_FILES['tracking'])
    person_logger = setup_logger('core.tracking.persons', LOG_FILES['person_tracking'])
    state_logger = setup_logger('core.tracking.states', LOG_FILES['state_changes'])
    
    # Notification loggers
    notif_logger = setup_logger('core.notifications', LOG_FILES['notifications'])
    alert_logger = setup_logger('core.notifications.alerts', LOG_FILES['alerts'])
    
    # Authentication loggers
    auth_logger = setup_logger('core.auth', LOG_FILES['auth'])
    session_logger = setup_logger('core.auth.sessions', LOG_FILES['sessions'])
    
    # WebSocket loggers
    ws_logger = setup_logger('core.websocket', LOG_FILES['websocket'])
    ws_error_logger = setup_logger('core.websocket.errors', LOG_FILES['websocket_errors'], level=logging.ERROR)
    
    # Error loggers - catch all errors
    error_logger = setup_logger('errors', LOG_FILES['errors'], level=logging.ERROR)
    critical_logger = setup_logger('critical', LOG_FILES['critical'], level=logging.CRITICAL)
    
    # Setup asyncio error logging
    asyncio_logger = setup_logger('asyncio', LOG_FILES['errors'], level=logging.ERROR)
    
    # Add error handler to root logger to catch all errors
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    error_handler = get_rotating_handler(LOG_FILES['errors'])
    error_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_handler)
    
    print(f"✅ Logging initialized - Logs directory: {LOGS_DIR}")
    print(f"📁 Log categories: app, database, video_processing, tracking, notifications, auth, websocket, errors")
    
    return {
        'app': app_logger,
        'startup': startup_logger,
        'database': db_logger,
        'video': video_logger,
        'model': model_logger,
        'detection': detection_logger,
        'tracking': tracking_logger,
        'person': person_logger,
        'state': state_logger,
        'notifications': notif_logger,
        'alerts': alert_logger,
        'auth': auth_logger,
        'sessions': session_logger,
        'websocket': ws_logger,
        'errors': error_logger,
        'critical': critical_logger,
    }

# Convenience functions for logging
def log_startup(message):
    """Log startup messages"""
    logging.getLogger('core.startup').info(message)

def log_database(message, level='info'):
    """Log database operations"""
    logger = logging.getLogger('core.database')
    getattr(logger, level)(message)

def log_video_processing(message, level='info'):
    """Log video processing"""
    logger = logging.getLogger('core.process_video')
    getattr(logger, level)(message)

def log_state_change(person_id, old_state, new_state):
    """Log person state changes"""
    logger = logging.getLogger('core.tracking.states')
    logger.info(f"Person #{person_id}: {old_state} → {new_state}")

def log_alert(track_id, severity, camera_name):
    """Log alerts"""
    logger = logging.getLogger('core.notifications.alerts')
    logger.warning(f"ALERT: Track {track_id}, Severity: {severity}, Camera: {camera_name}")

def log_auth(message, level='info'):
    """Log authentication events"""
    logger = logging.getLogger('core.auth')
    getattr(logger, level)(message)

def log_websocket(message, level='info'):
    """Log WebSocket events"""
    logger = logging.getLogger('core.websocket')
    getattr(logger, level)(message)

def log_error(message, exc_info=None):
    """Log errors"""
    logger = logging.getLogger('errors')
    logger.error(message, exc_info=exc_info)

def log_critical(message, exc_info=None):
    """Log critical errors"""
    logger = logging.getLogger('critical')
    logger.critical(message, exc_info=exc_info)

# Initialize logging when module is imported
loggers = init_logging()

__all__ = [
    'init_logging',
    'loggers',
    'log_startup',
    'log_database',
    'log_video_processing',
    'log_state_change',
    'log_alert',
    'log_auth',
    'log_websocket',
    'log_error',
    'log_critical',
    'LOGS_DIR',
    'LOG_FILES',
]
