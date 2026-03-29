import sys
import os
import asyncio
import logging
from pathlib import Path

# Configure logging FIRST
logging.basicConfig(level=logging.INFO)

# Add backend/ directory to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.database import db, Session, User, Alert, AuditLog
from core.notifications import create_notification_service, initialize_database
import config

async def test_push():
    print("Testing push notification...")
    
    # Init DB
    db.initialize(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        pool_size=1
    )
    
    # Init notification service
    initialize_database(Session, User, Alert, AuditLog)
    service = create_notification_service(config, use_database=True)
    
    print("Triggering DANGER alert to active sessions (or escalating to admin)...")
    await service._send_notification_async(
        track_id=999, 
        severity="DANGER", 
        camera_name="Test Push Camera",
        notification_key="test_key"
    )
    print("Done testing.")

if __name__ == "__main__":
    asyncio.run(test_push())
