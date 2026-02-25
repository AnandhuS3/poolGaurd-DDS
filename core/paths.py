"""
Centralized Path Configuration for Drowning Detection System
All file paths are defined here to avoid hardcoding throughout the codebase
"""
import os
from pathlib import Path

# ============================================================================
# BASE PATHS
# ============================================================================
# Project root directory (parent of core/ directory where this file is located)
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

# ============================================================================
# MODEL PATHS
# ============================================================================
WEIGHTS_DIR = PROJECT_ROOT / "weights"
MODEL_PRIMARY = WEIGHTS_DIR / "best.pt"
MODEL_SECONDARY = WEIGHTS_DIR / "best1.pt"

# ============================================================================
# DATA DIRECTORIES
# ============================================================================
UPLOADS_DIR = PROJECT_ROOT / "uploads"
OUTPUT_DIR = PROJECT_ROOT / "output"
SOUNDS_DIR = PROJECT_ROOT / "sounds"

# ============================================================================
# FRONTEND PATHS
# ============================================================================
# Frontend HTML files are in frontend/ directory
FRONTEND_DIR = PROJECT_ROOT / "frontend"
CLIENT_INDEX = FRONTEND_DIR / "index.html"
CLIENT_LOGIN = FRONTEND_DIR / "login.html"
CLIENT_REGISTER = FRONTEND_DIR / "register.html"
CLIENT_ADMIN = FRONTEND_DIR / "admin.html"

# ============================================================================
# DATABASE PATHS
# ============================================================================
DATABASE_DIR = PROJECT_ROOT / "database"
SCHEMA_FILE = DATABASE_DIR / "schema.sql"

# ============================================================================
# LOG PATHS
# ============================================================================
LOG_FILE = PROJECT_ROOT / "drowning_detection.log"

# ============================================================================
# SOUND FILES
# ============================================================================
ALARM_SOUND = SOUNDS_DIR / "alarm.mp3"

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def ensure_directories():
    """
    Create required directories if they don't exist.
    Call this during application startup.
    """
    directories = [
        UPLOADS_DIR,
        OUTPUT_DIR,
        SOUNDS_DIR,
        WEIGHTS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        
    return True


def get_upload_path(filename: str) -> Path:
    """Get full path for uploaded file"""
    return UPLOADS_DIR / filename


def get_output_path(filename: str) -> Path:
    """Get full path for output file"""
    return OUTPUT_DIR / filename


def validate_paths():
    """
    Validate that critical paths exist.
    Returns list of missing critical files.
    """
    missing = []
    
    # Check critical files
    if not MODEL_PRIMARY.exists():
        missing.append(f"Primary YOLO model: {MODEL_PRIMARY}")
    
    if not SCHEMA_FILE.exists():
        missing.append(f"Database schema: {SCHEMA_FILE}")
    
    return missing


# ============================================================================
# PATH STRINGS (for backward compatibility)
# ============================================================================
# Some libraries require string paths instead of Path objects
# Use these when needed

def get_model_path_str() -> str:
    """Get primary model path as string"""
    return str(MODEL_PRIMARY)


def get_model_secondary_path_str() -> str:
    """Get secondary model path as string"""
    return str(MODEL_SECONDARY)


def get_schema_path_str() -> str:
    """Get schema file path as string"""
    return str(SCHEMA_FILE)


# ============================================================================
# INITIALIZATION
# ============================================================================
# # Ensure directories exist when module is imported
# ensure_directories()

# Print path information (helpful for debugging)
if __name__ == "__main__":
    print("=" * 60)
    print("  Drowning Detection System - Path Configuration")
    print("=" * 60)
    print(f"\n📁 Project Root: {PROJECT_ROOT}")
    print(f"\n🤖 Models:")
    print(f"   Primary:   {MODEL_PRIMARY} {'✅' if MODEL_PRIMARY.exists() else '❌'}")
    print(f"   Secondary: {MODEL_SECONDARY} {'✅' if MODEL_SECONDARY.exists() else '⚠️ (optional)'}")
    print(f"\n📂 Directories:")
    print(f"   Uploads: {UPLOADS_DIR} {'✅' if UPLOADS_DIR.exists() else '❌'}")
    print(f"   Output:  {OUTPUT_DIR} {'✅' if OUTPUT_DIR.exists() else '❌'}")
    print(f"   Sounds:  {SOUNDS_DIR} {'✅' if SOUNDS_DIR.exists() else '❌'}")
    print(f"\n🗄️ Database:")
    print(f"   Schema: {SCHEMA_FILE} {'✅' if SCHEMA_FILE.exists() else '❌'}")
    print(f"\n📝 Logs:")
    print(f"   Log file: {LOG_FILE}")
    
    # Validate
    missing = validate_paths()
    if missing:
        print(f"\n⚠️ Missing critical files:")
        for item in missing:
            print(f"   - {item}")
    else:
        print(f"\n✅ All critical paths validated")
    
    print("=" * 60)
