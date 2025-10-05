"""
FastAPI dependencies for authentication and database access.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Dict, Any

from .auth import get_current_active_user, get_current_admin_user
from ..db.base import get_db

# Security scheme
security = HTTPBearer()


def get_current_user_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current authenticated user."""
    return get_current_active_user(credentials)


def get_current_admin_dependency(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """Dependency to get current admin user."""
    return get_current_admin_user(credentials)


def get_database_dependency() -> Session:
    """Dependency to get database session."""
    return next(get_db())


def require_user_permissions(user: Dict[str, Any] = Depends(get_current_user_dependency)):
    """Dependency that requires user to have basic permissions."""
    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )
    return user


def require_admin_permissions(user: Dict[str, Any] = Depends(get_current_admin_dependency)):
    """Dependency that requires admin permissions."""
    return user


def require_resource_access(resource_user_id: int):
    """Factory for dependency that requires access to specific resource."""
    def check_access(user: Dict[str, Any] = Depends(get_current_user_dependency)):
        if user["role"] != "admin" and user["id"] != resource_user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to access this resource"
            )
        return user
    return check_access


def get_optional_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any] | None:
    """Dependency to get current user if authenticated, None otherwise."""
    try:
        return get_current_active_user(credentials)
    except HTTPException:
        return None


def validate_user_id(user_id: int, current_user: Dict[str, Any] = Depends(get_current_user_dependency)):
    """Validate that user can access the specified user_id."""
    if current_user["role"] != "admin" and current_user["id"] != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this user"
        )
    return user_id


def validate_vehicle_access(vehicle_id: int, db: Session = Depends(get_database_dependency), 
                           current_user: Dict[str, Any] = Depends(get_current_user_dependency)):
    """Validate that user can access the specified vehicle."""
    from ..db.crud import vehicle_crud
    
    vehicle = vehicle_crud.get_by_id(db, vehicle_id)
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vehicle not found"
        )
    
    if current_user["role"] != "admin" and vehicle.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this vehicle"
        )
    
    return vehicle


def validate_policy_access(policy_id: int, db: Session = Depends(get_database_dependency),
                          current_user: Dict[str, Any] = Depends(get_current_user_dependency)):
    """Validate that user can access the specified policy."""
    from ..db.crud import policy_crud
    
    policy = policy_crud.get_by_id(db, policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )
    
    if current_user["role"] != "admin" and policy.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this policy"
        )
    
    return policy


def validate_trip_access(trip_id: int, db: Session = Depends(get_database_dependency),
                        current_user: Dict[str, Any] = Depends(get_current_user_dependency)):
    """Validate that user can access the specified trip."""
    from ..db.crud import trip_crud
    
    trip = trip_crud.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    if current_user["role"] != "admin" and trip.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions to access this trip"
        )
    
    return trip


def get_pagination_params(skip: int = 0, limit: int = 100):
    """Dependency for pagination parameters."""
    if skip < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skip parameter must be non-negative"
        )
    
    if limit < 1 or limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit parameter must be between 1 and 1000"
        )
    
    return {"skip": skip, "limit": limit}


def get_date_range_params(days: int = 30):
    """Dependency for date range parameters."""
    if days < 1 or days > 365:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Days parameter must be between 1 and 365"
        )
    
    return days


def validate_api_version(version: str = "v1"):
    """Dependency to validate API version."""
    if version not in ["v1"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported API version"
        )
    
    return version
