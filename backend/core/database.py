"""
Database connection and models for Drowning Detection System
Implements PostgreSQL connection pooling and data models
"""
import psycopg2
import psycopg2.pool
import psycopg2.extras
from psycopg2 import Error
from typing import Optional, Dict, List, Any
from datetime import datetime
import logging
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """PostgreSQL database connection pool manager"""

    _instance = None
    _pool = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
        return cls._instance

    def initialize(self, host: str, port: int, user: str, password: str, database: str, pool_size: int = 5):
        """
        Initialize database connection pool

        Args:
            host: PostgreSQL host
            port: PostgreSQL port
            user: PostgreSQL username
            password: PostgreSQL password
            database: Database name
            pool_size: Connection pool size
        """
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=pool_size,
                host=host,
                port=port,
                user=user,
                password=password,
                dbname=database,
            )
            logger.info(f"[DATABASE] Connection pool initialized: {host}:{port}/{database}")
        except Error as e:
            logger.error(f"[DATABASE] Failed to create connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """
        Context manager for database connections.
        Returns a connection with RealDictCursor support.
        Automatically handles commit/rollback and connection return to pool.

        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
                cursor.execute("SELECT * FROM users")
                results = cursor.fetchall()
        """
        if self._pool is None:
            raise RuntimeError(
                "Database connection pool is not initialized. "
                "PostgreSQL may have been unavailable when the server started. "
                "Restart the server after ensuring PostgreSQL is running."
            )
        connection = None
        try:
            connection = self._pool.getconn()
            yield connection
            connection.commit()
        except Error as e:
            if connection:
                connection.rollback()
            logger.error(f"[DATABASE] Transaction error: {e}")
            raise
        finally:
            if connection:
                self._pool.putconn(connection)

    def execute_query(self, query: str, params: tuple = None, fetch: bool = True) -> Optional[List[Dict]]:
        """
        Execute a query and return results.

        Args:
            query: SQL query (use %s placeholders)
            params: Query parameters (tuple)
            fetch: Whether to fetch results

        Returns:
            List of dicts for SELECT queries, lastrowid int for INSERT, None otherwise
        """
        with self.get_connection() as conn:
            cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(query, params or ())

            if fetch:
                results = cursor.fetchall()
                cursor.close()
                # Convert RealDictRow → plain dict so callers can mutate freely
                return [dict(row) for row in results]
            else:
                # For INSERT…RETURNING id or similar
                try:
                    row = cursor.fetchone()
                    last_id = row[0] if row else None
                except Exception:
                    last_id = cursor.rowcount
                cursor.close()
                return last_id

    def execute_many(self, query: str, params_list: List[tuple]) -> int:
        """
        Execute a query multiple times with different parameters.

        Args:
            query: SQL query
            params_list: List of parameter tuples

        Returns:
            Number of affected rows
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            affected = cursor.rowcount
            cursor.close()
            return affected


# Global database instance
db = Database()


# ============================================================================
# Data Models
# ============================================================================

class User:
    """User model with CRUD operations"""

    @staticmethod
    def create(name: str, email: str, phone_number: str, password_hash: str,
               role: str = 'guard', is_active: bool = True,
               email_verified: bool = False,
               verification_token: Optional[str] = None,
               verification_token_expiry: Optional[datetime] = None) -> Optional[int]:
        """Create a new user"""
        query = """
            INSERT INTO users (name, email, phone_number, password_hash, role, is_active,
                               email_verified, verification_token, verification_token_expiry)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        try:
            user_id = db.execute_query(
                query,
                (name, email, phone_number, password_hash, role, is_active,
                 email_verified, verification_token, verification_token_expiry),
                fetch=False,
            )
            logger.info(f"[DATABASE] User created: {email} (ID: {user_id})")
            return user_id
        except Error as e:
            logger.error(f"[DATABASE] Failed to create user: {e}")
            return None

    @staticmethod
    def get_by_email(email: str) -> Optional[Dict]:
        """Get user by email"""
        query = "SELECT * FROM users WHERE email = %s"
        results = db.execute_query(query, (email,))
        return results[0] if results else None

    @staticmethod
    def get_by_id(user_id: int) -> Optional[Dict]:
        """Get user by ID"""
        query = "SELECT * FROM users WHERE id = %s"
        results = db.execute_query(query, (user_id,))
        return results[0] if results else None

    @staticmethod
    def update(user_id: int, updates: Dict = None, **kwargs) -> bool:
        """
        Update user fields

        Args:
            user_id: User ID to update
            updates: Dict of fields to update (preferred)
            **kwargs: Alternative way to pass updates
        """
        if updates is None:
            updates = kwargs
        else:
            updates.update(kwargs)

        allowed_fields = [
            'name', 'email', 'phone_number', 'password_hash', 'role', 'is_active',
            'email_verified', 'verification_token', 'verification_token_expiry',
            'password_reset_token', 'password_reset_expiry',
        ]
        updates = {k: v for k, v in updates.items() if k in allowed_fields and v is not None}

        if not updates:
            return False

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        query = f"UPDATE users SET {set_clause} WHERE id = %s"
        values = tuple(updates.values()) + (user_id,)

        try:
            db.execute_query(query, values, fetch=False)
            logger.info(f"[DATABASE] User updated: ID {user_id}")
            return True
        except Error as e:
            logger.error(f"[DATABASE] Failed to update user: {e}")
            return False

    @staticmethod
    def deactivate(user_id: int) -> bool:
        """Deactivate user (soft delete)"""
        return User.update(user_id, is_active=False)

    @staticmethod
    def delete(user_id: int) -> bool:
        """Delete user permanently (hard delete)"""
        query = "DELETE FROM users WHERE id = %s"
        try:
            db.execute_query(query, (user_id,), fetch=False)
            logger.info(f"[DATABASE] User deleted: ID {user_id}")
            return True
        except Error as e:
            logger.error(f"[DATABASE] Failed to delete user: {e}")
            return False

    @staticmethod
    def get_all(role: Optional[str] = None, is_active: Optional[bool] = None,
                exclude_system_admin: bool = False) -> List[Dict]:
        """Get all users with optional filters"""
        query = "SELECT id, name, email, phone_number, role, is_active, created_at, is_system_admin FROM users WHERE 1=1"
        params = []

        if exclude_system_admin:
            query += " AND is_system_admin = FALSE"

        if role:
            query += " AND role = %s"
            params.append(role)

        if is_active is not None:
            query += " AND is_active = %s"
            params.append(is_active)

        query += " ORDER BY created_at DESC"
        return db.execute_query(query, tuple(params))

    @staticmethod
    def get_system_admin() -> Optional[Dict]:
        """Get the system administrator"""
        query = "SELECT id, name, email, phone_number, role, is_active, created_at, password_hash FROM users WHERE is_system_admin = TRUE LIMIT 1"
        results = db.execute_query(query)
        return results[0] if results else None

    @staticmethod
    def is_system_admin(user_id: int) -> bool:
        """Check if user is system administrator"""
        query = "SELECT is_system_admin FROM users WHERE id = %s"
        results = db.execute_query(query, (user_id,))
        return results[0]['is_system_admin'] if results else False

    # ------------------------------------------------------------------
    # Email Verification helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_by_verification_token(token: str) -> Optional[Dict]:
        """Lookup a user by their email-verification token."""
        query = "SELECT * FROM users WHERE verification_token = %s LIMIT 1"
        results = db.execute_query(query, (token,))
        return results[0] if results else None

    @staticmethod
    def set_email_verified(user_id: int) -> bool:
        """Mark account as email-verified and clear the one-time token."""
        query = """
            UPDATE users
            SET email_verified = TRUE,
                verification_token = NULL,
                verification_token_expiry = NULL
            WHERE id = %s
        """
        try:
            db.execute_query(query, (user_id,), fetch=False)
            return True
        except Error as e:
            logger.error(f"[DATABASE] set_email_verified failed: {e}")
            return False

    @staticmethod
    def clear_verification_token(user_id: int) -> bool:
        """Remove an expired verification token."""
        query = """
            UPDATE users
            SET verification_token = NULL, verification_token_expiry = NULL
            WHERE id = %s
        """
        try:
            db.execute_query(query, (user_id,), fetch=False)
            return True
        except Error as e:
            logger.error(f"[DATABASE] clear_verification_token failed: {e}")
            return False

    # ------------------------------------------------------------------
    # Password Reset helpers
    # ------------------------------------------------------------------

    @staticmethod
    def get_by_reset_token(token: str) -> Optional[Dict]:
        """Lookup a user by their password-reset token."""
        query = "SELECT * FROM users WHERE password_reset_token = %s LIMIT 1"
        results = db.execute_query(query, (token,))
        return results[0] if results else None

    @staticmethod
    def set_password_reset_token(user_id: int, token: str, expiry: datetime) -> bool:
        """Store a password-reset token and its expiry."""
        query = """
            UPDATE users
            SET password_reset_token = %s, password_reset_expiry = %s
            WHERE id = %s
        """
        try:
            db.execute_query(query, (token, expiry, user_id), fetch=False)
            return True
        except Error as e:
            logger.error(f"[DATABASE] set_password_reset_token failed: {e}")
            return False

    @staticmethod
    def clear_reset_token(user_id: int) -> bool:
        """Remove a used / expired reset token."""
        query = """
            UPDATE users
            SET password_reset_token = NULL, password_reset_expiry = NULL
            WHERE id = %s
        """
        try:
            db.execute_query(query, (user_id,), fetch=False)
            return True
        except Error as e:
            logger.error(f"[DATABASE] clear_reset_token failed: {e}")
            return False

    @staticmethod
    def update_password_hash(user_id: int, new_hash: str) -> bool:
        """Directly update the password hash (used for password reset flow)."""
        query = "UPDATE users SET password_hash = %s WHERE id = %s"
        try:
            db.execute_query(query, (new_hash, user_id), fetch=False)
            logger.info(f"[DATABASE] Password hash updated for user {user_id}")
            return True
        except Error as e:
            logger.error(f"[DATABASE] update_password_hash failed: {e}")
            return False


class Session:
    """Active session model"""

    @staticmethod
    def create(user_id: int, ip_address: Optional[str] = None,
               user_agent: Optional[str] = None) -> Optional[int]:
        """
        Create new session with role-based enforcement:
        - For same user: logout previous sessions
        - For guards: logout ALL other guards (single guard policy)
        - For admins: allow multiple concurrent sessions
        """
        # First, deactivate any existing active sessions for this user
        Session.logout_user(user_id)

        # Check if user is a guard - enforce single guard policy
        user = User.get_by_id(user_id)
        if user and user['role'] == 'guard':
            # Logout ALL other active guards
            logout_query = """
                UPDATE active_sessions
                SET is_active = FALSE, logout_time = CURRENT_TIMESTAMP
                WHERE user_id IN (
                    SELECT id FROM users WHERE role = 'guard' AND id != %s
                ) AND is_active = TRUE
            """
            try:
                db.execute_query(logout_query, (user_id,), fetch=False)
                logger.info(f"[DATABASE] Logged out other guards for single-guard policy")
            except Error as e:
                logger.warning(f"[DATABASE] Failed to logout other guards: {e}")

        query = """
            INSERT INTO active_sessions (user_id, ip_address, user_agent, is_active)
            VALUES (%s, %s, %s, TRUE)
            RETURNING id
        """
        try:
            session_id = db.execute_query(query, (user_id, ip_address, user_agent), fetch=False)
            logger.info(f"[DATABASE] Session created for user {user_id}")
            return session_id
        except Error as e:
            logger.error(f"[DATABASE] Failed to create session: {e}")
            return None

    @staticmethod
    def get_active_session(user_id: int) -> Optional[Dict]:
        """Get active session for user"""
        query = """
            SELECT * FROM active_sessions
            WHERE user_id = %s AND is_active = TRUE
            ORDER BY login_time DESC LIMIT 1
        """
        results = db.execute_query(query, (user_id,))
        return results[0] if results else None

    @staticmethod
    def logout_user(user_id: int) -> bool:
        """Logout user (deactivate all active sessions)"""
        query = """
            UPDATE active_sessions
            SET is_active = FALSE, logout_time = CURRENT_TIMESTAMP
            WHERE user_id = %s AND is_active = TRUE
        """
        try:
            db.execute_query(query, (user_id,), fetch=False)
            logger.info(f"[DATABASE] User {user_id} logged out")
            return True
        except Error as e:
            logger.error(f"[DATABASE] Failed to logout user: {e}")
            return False

    @staticmethod
    def get_active_guards() -> List[Dict]:
        """Get all currently logged-in guards"""
        query = """
            SELECT u.id, u.name, u.email, u.phone_number, s.login_time
            FROM users u
            INNER JOIN active_sessions s ON u.id = s.user_id
            WHERE u.role = 'guard' AND u.is_active = TRUE AND s.is_active = TRUE
            ORDER BY s.login_time ASC
        """
        return db.execute_query(query)

    @staticmethod
    def get_all_active_sessions() -> List[Dict]:
        """
        Get all active sessions for any logged-in user (admin, guard, or regular user).
        Returns sessions in FIFO order (oldest login first).
        Used for broadcasting alerts to all active users.
        """
        query = """
            SELECT s.id, s.user_id, s.login_time, s.ip_address,
                   u.name, u.email, u.phone_number, u.role
            FROM active_sessions s
            INNER JOIN users u ON s.user_id = u.id
            WHERE s.is_active = TRUE
              AND u.is_active = TRUE
            ORDER BY s.login_time ASC
        """
        return db.execute_query(query)


class Alert:
    """Alert model for drowning detection events"""

    @staticmethod
    def create(track_id: int, alert_type: str, user_id: Optional[int] = None,
               camera_name: str = 'Main Camera', escalated_to_admin: bool = False) -> Optional[int]:
        """Create new alert"""
        query = """
            INSERT INTO alerts (user_id, track_id, alert_type, camera_name, escalated_to_admin)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
        """
        try:
            alert_id = db.execute_query(
                query,
                (user_id, track_id, alert_type.lower(), camera_name, escalated_to_admin),
                fetch=False
            )
            logger.info(f"[DATABASE] Alert created: Track {track_id}, Type {alert_type}")
            return alert_id
        except Error as e:
            logger.error(f"[DATABASE] Failed to create alert: {e}")
            return None

    @staticmethod
    def mark_notification_sent(alert_id: int, method: str) -> bool:
        """Mark alert notification as sent"""
        query = """
            UPDATE alerts
            SET notification_sent = TRUE, notification_method = %s
            WHERE id = %s
        """
        try:
            db.execute_query(query, (method, alert_id), fetch=False)
            return True
        except Error as e:
            logger.error(f"[DATABASE] Failed to update alert notification status: {e}")
            return False

    @staticmethod
    def resolve(alert_id: int, user_id: Optional[int] = None) -> bool:
        """Mark alert as resolved and record the user who did it"""
        query = """
            UPDATE alerts
            SET resolved_at = CURRENT_TIMESTAMP, user_id = %s
            WHERE id = %s
        """
        try:
            db.execute_query(query, (user_id, alert_id), fetch=False)
            logger.info(f"[DATABASE] Alert {alert_id} resolved by user {user_id}")
            return True
        except Error as e:
            logger.error(f"[DATABASE] Failed to resolve alert: {e}")
            return False

    @staticmethod
    def get_recent(limit: int = 100) -> List[Dict]:
        """Get recent alerts"""
        query = """
            SELECT a.*, u.name as user_name, u.email as user_email
            FROM alerts a
            LEFT JOIN users u ON a.user_id = u.id
            ORDER BY a.triggered_at DESC
            LIMIT %s
        """
        return db.execute_query(query, (limit,))

    @staticmethod
    def get_by_user(user_id: int, limit: int = 50) -> List[Dict]:
        """Get alerts for specific user"""
        query = """
            SELECT * FROM alerts
            WHERE user_id = %s
            ORDER BY triggered_at DESC
            LIMIT %s
        """
        return db.execute_query(query, (user_id, limit))

    @staticmethod
    def delete_multiple(alert_ids: List[int]) -> bool:
        """Delete multiple alerts by ID"""
        if not alert_ids:
            return True

        placeholders = ', '.join(['%s'] * len(alert_ids))
        query = f"DELETE FROM alerts WHERE id IN ({placeholders})"
        try:
            db.execute_query(query, tuple(alert_ids), fetch=False)
            logger.info(f"[DATABASE] Deleted {len(alert_ids)} alerts")
            return True
        except Error as e:
            logger.error(f"[DATABASE] Failed to delete alerts: {e}")
            return False


class AuditLog:
    """Audit log for security and compliance"""

    @staticmethod
    def log(action: str, user_id: Optional[int] = None,
            details: Optional[str] = None, ip_address: Optional[str] = None) -> bool:
        """Create audit log entry"""
        query = """
            INSERT INTO audit_logs (user_id, action, details, ip_address)
            VALUES (%s, %s, %s, %s)
        """
        try:
            db.execute_query(query, (user_id, action, details, ip_address), fetch=False)
            return True
        except Error as e:
            logger.error(f"[DATABASE] Failed to create audit log: {e}")
            return False

    @staticmethod
    def get_recent(limit: int = 100) -> List[Dict]:
        """Get recent audit logs"""
        query = """
            SELECT al.*, u.name as user_name, u.email as user_email
            FROM audit_logs al
            LEFT JOIN users u ON al.user_id = u.id
            ORDER BY al.created_at DESC
            LIMIT %s
        """
        return db.execute_query(query, (limit,))
