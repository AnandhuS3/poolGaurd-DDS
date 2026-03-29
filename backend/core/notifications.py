"""
Remote Notification System for Drowning Detection
Sends alerts via Email, SMS, or WhatsApp when DANGER state is detected
Non-blocking, failure-safe implementation

AUTHENTICATION-AWARE:
- Sends notifications only to currently logged-in users
- Escalates to Admin if no Guard is logged in
- Uses stored contact details from database
"""
import logging
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, Dict, List

try:
    import firebase_admin
    from firebase_admin import messaging
    from firebase_admin import credentials
    FIREBASE_ENABLED = True
except ImportError:
    FIREBASE_ENABLED = False

logger = logging.getLogger(__name__)

# ── Lazy Firebase initialization ──────────────────────────────────────────────
# Do NOT initialize at import time — the .env / SA path may not be loaded yet.
# Call _ensure_firebase_initialized() right before each FCM send instead.

def _ensure_firebase_initialized() -> bool:
    """
    Initialize Firebase using the service account JSON, if not already done.
    Called lazily so that FIREBASE_SA_PATH is read AFTER the .env has been loaded.
    Returns True if Firebase is ready to use, False otherwise.
    """
    if not FIREBASE_ENABLED:
        return False
    if firebase_admin._apps:
        return True   # Already initialized
    try:
        import os
        sa_path = os.getenv("FIREBASE_SA_PATH", "").strip()
        if sa_path and os.path.exists(sa_path):
            cred = credentials.Certificate(sa_path)
            firebase_admin.initialize_app(cred)
            logger.info(f"[NOTIFICATION] Firebase initialized with service account: {sa_path}")
            return True
        else:
            logger.error(
                f"[NOTIFICATION] FIREBASE_SA_PATH not found or not set ('{sa_path}'). "
                "Push notifications disabled."
            )
            return False
    except Exception as e:
        logger.error(f"[NOTIFICATION] Firebase initialization failed: {e}")
        return False

# Import database models (will be set by initialize_database)
_db_session = None
_db_user = None
_db_alert = None
_db_audit = None

