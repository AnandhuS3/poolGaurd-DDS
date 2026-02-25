"""
Quick test script to verify the new logging system works
"""

from core.logging_config import (
    loggers, 
    log_startup, 
    log_database, 
    log_video_processing,
    log_state_change,
    log_alert,
    log_auth,
    log_websocket,
    LOGS_DIR
)

print("=" * 60)
print("Testing New Logging System")
print("=" * 60)

# Test all loggers
print("\n1. Testing Application Logger...")
loggers['app'].info("[TEST] Application logger working")
log_startup("[TEST] Startup logger working")

print("2. Testing Database Logger...")
loggers['database'].info("[TEST] Database logger working")
log_database("[TEST] Database operation logged")

print("3. Testing Video Processing Logger...")
loggers['video'].info("[TEST] Video processing logger working")
log_video_processing("[TEST] Video processing operation logged")

print("4. Testing Model Logger...")
loggers['model'].info("[TEST] Model loading logger working")

print("5. Testing Detection Logger...")
loggers['detection'].info("[TEST] Detection logger working")

print("6. Testing Tracking Loggers...")
loggers['tracking'].info("[TEST] DeepSORT tracker logger working")
loggers['person'].info("[TEST] Person tracking logger working")
log_state_change(person_id=999, old_state="SAFE", new_state="WARNING")

print("7. Testing Notification Loggers...")
loggers['notifications'].info("[TEST] Notification logger working")
log_alert(track_id=999, severity="DANGER", camera_name="Test Camera")

print("8. Testing Auth Loggers...")
loggers['auth'].info("[TEST] Auth logger working")
log_auth("[TEST] Authentication event logged")

print("9. Testing WebSocket Loggers...")
loggers['websocket'].info("[TEST] WebSocket logger working")
log_websocket("[TEST] WebSocket connection logged")

print("10. Testing Error Loggers...")
loggers['errors'].error("[TEST] Error logger working")
loggers['critical'].critical("[TEST] Critical logger working")

print("\n" + "=" * 60)
print("✅ All loggers tested successfully!")
print("=" * 60)
print(f"\n📁 Logs directory: {LOGS_DIR}")
print("\nCheck the following log files:")
print("  - dlogs/app/application.log")
print("  - dlogs/app/startup.log")
print("  - dlogs/database/database.log")
print("  - dlogs/video_processing/processing.log")
print("  - dlogs/tracking/state_changes.log")
print("  - dlogs/notifications/alerts.log")
print("  - dlogs/auth/authentication.log")
print("  - dlogs/websocket/connections.log")
print("  - dlogs/errors/all_errors.log")
print("\n" + "=" * 60)
