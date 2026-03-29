"""
Main Entry Point for Drowning Detection System
This file imports and runs the FastAPI application from the core module
"""
import sys
import socket
from pathlib import Path

# Add backend/ directory to Python path so package imports (core, config, etc.) resolve
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the application
from core.app import app, SERVER_HOST, SERVER_PORT
import uvicorn


def _get_lan_ip() -> str:
    """Auto-detect this machine's LAN IP address."""
    try:
        # Create a dummy UDP socket and connect to an external address.
        # This tells the OS to pick the correct outbound interface without
        # actually sending any traffic.
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


if __name__ == "__main__":
    lan_ip = _get_lan_ip()
    mobile_url = f"http://{lan_ip}:{SERVER_PORT}"

    print("=" * 60)
    print("  🏊 PoolGuard - Drowning Detection System")
    print("=" * 60)
    print(f"\n🌐 Server: http://{SERVER_HOST}:{SERVER_PORT}")
    print(f"🔐 Login:  http://localhost:{SERVER_PORT}/login")
    print(f"📝 Register: http://localhost:{SERVER_PORT}/register")
    print()
    print("  ┌───────────────────────────────────────────────────┐")
    print(f"  │  📱 Mobile App URL: {mobile_url:<30s}│")
    print("  │  Copy this into the app's ⚙️  Server Config       │")
    print("  └───────────────────────────────────────────────────┘")
    print(f"\n✨ PoolGuard - Advanced Pool Safety System\n")
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)
