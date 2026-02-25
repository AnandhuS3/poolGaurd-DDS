"""
Authentication system for Drowning Detection System
Implements JWT-based authentication, password hashing, and role-based access control
"""
import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Tuple
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
import logging

from core.database import db, User, Session, AuditLog

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET_KEY = "your-secret-key-change-in-production-use-env-variable"  # TODO: Move to environment variable
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 8  # Access token expires in 8 hours

# Security
security = HTTPBearer()


# ============================================================================
# Request/Response Models
# ============================================================================

class LoginRequest(BaseModel):
    """Login request model"""
    email: str  # Use plain string for login (less strict validation)
    password: str


class RegisterRequest(BaseModel):
    """User registration request"""
    name: str
    email: EmailStr
    phone_number: str
    password: str
    role: str = 'guard'  # Default role for public registration
    
    @validator('role')
    def validate_role(cls, v):
        if v not in ['admin', 'guard']:
            raise ValueError('Role must be either admin or guard')
        return v
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        return v.strip()
    
    @validator('phone_number')
    def validate_phone(cls, v):
        """
        Validate international phone number in E.164 format
        Expected format: +[country_code][number]
        Example: +91 9876543210, +1 5551234567
        """
        from core.region_utils import validate_phone_number
        
        # Clean the phone number
        clean_phone = v.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        
        # Must start with +
        if not clean_phone.startswith('+'):
            raise ValueError('Phone number must include country code (e.g., +91 for India, +1 for USA)')
        
        # Validate E.164 format
        if not validate_phone_number(clean_phone):
            raise ValueError('Invalid phone number format. Use international format: +[country code][number]')
        
        return v


class UpdateUserRequest(BaseModel):
    """Update user request"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    
    @validator('role')
    def validate_role(cls, v):
        if v is not None and v not in ['admin', 'guard']:
            raise ValueError('Role must be either admin or guard')
        return v


class AuthResponse(BaseModel):
    """Authentication response"""
    access_token: str
    token_type: str = "bearer"
    user: Dict


class UserInfo(BaseModel):
    """User information (safe, no sensitive data)"""
    id: int
    name: str
    email: str
    phone_number: str
    role: str
    is_active: bool


# ============================================================================
# Password Hashing
# ============================================================================

class PasswordHasher:
    """Password hashing using bcrypt"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash password using bcrypt
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """
        Verify password against hash
        
        Args:
            password: Plain text password
            hashed: Hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        except Exception as e:
            logger.error(f"[AUTH] Password verification error: {e}")
            return False


# ============================================================================
# JWT Token Management
# ============================================================================

class TokenManager:
    """JWT token creation and validation"""
    
    @staticmethod
    def create_access_token(user_id: int, email: str, role: str) -> str:
        """
        Create JWT access token
        
        Args:
            user_id: User ID
            email: User email
            role: User role (admin/guard)
            
        Returns:
            JWT token string
        """
        expiration = datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS)
        
        payload = {
            "sub": str(user_id),  # Subject (user ID)
            "email": email,
            "role": role,
            "exp": expiration,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return token
    
    @staticmethod
    def decode_token(token: str) -> Dict:
        """
        Decode and validate JWT token
        
        Args:
            token: JWT token string
            
        Returns:
            Token payload
            
        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


# ============================================================================
# Authentication Service
# ============================================================================

