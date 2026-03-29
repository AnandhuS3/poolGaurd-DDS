-- ============================================================================
-- Drowning Detection System - Database Schema (PostgreSQL Edition)
-- PostgreSQL 14+ compatible | Timezone: IST (Asia/Kolkata)
-- ============================================================================

-- ============================================================================
-- Custom ENUM Types
-- ============================================================================
DO $$ BEGIN
    CREATE TYPE user_role AS ENUM ('admin', 'guard');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE alert_type_enum AS ENUM ('warning', 'danger', 'struggling');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

DO $$ BEGIN
    CREATE TYPE camera_status_enum AS ENUM ('active', 'inactive', 'maintenance');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- ============================================================================
-- Users Table
-- Stores all system users (Admin, Guard)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id                        SERIAL PRIMARY KEY,
    name                      VARCHAR(255) NOT NULL,
    email                     VARCHAR(255) NOT NULL UNIQUE,
    phone_number              VARCHAR(20)  NOT NULL DEFAULT '',
    password_hash             VARCHAR(255) NOT NULL,
    role                      user_role    NOT NULL DEFAULT 'guard',
    is_active                 BOOLEAN      NOT NULL DEFAULT TRUE,
    is_system_admin           BOOLEAN      NOT NULL DEFAULT FALSE,
    -- Email verification
    email_verified            BOOLEAN      NOT NULL DEFAULT FALSE,
    verification_token        VARCHAR(255) NULL,
    verification_token_expiry TIMESTAMP    NULL,
    -- Password reset
    password_reset_token      VARCHAR(255) NULL,
    password_reset_expiry     TIMESTAMP    NULL,
    -- Mobile push notifications (FCM device token)
    fcm_token                 VARCHAR(255) NULL,
    created_at                TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email              ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role               ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_is_active          ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_system_admin       ON users(is_system_admin);
CREATE INDEX IF NOT EXISTS idx_users_verification_token ON users(verification_token);
CREATE INDEX IF NOT EXISTS idx_users_reset_token        ON users(password_reset_token);

-- ============================================================================
-- Active Sessions Table
-- Tracks currently logged-in users
-- ============================================================================
CREATE TABLE IF NOT EXISTS active_sessions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER  NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    login_time  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL,
    is_active   BOOLEAN   NOT NULL DEFAULT TRUE,
    ip_address  VARCHAR(45) NULL,
    user_agent  TEXT NULL
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_active ON active_sessions(user_id, is_active);
CREATE INDEX IF NOT EXISTS idx_sessions_is_active   ON active_sessions(is_active);

-- ============================================================================
-- Alerts Table
-- Records all drowning alerts triggered by the system
-- ============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id                  SERIAL PRIMARY KEY,
    user_id             INTEGER          NULL REFERENCES users(id) ON DELETE SET NULL,
    track_id            INTEGER          NOT NULL,
    alert_type          alert_type_enum  NOT NULL,
    triggered_at        TIMESTAMP        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at         TIMESTAMP        NULL,
    notification_sent   BOOLEAN          NOT NULL DEFAULT FALSE,
    notification_method VARCHAR(50)      NULL,
    escalated_to_admin  BOOLEAN          NOT NULL DEFAULT FALSE,
    camera_name         VARCHAR(255)     NOT NULL DEFAULT 'Main Camera'
);

CREATE INDEX IF NOT EXISTS idx_alerts_user_id     ON alerts(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_triggered   ON alerts(triggered_at);
CREATE INDEX IF NOT EXISTS idx_alerts_type        ON alerts(alert_type);
CREATE INDEX IF NOT EXISTS idx_alerts_track_id    ON alerts(track_id);

-- ============================================================================
-- Audit Logs Table
-- Records authentication and system events for security auditing
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id         SERIAL PRIMARY KEY,
    user_id    INTEGER      NULL REFERENCES users(id) ON DELETE SET NULL,
    action     VARCHAR(100) NOT NULL,
    details    TEXT         NULL,
    ip_address VARCHAR(45)  NULL,
    created_at TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_user_id   ON audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_audit_action    ON audit_logs(action);
CREATE INDEX IF NOT EXISTS idx_audit_created   ON audit_logs(created_at);

-- ============================================================================
-- System Configuration Table
-- Stores system-level settings manageable by Admin
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_config (
    id           SERIAL PRIMARY KEY,
    config_key   VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT         NOT NULL,
    description  TEXT         NULL,
    updated_by   INTEGER      NULL REFERENCES users(id) ON DELETE SET NULL,
    updated_at   TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sysconfig_key ON system_config(config_key);

-- ============================================================================
-- Cameras Table
-- Registry of CCTV cameras integrated with the PoolGuard system
-- ============================================================================
CREATE TABLE IF NOT EXISTS cameras (
    id                SERIAL PRIMARY KEY,
    camera_name       VARCHAR(255)        NOT NULL,
    pool_location     VARCHAR(255)        NOT NULL DEFAULT 'Main Pool',
    rtsp_url          VARCHAR(1024)       NOT NULL,
    hls_url           VARCHAR(1024)       NULL,
    status            camera_status_enum  NOT NULL DEFAULT 'active',
    assigned_guard_id INTEGER             NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at        TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cameras_status ON cameras(status);
CREATE INDEX IF NOT EXISTS idx_cameras_guard  ON cameras(assigned_guard_id);

-- ============================================================================
-- Auto-update updated_at trigger
-- ============================================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_updated_at   ON users;
CREATE TRIGGER trg_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_cameras_updated_at ON cameras;
CREATE TRIGGER trg_cameras_updated_at
    BEFORE UPDATE ON cameras
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS trg_sysconfig_updated_at ON system_config;
CREATE TRIGGER trg_sysconfig_updated_at
    BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================================
-- Initial Data
-- ============================================================================

-- Default admin user (password: admin123)
-- Password hash generated using bcrypt with cost factor 12
INSERT INTO users (name, email, phone_number, password_hash, role, is_active, is_system_admin, email_verified)
VALUES (
    'System Administrator',
    'creagoouon@gmail.com',
    '+1234567890',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqMvFj9nPu',
    'admin',
    TRUE,
    TRUE,
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Default system configuration
INSERT INTO system_config (config_key, config_value, description) VALUES
    ('site_name',               'PoolGuard Drowning Detection System',  'System display name'),
    ('max_concurrent_guards',   '5',   'Maximum guards logged in simultaneously'),
    ('alert_retention_days',    '90',  'Days to keep alert records'),
    ('session_timeout_minutes', '480', 'Session timeout in minutes (8 hours)')
ON CONFLICT (config_key) DO NOTHING;

-- ============================================================================
-- Views
-- ============================================================================

CREATE OR REPLACE VIEW v_active_users AS
SELECT
    u.id,
    u.name,
    u.email,
    u.phone_number,
    u.role,
    s.login_time,
    s.ip_address
FROM users u
INNER JOIN active_sessions s ON u.id = s.user_id
WHERE u.is_active = TRUE AND s.is_active = TRUE;

CREATE OR REPLACE VIEW v_alert_summary AS
SELECT
    a.id,
    a.track_id,
    a.alert_type,
    a.triggered_at,
    a.resolved_at,
    u.name  AS assigned_user,
    u.role  AS user_role,
    a.escalated_to_admin,
    a.notification_sent
FROM alerts a
LEFT JOIN users u ON a.user_id = u.id
ORDER BY a.triggered_at DESC;

-- ============================================================================
-- End of Schema
-- ============================================================================
