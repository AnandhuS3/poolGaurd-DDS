"""
Main Entry Point for Drowning Detection System
This file imports and runs the FastAPI application from the core module
"""
import sys
from pathlib import Path

# Add backend/ directory to Python path so package imports (core, config, etc.) resolve
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the application
from core.app import app, SERVER_HOST, SERVER_PORT
import uvicorn

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