# REMOTE NOTIFICATION
class NotificationService:
    """
    Handles external notifications for drowning alerts.
    Supports Email (SMTP), SMS (Twilio), and WhatsApp (Twilio).
    Non-blocking and failure-safe.
    
    AUTHENTICATION-AWARE:
    - Sends notifications only to logged-in users
    - Escalates to admin if no guard is active
    """
    
    def __init__(self, config, use_database: bool = True):
        """Initialize notification service with configuration
        
        Args:
            config: Configuration dictionary or module
            use_database: If True, use database for user lookup (default: True)
        """
        self.enabled = config.get("NOTIFICATION_ENABLED", False) if hasattr(config, 'get') else getattr(config, "NOTIFICATION_ENABLED", False)
        self.notification_type = (config.get("NOTIFICATION_TYPE", "email") if hasattr(config, 'get') else getattr(config, "NOTIFICATION_TYPE", "email")).lower()
        self.config = config
        self.use_database = use_database
        
        # Track sent notifications to prevent duplicates within a short time window.
        self._sent_notification_times: dict = {}  # key -> last sent timestamp
        
        # Timing windows for alert de-duplication (seconds)
        self.DEFAULT_WINDOW = 60
        self.CRITICAL_WINDOW = 2 # DANGER
        self.STRUGGLING_WINDOW = 5 # STRUGGLING
        
        logger.info(f"[NOTIFICATION] Service initialized: Enabled={self.enabled}, Type={self.notification_type}, DB={use_database}")
    
    async def send_alert(self, track_id: int, severity: str, camera_name: str = "Main Camera", user_id: Optional[int] = None):
        """
        Send notification about drowning alert.
        Non-blocking, will not crash on failure.
        
        AUTHENTICATION-AWARE:
        - If use_database=True, sends to currently logged-in user
        - If no guard is logged in, escalates to admin
        - If use_database=False, falls back to config recipients (legacy mode)
        
        Args:
            track_id: Person tracking ID
            severity: Alert severity (WARNING or DANGER)
            camera_name: Source camera identifier
            user_id: Optional user ID (if not provided, will fetch active user from DB)
        """
        if not self.enabled:
            return
        
        # REMOTE NOTIFICATION - Prevent duplicate alerts within a 60-second window.
        # Using a time-windowed approach so alerts can re-fire across video sessions
        # rather than being permanently suppressed until the server restarts.
        notification_key = f"{track_id}_{severity.upper()}"
        now = datetime.now().timestamp()
        
        # Select window based on severity
        window = self.DEFAULT_WINDOW
        if severity.upper() == "DANGER":
            window = self.CRITICAL_WINDOW
        elif severity.upper() == "STRUGGLING":
            window = self.STRUGGLING_WINDOW
            
        last_sent = self._sent_notification_times.get(notification_key, 0)
        if now - last_sent < window:
            logger.debug(f"[NOTIFICATION] Skipping duplicate alert for {notification_key} (last sent {int(now - last_sent)}s ago)")
            return
        
        # Mark as sent immediately to prevent race conditions
        self._sent_notification_times[notification_key] = now
        
        # REMOTE NOTIFICATION - Run notification in background (non-blocking)
        asyncio.create_task(self._send_notification_async(track_id, severity, camera_name, notification_key, user_id))
    
    async def _send_notification_async(self, track_id: int, severity: str, camera_name: str, notification_key: str, user_id: Optional[int] = None):
        """
        Internal async method to send notification without blocking main processing.
        
        AUTHENTICATION-AWARE:
        - Determines recipient based on logged-in users
        - Escalates to admin if no guard is logged in
        - Records alert in database
        """
        try:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Determine recipient(s) and create alert record
            recipients = await self._get_alert_recipients(user_id)
            
            if not recipients:
                logger.warning(f"[NOTIFICATION] No recipients found for alert (Track #{track_id})")
                self._sent_notification_times.pop(notification_key, None)
                return
            
            # Create alert record in database
            alert_id = None
            if self.use_database and _db_alert:
                escalated = recipients.get('escalated', False)
                recipient_user_id = recipients.get('user_id')
                alert_id = _db_alert.create(
                    track_id=track_id,
                    alert_type=severity.lower(),
                    user_id=recipient_user_id,
                    camera_name=camera_name,
                    escalated_to_admin=escalated
                )
            
            # Format message with system timezone
            try:
                from core.region_utils import format_datetime
                timestamp = format_datetime()
            except:
                timestamp = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
            
            message = self._format_message(track_id, severity, camera_name, timestamp, recipients)
            
            # ALWAYS fire off Push Notifications (FCM) and Email in the background.
            # We DO NOT wait for them to finish to avoid blocking the critical path.
            # This ensures the AI loop continues analyzing without hitches.
            
            asyncio.create_task(self._send_push_notification(recipients, track_id, severity, camera_name, alert_id))
            
            if self.notification_type in ("email", "sms", "whatsapp"):
                # Use to_thread for the blocking SMTP logic
                asyncio.create_task(self._send_email(message, severity, recipients))
            
            # Mark notification as sent immediately (best effort)
            if alert_id and _db_alert:
                _db_alert.mark_notification_sent(alert_id, f"{self.notification_type}+fcm")
            
            recipient_info = f"{recipients['name']} ({recipients['role']})"
            logger.info(f"[NOTIFICATION] ✓ Sent {severity} alert for Person #{track_id} to {recipient_info} via {self.notification_type} and FCM")
            
        except Exception as e:
            # FAILURE SAFETY - Log error but DO NOT crash processing
            logger.error(f"[NOTIFICATION] ✗ Failed to send alert: {e}")
            import traceback
            logger.error(traceback.format_exc())
            # Remove from tracking to allow retry on next detection
            self._sent_notification_times.pop(notification_key, None)
    
    async def _get_alert_recipients(self, user_id: Optional[int] = None) -> Optional[Dict]:
        """
        Determine who should receive the alert based on authentication state.
        
        UPDATED LOGIC FOR PRODUCTION:
        1. If user_id provided, use that user
        2. Send to ALL ACTIVE USERS (logged in) - they all get notified
        3. If no users logged in, escalate to first available admin
        4. If database disabled, fall back to config recipients
        
        Returns:
            Dict with keys: user_id, name, email, phone_number, role, escalated, all_users (list)
            None if no recipients found
        """
        if not self.use_database or not _db_session or not _db_user:
            # Fall back to config-based recipients (legacy mode)
            recipients_list = self._get_config_recipients()
            if recipients_list:
                return {
                    'user_id': None,
                    'name': 'Config Recipients',
                    'email': recipients_list[0] if '@' in str(recipients_list[0]) else None,
                    'phone_number': recipients_list[0] if '@' not in str(recipients_list[0]) else None,
                    'role': 'unknown',
                    'escalated': False,
                    'recipients_list': recipients_list  # For backward compatibility
                }
            return None
        
        # If specific user_id provided, use that user
        if user_id:
            user = _db_user.get_by_id(user_id)
            if user and user['is_active']:
                return {
                    'user_id': user['id'],
                    'name': user['name'],
                    'email': user['email'],
                    'phone_number': user['phone_number'],
                    'role': user['role'],
                    'escalated': False,
                    'all_users': [user]
                }
        
        # Get ALL active logged-in users (guards, admins, and regular users)
        active_sessions = _db_session.get_all_active_sessions()
        
        if active_sessions:
            # Get user details for all active sessions
            active_users = []
            for session in active_sessions:
                user = _db_user.get_by_id(session['user_id'])
                if user and user['is_active']:
                    active_users.append(user)
            
            if active_users:
                # Primary recipient (first logged-in user, typically guard or admin)
                primary = active_users[0]
                logger.info(f"[NOTIFICATION] Sending alerts to {len(active_users)} active user(s)")
                return {
                    'user_id': primary['id'],
                    'name': primary['name'],
                    'email': primary['email'],
                    'phone_number': primary['phone_number'],
                    'role': primary['role'],
                    'escalated': False,
                    'all_users': active_users  # All users who should receive alerts
                }
        
        # No active users - escalate to admin
        admins = _db_user.get_all(role='admin', is_active=True)
        if admins:
            admin = admins[0]  # Use first active admin
            logger.warning(f"[NOTIFICATION] No active users - escalating alert to admin: {admin['name']}")
            return {
                'user_id': admin['id'],
                'name': admin['name'],
                'email': admin['email'],
                'phone_number': admin['phone_number'],
                'role': 'admin',
                'escalated': True,
                'all_users': [admin]
            }
        
        logger.error("[NOTIFICATION] No active users or admins found!")
        return None
    
    def _get_config_recipients(self) -> List[str]:
        """Get recipients from config (legacy mode)"""
        if hasattr(self.config, 'get'):
            return self.config.get("NOTIFICATION_RECIPIENTS", [])
        return getattr(self.config, "NOTIFICATION_RECIPIENTS", [])
    
    def _format_message(self, track_id: int, severity: str, camera_name: str, timestamp: str, recipients: Dict) -> str:
        """Format alert message"""
        if severity == "DANGER":
            urgency = "🚨 CRITICAL DROWNING ALERT"
        elif severity == "STRUGGLING":
            urgency = "🟠 STRUGGLING - Suspicious behaviour"
        else:
            urgency = "⚠️ WARNING - Potential Distress"
        
        escalation_note = ""
        if recipients.get('escalated'):
            escalation_note = "\n⚠️ ESCALATED: No users currently logged in\n"
        
        # Count total recipients
        all_users = recipients.get('all_users', [recipients])
        recipient_count = len(all_users)
        recipient_info = f"Alert sent to {recipient_count} active user(s)"
        
        message = f"""
{urgency}
{escalation_note}
Time: {timestamp}
Camera: {camera_name}
Person ID: #{track_id}
Severity: {severity}
{recipient_info}

⚠️ IMMEDIATE ACTION REQUIRED ⚡️
Check camera feed and respond immediately if assistance needed.

-- Drowning Detection System
"""
        return message
    
    async def _send_email(self, message: str, severity: str, recipients: Dict):
        """
        Send email notification to all active users
        
        Args:
            message: Email body
            severity: Alert severity
            recipients: Recipients dict with 'all_users' list
        """
        try:
            # Get SMTP settings
            smtp_server = self._get_config_value("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = self._get_config_value("SMTP_PORT", 587)
            smtp_user = self._get_config_value("SMTP_USERNAME", "")
            smtp_password = self._get_config_value("SMTP_PASSWORD", "")
            sender_email = self._get_config_value("SMTP_FROM_EMAIL", smtp_user) or smtp_user
            
            if not smtp_user or not smtp_password:
                logger.warning("[NOTIFICATION] SMTP credentials not configured, skipping email")
                return
            
            # Get all users to notify
            all_users = recipients.get('all_users', [recipients])
            recipient_emails = [user.get('email') or user['email'] for user in all_users if user.get('email')]
            
            if not recipient_emails:
                logger.warning("[NOTIFICATION] No email addresses found for recipients")
                return
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = ', '.join(recipient_emails[:3])  # Show first 3 in header
            if len(recipient_emails) > 3:
                msg['Bcc'] = ', '.join(recipient_emails[3:])  # BCC the rest
            msg['Subject'] = f"🚨 Drowning Alert - {severity} - URGENT"
            
            # HTML body for better formatting
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <div style="background: #fee; border-left: 4px solid #e63946; padding: 15px; margin-bottom: 20px;">
                        <h2 style="color: #e63946; margin: 0;">🚨 DROWNING ALERT</h2>
                    </div>
                    <pre style="background: #f5f5f5; padding: 15px; border-radius: 5px;">{message}</pre>
                    <p style="color: #666; font-size: 12px; margin-top: 30px;">
                        This is an automated alert from the Drowning Detection System.
                        <br>If you did not register for these alerts, please contact your system administrator.
                    </p>
                </body>
            </html>
            """
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            logger.info(f"[NOTIFICATION] ✓ Email sent to {len(recipient_emails)} recipient(s): {', '.join(recipient_emails)}")
            
        except Exception as e:
            logger.error(f"[NOTIFICATION] ✗ Email send failed: {e}")
            raise

    async def _send_push_notification(self, recipients: Dict, track_id: int, severity: str, camera_name: str, alert_id: Optional[int]):
        """
        Send FCM push notifications to all active users with registered devices.
        
        Args:
            recipients: Recipients dict with 'all_users' list
            track_id: Person tracking ID
            severity: Alert severity (warning/danger)
            camera_name: Camera name
            alert_id: Database Alert ID
        """
        if not _ensure_firebase_initialized():
            logger.warning("[NOTIFICATION] Firebase not ready. Skipping push notification.")
            return

        try:
            timestamp = datetime.now().isoformat()
            
            # The Flutter app expects certain fields in the data payload:
            # track_id, state, duration, confidence, camera_id, alert_id, timestamp
            data_payload = {
                "track_id": str(track_id),
                "state": severity.lower(),
                "duration": "0.0",
                "confidence": "95.0", # Mocked unless passed in
                "camera_id": str(camera_name),
                "alert_id": str(alert_id) if alert_id else "0",
                "timestamp": timestamp
            }

            all_users = recipients.get('all_users', [recipients])
            tokens = [user.get('fcm_token') for user in all_users if user.get('fcm_token')]

            if not tokens:
                logger.info("[NOTIFICATION] No FCM tokens found for active users. Skipping push notification.")
                return

            # Prepare message
            # For background/foreground FCM, we use a data-only message and let the Flutter app 
            # construct the local notification if it's in the foreground, or use FCM's default if background.
            # But here we will explicitly send a notification payload so iOS/Android display it automatically when in background.
            
            if severity.upper() == "DANGER":
                title = '🚨 DANGER — Possible drowning detected'
            elif severity.upper() == "STRUGGLING":
                title = '🟠 STRUGGLING — Suspicious behaviour'
            else:
                title = '⚠️ WARNING — Potential Distress'
            
            body = f'Track {track_id} — {camera_name}'

            android_config = messaging.AndroidConfig(
                priority='high', # Delivers as fast as possible, even in Doze mode
                notification=messaging.AndroidNotification(
                    channel_id='dds_critical_alarm' if severity.upper() == "DANGER" else 'dds_alerts',
                    default_sound=True,
                    default_vibrate_timings=True,
                    click_action='FLUTTER_NOTIFICATION_CLICK',
                    visibility='public' # Show on lock screen
                )
            )

            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        sound='default',
                        content_available=True,
                        mutable_content=True
                    )
                )
            )

            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                android=android_config,
                apns=apns_config,
                data=data_payload,
                tokens=tokens
            )

            # Send multicast message
            response = messaging.send_each_for_multicast(message)
            logger.info(f"[NOTIFICATION] ✓ FCM Push sent to {response.success_count} device(s). Failed: {response.failure_count}")
            
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        logger.error(f"[NOTIFICATION] FCM Push failed for token {tokens[idx]}: {resp.exception}")

        except Exception as e:
            logger.error(f"[NOTIFICATION] ✗ FCM Push send failed: {e}")
            # Do not raise, we don't want to crash the loop
    
    def _get_config_value(self, key: str, default=None):
        """Get config value (supports both dict-like and module config)"""
        if hasattr(self.config, 'get'):
            return self.config.get(key, default)
        return getattr(self.config, key, default)

    def send_verification_email(self, user_name: str, user_email: str, verification_url: str) -> bool:
        """
        Send email verification link to a newly registered user.

        Args:
            user_name: Name of the new user
            user_email: Email address to send to
            verification_url: Full https verification URL (contains token)

        Returns:
            bool: True if sent successfully
        """
        try:
            smtp_server = self._get_config_value("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = self._get_config_value("SMTP_PORT", 587)
            smtp_user = self._get_config_value("SMTP_USERNAME", "")
            smtp_password = self._get_config_value("SMTP_PASSWORD", "")
            sender_email = self._get_config_value("SMTP_FROM_EMAIL", smtp_user) or smtp_user

            if not smtp_user or not smtp_password:
                logger.warning("[NOTIFICATION] SMTP credentials not configured, skipping verification email")
                return False

            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = user_email
            msg['Subject'] = "Verify your PoolGuard account"

            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; background:#f5f5f5; padding:20px;">
                <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.12);">
                  <div style="background:linear-gradient(135deg,#3B82F6,#1D4ED8);padding:30px;text-align:center;">
                    <h1 style="color:#fff;margin:0;font-size:24px;">🏊 PoolGuard</h1>
                    <p style="color:rgba(255,255,255,.85);margin:8px 0 0;">Verify your email address</p>
                  </div>
                  <div style="padding:30px;">
                    <p style="font-size:16px;color:#333;">Hi <strong>{user_name}</strong>,</p>
                    <p style="color:#555;line-height:1.6;">
                      Thank you for registering. Please verify your email address by clicking the button below.
                      This link expires in <strong>30 minutes</strong>.
                    </p>
                    <div style="text-align:center;margin:30px 0;">
                      <a href="{verification_url}"
                         style="background:#3B82F6;color:#fff;padding:14px 32px;text-decoration:none;
                                border-radius:6px;font-weight:bold;display:inline-block;">
                        ✅ Verify Email Address
                      </a>
                    </div>
                    <p style="color:#888;font-size:13px;">
                      If the button doesn't work, copy and paste this link into your browser:<br>
                      <a href="{verification_url}" style="color:#3B82F6;word-break:break-all;">{verification_url}</a>
                    </p>
                    <p style="color:#aaa;font-size:12px;margin-top:24px;">
                      If you did not create an account, you can safely ignore this email.
                    </p>
                  </div>
                </div>
              </body>
            </html>
            """
            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            # Do NOT log the verification URL/token in production
            logger.info(f"[NOTIFICATION] ✅ Verification email sent to {user_email}")
            return True

        except Exception as e:
            logger.error(f"[NOTIFICATION] ❌ Failed to send verification email to {user_email}: {e}")
            return False

    def send_password_reset_email(self, user_name: str, user_email: str, reset_url: str) -> bool:
        """
        Send password reset link to user.

        Args:
            user_name: Name of the user
            user_email: Email address to send to
            reset_url: Full https password-reset URL (contains token)

        Returns:
            bool: True if sent successfully
        """
        try:
            smtp_server = self._get_config_value("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = self._get_config_value("SMTP_PORT", 587)
            smtp_user = self._get_config_value("SMTP_USERNAME", "")
            smtp_password = self._get_config_value("SMTP_PASSWORD", "")
            sender_email = self._get_config_value("SMTP_FROM_EMAIL", smtp_user) or smtp_user

            if not smtp_user or not smtp_password:
                logger.warning("[NOTIFICATION] SMTP credentials not configured, skipping password reset email")
                return False

            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = user_email
            msg['Subject'] = "Reset your PoolGuard password"

            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; background:#f5f5f5; padding:20px;">
                <div style="max-width:560px;margin:0 auto;background:#fff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,.12);">
                  <div style="background:linear-gradient(135deg,#EF4444,#B91C1C);padding:30px;text-align:center;">
                    <h1 style="color:#fff;margin:0;font-size:24px;">🔑 Password Reset</h1>
                    <p style="color:rgba(255,255,255,.85);margin:8px 0 0;">PoolGuard Drowning Detection System</p>
                  </div>
                  <div style="padding:30px;">
                    <p style="font-size:16px;color:#333;">Hi <strong>{user_name}</strong>,</p>
                    <p style="color:#555;line-height:1.6;">
                      We received a request to reset your password. Click the button below to choose a new password.
                      This link expires in <strong>30 minutes</strong> and can only be used once.
                    </p>
                    <div style="text-align:center;margin:30px 0;">
                      <a href="{reset_url}"
                         style="background:#EF4444;color:#fff;padding:14px 32px;text-decoration:none;
                                border-radius:6px;font-weight:bold;display:inline-block;">
                        🔒 Reset Password
                      </a>
                    </div>
                    <p style="color:#888;font-size:13px;">
                      If the button doesn't work, copy and paste this link:<br>
                      <a href="{reset_url}" style="color:#EF4444;word-break:break-all;">{reset_url}</a>
                    </p>
                    <p style="color:#aaa;font-size:12px;margin-top:24px;">
                      If you did not request a password reset, please ignore this email.
                      Your password will not change.
                    </p>
                  </div>
                </div>
              </body>
            </html>
            """
            msg.attach(MIMEText(html_body, 'html'))

            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)

            logger.info(f"[NOTIFICATION] ✅ Password reset email sent to {user_email}")
            return True

        except Exception as e:
            logger.error(f"[NOTIFICATION] ❌ Failed to send password reset email to {user_email}: {e}")
            return False

    def send_welcome_email(self, user_name: str, user_email: str, role: str) -> bool:
        """
        Send welcome email to newly registered user
        
        Args:
            user_name: Name of the new user
            user_email: Email address of the new user
            role: User role (admin/guard/user)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Get SMTP settings
            smtp_server = self._get_config_value("SMTP_SERVER", "smtp.gmail.com")
            smtp_port = self._get_config_value("SMTP_PORT", 587)
            smtp_user = self._get_config_value("SMTP_USERNAME", "")
            smtp_password = self._get_config_value("SMTP_PASSWORD", "")
            sender_email = self._get_config_value("SMTP_FROM_EMAIL", smtp_user) or smtp_user
            
            if not smtp_user or not smtp_password:
                logger.warning("[NOTIFICATION] SMTP credentials not configured for welcome email")
                return False
            
            # Import system timezone utilities
            try:
                from core.region_utils import get_system_time, format_datetime
                current_time = get_system_time()
                timestamp = format_datetime(current_time)
            except Exception as e:
                timestamp = datetime.now().strftime("%d-%m-%Y %I:%M:%S %p")
            
            # Create email
            msg = MIMEMultipart('alternative')
            msg['From'] = sender_email
            msg['To'] = user_email
            msg['Subject'] = f"Welcome to PoolGaurd - Drowning Detection System"
            
            # Create HTML email body
            role_emoji = {
                'admin': '👑',
                'guard': '🛡️',
                'user': '👤'
            }.get(role, '👤')
            
            role_description = {
                'admin': 'Full system administrator with complete access',
                'guard': 'Security guard with monitoring and alert capabilities',
                'user': 'User with alert notification access'
            }.get(role, 'User with notification access')
            
            html_body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                        <!-- Header -->
                        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                            <h1 style="color: white; margin: 0; font-size: 28px;">🏊 Welcome to</h1>
                            <h2 style="color: white; margin: 10px 0 0 0; font-size: 24px;">PoolGaurd</h2>
                            <p style="color: rgba(255,255,255,0.9); margin: 10px 0 0 0;">Drowning Detection System</p>
                        </div>
                        
                        <!-- Body -->
                        <div style="padding: 30px;">
                            <p style="font-size: 18px; color: #333; margin-top: 0;">
                                <strong>Namaste {user_name}! {role_emoji}</strong>
                            </p>
                            
                            <p style="color: #555; line-height: 1.6;">
                                Your account has been successfully created in the Drowning Detection System.
                            </p>
                            
                            <div style="background: #e3f2fd; border-left: 4px solid #2196f3; padding: 15px; margin: 20px 0;">
                                <h3 style="color: #1976d2; margin: 0 0 10px 0;">📋 Account Details</h3>
                                <p style="margin: 5px 0; color: #333;"><strong>Name:</strong> {user_name}</p>
                                <p style="margin: 5px 0; color: #333;"><strong>Email:</strong> {user_email}</p>
                                <p style="margin: 5px 0; color: #333;"><strong>Role:</strong> {role.title()} {role_emoji}</p>
                                <p style="margin: 5px 0; color: #666; font-size: 14px;">{role_description}</p>
                                <p style="margin: 10px 0 0 0; color: #666; font-size: 14px;">
                                    <strong>Registered:</strong> {timestamp}
                                </p>
                            </div>
                            
                            <div style="background: #fff3e0; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0;">
                                <h3 style="color: #f57c00; margin: 0 0 10px 0;">🔔 Alert Notifications</h3>
                                <p style="margin: 0; color: #555; line-height: 1.6;">
                                    You will receive <strong>real-time email alerts</strong> at this address (<strong>{user_email}</strong>) 
                                    whenever the system detects a potential drowning incident while you are logged in.
                                </p>
                            </div>
                            
                            <div style="background: #f3e5f5; border-left: 4px solid #9c27b0; padding: 15px; margin: 20px 0;">
                                <h3 style="color: #7b1fa2; margin: 0 0 10px 0;">🚀 Getting Started</h3>
                                <ol style="margin: 10px 0; padding-left: 20px; color: #555; line-height: 1.8;">
                                    <li>Login to the system using your credentials</li>
                                    <li>Keep your session active to receive alerts</li>
                                    <li>Monitor the live camera feed for any incidents</li>
                                    <li>Respond immediately when alerts are triggered</li>
                                </ol>
                            </div>
                            
                            <div style="text-align: center; margin: 30px 0;">
                                <a href="http://localhost:8000/login.html" 
                                   style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                                          color: white; 
                                          padding: 12px 30px; 
                                          text-decoration: none; 
                                          border-radius: 5px; 
                                          display: inline-block;
                                          font-weight: bold;">
                                    🔐 Login to System
                                </a>
                            </div>
                            
                            <div style="background: #f5f5f5; padding: 15px; border-radius: 5px; margin-top: 20px;">
                                <p style="margin: 0; color: #666; font-size: 14px; text-align: center;">
                                    <strong>System Email:</strong> {sender_email}<br>
                                    All drowning alerts will be sent from this address
                                </p>
                            </div>
                        </div>
                        
                        <!-- Footer -->
                        <div style="background: #f5f5f5; padding: 20px; text-align: center; border-top: 1px solid #ddd;">
                            <p style="color: #666; margin: 0; font-size: 14px;">
                                PoolGaurd - Drowning Detection System
                            </p>
                            <p style="color: #999; margin: 10px 0 0 0; font-size: 12px;">
                                This is an automated message from the Drowning Detection System
                            </p>
                        </div>
                    </div>
                </body>
            </html>
            """
            
            # Attach HTML body
            msg.attach(MIMEText(html_body, 'html'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port, timeout=10) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            
            logger.info(f"[NOTIFICATION] ✅ Welcome email sent to {user_email} (Role: {role})")
            return True
            
        except Exception as e:
            logger.error(f"[NOTIFICATION] ❌ Failed to send welcome email to {user_email}: {e}")
            return False


# Database initialization
def initialize_database(session_model, user_model, alert_model, audit_model):
    """
    Initialize database models for notification service.
    Must be called before using database-aware notifications.
    
    Args:
        session_model: Session model class
        user_model: User model class
        alert_model: Alert model class
        audit_model: AuditLog model class
    """
    global _db_session, _db_user, _db_alert, _db_audit
    _db_session = session_model
    _db_user = user_model
    _db_alert = alert_model
    _db_audit = audit_model
    logger.info("[NOTIFICATION] Database models initialized")


# Factory function to create notification service
def create_notification_service(config_dict: dict, use_database: bool = True) -> NotificationService:
    """
    Create and return a NotificationService instance.
    
    Args:
        config_dict: Configuration dictionary containing notification settings
        use_database: If True, use database for user lookup (default: True)
    
    Returns:
        NotificationService instance
    """
    return NotificationService(config_dict, use_database=use_database)


def reset_notifications():
    """Reset notification tracking (useful for testing)"""
    logger.info("[NOTIFICATION] Notification tracking reset")
