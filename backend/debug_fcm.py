"""
Debug FCM notification pipeline — run from project root with:
    .\.venv\Scripts\python.exe backend\debug_fcm.py
"""
import sys
import os
import logging
from pathlib import Path

# ── Path setup (backend/ must be importable as top-level) ─────────────────────
backend_root = Path(__file__).parent               # …/backend/
project_root = backend_root.parent                 # …/v5-poss/
sys.path.insert(0, str(backend_root))

# ── Load .env BEFORE any config import ────────────────────────────────────────
env_path = backend_root / "config" / ".env"
if env_path.exists():
    print(f"✅ Loading .env from: {env_path}")
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, val = line.partition("=")
                os.environ.setdefault(key.strip(), val.strip())
else:
    print(f"❌ .env not found at: {env_path}")

logging.basicConfig(level=logging.WARNING)

# ── Imports (after path + env are ready) ──────────────────────────────────────
from core.config import (
    DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD,
    FIREBASE_SA_PATH,
)
from core.database import db, Session, User

print(f"\n📋 FIREBASE_SA_PATH = {FIREBASE_SA_PATH}")

# ── Init DB ───────────────────────────────────────────────────────────────────
db.initialize(
    host=DB_HOST, port=DB_PORT,
    user=DB_USER, password=DB_PASSWORD,
    database=DB_NAME, pool_size=1
)

# ── Init Firebase ─────────────────────────────────────────────────────────────
try:
    import firebase_admin
    from firebase_admin import messaging, credentials

    try:
        firebase_admin.get_app()
        print("✅ Firebase already initialized")
    except ValueError:
        if FIREBASE_SA_PATH and Path(FIREBASE_SA_PATH).exists():
            firebase_admin.initialize_app(credentials.Certificate(FIREBASE_SA_PATH))
            print("✅ Firebase initialized from service account")
        else:
            print(f"❌ Firebase SA not found at: {FIREBASE_SA_PATH}")
            sys.exit(1)
except ImportError:
    print("❌ firebase_admin not installed — run: pip install firebase-admin")
    sys.exit(1)

# ── Check FCM tokens in DB ────────────────────────────────────────────────────
print("\n" + "="*60)
print("  FCM TOKEN CHECK")
print("="*60)

with Session() as session:
    users = session.query(User).all()
    if not users:
        print("❌ No users in the database!")
        sys.exit(1)

    all_tokens = []
    for u in users:
        token = getattr(u, 'fcm_token', None)
        tag = "✅ HAS TOKEN" if token else "❌ NO TOKEN "
        print(f"  [{tag}] {u.name}  ({u.email})  role={u.role}")
        if token:
            print(f"           {token[:50]}...{token[-8:]}")
            all_tokens.append(token)

if not all_tokens:
    print("\n❌ No FCM tokens found — push notifications CANNOT be delivered.")
    print("   Fix: Open the mobile app, log in, then re-run this script.")
    sys.exit(1)

# ── Send live test push ────────────────────────────────────────────────────────
print(f"\n" + "="*60)
print(f"  SENDING TEST PUSH → {len(all_tokens)} device(s)")
print("="*60)

msg = messaging.MulticastMessage(
    notification=messaging.Notification(
        title='🟠 STRUGGLING - Suspicious behaviour  [TEST]',
        body='Person #99 | Main Pool Camera | Severity: STRUGGLING'
    ),
    android=messaging.AndroidConfig(
        priority='high',
        notification=messaging.AndroidNotification(
            channel_id='dds_critical_alarm',
            default_sound=True,
            default_vibrate_timings=True,
            visibility='VISIBILITY_PUBLIC',
        )
    ),
    data={
        "track_id": "99",
        "state": "struggling",
        "duration": "5.0",
        "confidence": "92.0",
        "camera_id": "Main Pool Camera",
        "alert_id": "0",
        "timestamp": "2026-03-26T07:51:00",
    },
    tokens=all_tokens,
)

response = messaging.send_each_for_multicast(msg)
print(f"\n  ✅ Delivered: {response.success_count}")
print(f"  ❌ Failed:    {response.failure_count}")
for i, resp in enumerate(response.responses):
    if resp.success:
        print(f"     [{i}] ✅ {resp.message_id}")
    else:
        print(f"     [{i}] ❌ {resp.exception}")

print("\nDone. If delivered, the dialog should appear on the mobile app immediately.")
