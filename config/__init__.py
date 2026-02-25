"""
Configuration module for Drowning Detection System
Re-exports configuration from core.config for backward compatibility
"""

from core.config import (
    # Database Configuration
    DB_HOST,
    DB_PORT,
    DB_USER,
    DB_PASSWORD,
    DB_NAME,
    DB_POOL_SIZE,
    
    # Server Configuration
    SERVER_HOST,
    SERVER_PORT,
)

__all__ = [
    'DB_HOST',
    'DB_PORT',
    'DB_USER',
    'DB_PASSWORD',
    'DB_NAME',
    'DB_POOL_SIZE',
    'SERVER_HOST',
    'SERVER_PORT',
]