class AuthService:
    """Main authentication service"""
    
    @staticmethod
    def login(email: str, password: str, ip_address: Optional[str] = None,
              user_agent: Optional[str] = None) -> Tuple[str, Dict]:
        """
        Authenticate user and create session
        
        Args:
            email: User email
            password: User password
            ip_address: Client IP address
            user_agent: Client user agent
            
        Returns:
            Tuple of (access_token, user_dict)
            
        Raises:
            HTTPException: If authentication fails
        """
        # Get user by email
        user = User.get_by_email(email)
        
        if not user:
            AuditLog.log("LOGIN_FAILED", None, f"Email not found: {email}", ip_address)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user['is_active']:
            AuditLog.log("LOGIN_FAILED", user['id'], "Inactive account", ip_address)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        # Verify password
        if not PasswordHasher.verify_password(password, user['password_hash']):
            AuditLog.log("LOGIN_FAILED", user['id'], "Invalid password", ip_address)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Create session
        session_id = Session.create(user['id'], ip_address, user_agent)
        if not session_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create session"
            )
        
        # Create access token
        access_token = TokenManager.create_access_token(
            user['id'], 
            user['email'], 
            user['role']
        )
        
        # Log successful login
        AuditLog.log("LOGIN_SUCCESS", user['id'], f"Role: {user['role']}", ip_address)
        
        # Return token and safe user info
        user_info = {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "phone_number": user['phone_number'],
            "role": user['role'],
            "is_active": user['is_active']
        }
        
        logger.info(f"[AUTH] User logged in: {email} (Role: {user['role']})")
        return access_token, user_info
    
    @staticmethod
    def logout(user_id: int, ip_address: Optional[str] = None) -> bool:
        """
        Logout user and deactivate session
        
        Args:
            user_id: User ID
            ip_address: Client IP address
            
        Returns:
            True if successful
        """
        success = Session.logout_user(user_id)
        if success:
            AuditLog.log("LOGOUT", user_id, "User logged out", ip_address)
            logger.info(f"[AUTH] User logged out: ID {user_id}")
        return success
    
    @staticmethod
    def register_user(name: str, email: str, phone_number: str, password: str,
                      role: str = 'guard', created_by: Optional[int] = None) -> Dict:
        """
        Register new user (Admin only)
        
        Args:
            name: User name
            email: User email
            phone_number: User phone number
            password: User password (plain text, will be hashed)
            role: User role (admin/guard)
            created_by: Admin user ID who created this user
            
        Returns:
            Created user info
            
        Raises:
            HTTPException: If user creation fails
        """
        # Check if email already exists
        existing_user = User.get_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        password_hash = PasswordHasher.hash_password(password)
        
        # Create user
        user_id = User.create(name, email, phone_number, password_hash, role)
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create user"
            )
        
        # Log user creation
        AuditLog.log("USER_CREATED", created_by, f"Created user: {email} (Role: {role})")
        
        # Get created user
        user = User.get_by_id(user_id)
        
        return {
            "id": user['id'],
            "name": user['name'],
            "email": user['email'],
            "phone_number": user['phone_number'],
            "role": user['role'],
            "is_active": user['is_active']
        }
    
    @staticmethod
    def update_user(user_id: int, update_data: UpdateUserRequest) -> Dict:
        """
        Update user profile
        
        Args:
            user_id: User ID to update
            update_data: UpdateUserRequest with fields to update
            
        Returns:
            Updated user info
            
        Raises:
            HTTPException: If update fails
        """
        user = User.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Check email uniqueness if being updated
        if update_data.email and update_data.email != user['email']:
            existing = User.get_by_email(update_data.email)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )
        
        # Update user
        success = User.update(user_id, update_data.dict(exclude_unset=True))
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user"
            )
        
        # Log update
        AuditLog.log("USER_UPDATED", user_id, f"Profile updated")
        
        # Return updated user
        updated_user = User.get_by_id(user_id)
        return {
            "id": updated_user['id'],
            "name": updated_user['name'],
            "email": updated_user['email'],
            "phone_number": updated_user['phone_number'],
            "role": updated_user['role'],
            "is_active": updated_user['is_active']
        }
    
    @staticmethod
    def change_password(user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password
        
        Args:
            user_id: User ID
            old_password: Current password
            new_password: New password
            
        Returns:
            True if successful
            
        Raises:
            HTTPException: If password change fails
        """
        user = User.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify old password
        if not PasswordHasher.verify_password(old_password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Current password is incorrect"
            )
        
        # Validate new password
        if len(new_password) < 8:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        
        # Hash and update password
        new_password_hash = PasswordHasher.hash_password(new_password)
        success = User.update(user_id, {'password_hash': new_password_hash})
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to change password"
            )
        
        # Log password change
        AuditLog.log("PASSWORD_CHANGED", user_id, "Password changed successfully")
        logger.info(f"[AUTH] Password changed for user ID {user_id}")
        
        return True


# ============================================================================
# Authentication Dependencies (for FastAPI routes)
# ============================================================================

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict:
    """
    Dependency to get current authenticated user from JWT token
    
    Usage in route:
        @app.get("/protected")
        async def protected_route(current_user: Dict = Depends(get_current_user)):
            return {"user": current_user}
    """
    token = credentials.credentials
    payload = TokenManager.decode_token(token)
    
    # Get user from database
    user_id = int(payload['sub'])
    user = User.get_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Check if user has active session
    active_session = Session.get_active_session(user_id)
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session. Please log in again."
        )
    
    return {
        "id": user['id'],
        "name": user['name'],
        "email": user['email'],
        "phone_number": user['phone_number'],
        "role": user['role'],
        "is_active": user['is_active']
    }


async def require_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency to require admin role
    
    Usage in route:
        @app.post("/admin/users")
        async def create_user(admin: Dict = Depends(require_admin)):
            # Only admins can access this route
    """
    if current_user['role'] != 'admin':
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


async def require_guard_or_admin(current_user: Dict = Depends(get_current_user)) -> Dict:
    """
    Dependency to require guard or admin role
    
    Usage in route:
        @app.get("/monitoring")
        async def monitoring(user: Dict = Depends(require_guard_or_admin)):
            # Both guards and admins can access
    """
    if current_user['role'] not in ['guard', 'admin']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Guard or Admin access required"
        )
    return current_user


# ============================================================================
# WebSocket Authentication
# ============================================================================

async def authenticate_websocket(token: str) -> Dict:
    """
    Authenticate WebSocket connection using JWT token
    
    Args:
        token: JWT token
        
    Returns:
        User dict
        
    Raises:
        HTTPException: If authentication fails
    """
    payload = TokenManager.decode_token(token)
    user_id = int(payload['sub'])
    user = User.get_by_id(user_id)
    
    if not user or not user['is_active']:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )
    
    active_session = Session.get_active_session(user_id)
    if not active_session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No active session"
        )
    
    return {
        "id": user['id'],
        "name": user['name'],
        "email": user['email'],
        "phone_number": user['phone_number'],
        "role": user['role']
    }


# ============================================================================
# Utility Functions
# ============================================================================

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def get_user_agent(request: Request) -> str:
    """Extract user agent from request"""
    return request.headers.get("User-Agent", "unknown")
