-- ============================================================================
-- Drowning Detection System - Database Schema (India Edition)
-- MySQL 8.0+ compatible | Timezone: IST (Asia/Kolkata)
-- ============================================================================

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS drowning_detection_db 
    CHARACTER SET utf8mb4 
    COLLATE utf8mb4_unicode_ci;

USE drowning_detection_db;

-- ============================================================================
-- Users Table
-- Stores all system users (Admin, Guard, and Regular Users)
-- ============================================================================
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(20) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'guard') NOT NULL DEFAULT 'guard',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_email (email),
    INDEX idx_role (role),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Active Sessions Table
-- Tracks currently logged-in users
-- Only one active session per user at a time (enforced by application logic)
-- ============================================================================
CREATE TABLE IF NOT EXISTS active_sessions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    logout_time TIMESTAMP NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    ip_address VARCHAR(45) NULL,
    user_agent TEXT NULL,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_active (user_id, is_active),
    INDEX idx_is_active (is_active)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Alerts Table
-- Records all drowning alerts triggered by the system
-- ============================================================================
CREATE TABLE IF NOT EXISTS alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,                           -- FK to user who was logged in
    track_id INT NOT NULL,                      -- Person tracking ID from detection system
    alert_type ENUM('warning', 'danger') NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP NULL,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_method VARCHAR(50) NULL,        -- email, sms, whatsapp
    escalated_to_admin BOOLEAN DEFAULT FALSE,    -- TRUE if no guard was logged in
    camera_name VARCHAR(255) DEFAULT 'Main Camera',
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_triggered_at (triggered_at),
    INDEX idx_alert_type (alert_type),
    INDEX idx_track_id (track_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Audit Logs Table
-- Records authentication and system events for security auditing
-- ============================================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NULL,
    action VARCHAR(100) NOT NULL,               -- LOGIN, LOGOUT, ALERT_SENT, USER_CREATED, etc.
    details TEXT NULL,
    ip_address VARCHAR(45) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_action (action),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- System Configuration Table
-- Stores system-level settings manageable by Admin
-- ============================================================================
CREATE TABLE IF NOT EXISTS system_config (
    id INT AUTO_INCREMENT PRIMARY KEY,
    config_key VARCHAR(100) NOT NULL UNIQUE,
    config_value TEXT NOT NULL,
    description TEXT NULL,
    updated_by INT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (updated_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_config_key (config_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================================================
-- Initial Data
-- Create default admin user (password: admin123)
-- IMPORTANT: Change this password immediately in production!
-- ============================================================================

-- Default admin user (password: admin123)
-- Password hash generated using bcrypt with cost factor 12
INSERT INTO users (name, email, phone_number, password_hash, role, is_active) 
VALUES (
    'System Administrator',
    'admin@dds.local',
    '+1234567890',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqMvFj9nPu',  -- admin123
    'admin',
    TRUE
) ON DUPLICATE KEY UPDATE id=id;

-- Default system configuration
INSERT INTO system_config (config_key, config_value, description) VALUES
    ('site_name', 'Drowning Detection System', 'System display name'),
    ('max_concurrent_guards', '5', 'Maximum number of guards that can be logged in simultaneously'),
    ('alert_retention_days', '90', 'Number of days to keep alert records'),
    ('session_timeout_minutes', '480', 'Session timeout in minutes (8 hours)')
ON DUPLICATE KEY UPDATE config_key=config_key;

-- ============================================================================
-- Stored Procedures
-- ============================================================================

-- Procedure to get currently active guard users
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS GetActiveGuards()
BEGIN
    SELECT u.id, u.name, u.email, u.phone_number, s.login_time
    FROM users u
    INNER JOIN active_sessions s ON u.id = s.user_id
    WHERE u.role = 'guard' 
      AND u.is_active = TRUE 
      AND s.is_active = TRUE
    ORDER BY s.login_time ASC;
END //
DELIMITER ;

-- Procedure to log out all sessions for a user
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS LogoutUser(IN p_user_id INT)
BEGIN
    UPDATE active_sessions 
    SET is_active = FALSE, logout_time = CURRENT_TIMESTAMP
    WHERE user_id = p_user_id AND is_active = TRUE;
END //
DELIMITER ;

-- Procedure to clean up old sessions (older than 30 days)
DELIMITER //
CREATE PROCEDURE IF NOT EXISTS CleanupOldSessions()
BEGIN
    DELETE FROM active_sessions 
    WHERE logout_time < DATE_SUB(NOW(), INTERVAL 30 DAY);
END //
DELIMITER ;

-- ============================================================================
-- Views
-- ============================================================================

-- View for active users with session info
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

-- View for alert summary
CREATE OR REPLACE VIEW v_alert_summary AS
SELECT 
    a.id,
    a.track_id,
    a.alert_type,
    a.triggered_at,
    a.resolved_at,
    u.name AS assigned_user,
    u.role AS user_role,
    a.escalated_to_admin,
    a.notification_sent
FROM alerts a
LEFT JOIN users u ON a.user_id = u.id
ORDER BY a.triggered_at DESC;

-- ============================================================================
-- Grants (adjust as needed for your MySQL user)
-- ============================================================================
-- GRANT ALL PRIVILEGES ON drowning_detection_db.* TO 'dds_user'@'localhost';
-- FLUSH PRIVILEGES;

-- ============================================================================
-- End of Schema
-- ============================================================================
