"""
JWT token handling and security utilities.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
import os
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .hashing import verify_password
from ..db.crud import user_crud
from ..db.schemas import TokenData

# JWT configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-key-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

# Security scheme
security = HTTPBearer()


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token."""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify JWT token and return token data."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = TokenData(email=email)
        return token_data
    
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def authenticate_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """Authenticate user with email and password."""
    from ..db.base import SessionLocal
    
    db = SessionLocal()
    try:
        user = user_crud.get_by_email(db, email)
        if not user:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active
        }
    finally:
        db.close()


def get_current_user(credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
    """Get current user from JWT token."""
    token = credentials.credentials
    token_data = verify_token(token)
    
    from ..db.base import SessionLocal
    
    db = SessionLocal()
    try:
        user = user_crud.get_by_email(db, token_data.email)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role,
            "is_active": user.is_active
        }
    finally:
        db.close()


def get_current_active_user(credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
    """Get current active user from JWT token."""
    user = get_current_user(credentials)
    
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


def get_current_admin_user(credentials: HTTPAuthorizationCredentials) -> Dict[str, Any]:
    """Get current admin user from JWT token."""
    user = get_current_active_user(credentials)
    
    if user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return user


def check_user_permissions(user: Dict[str, Any], resource_user_id: int) -> bool:
    """Check if user has permission to access resource."""
    return user["role"] == "admin" or user["id"] == resource_user_id


def require_permissions(user: Dict[str, Any], resource_user_id: int):
    """Require user to have permissions for resource."""
    if not check_user_permissions(user, resource_user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
