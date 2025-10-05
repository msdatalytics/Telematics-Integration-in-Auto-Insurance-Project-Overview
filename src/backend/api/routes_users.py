"""
User management API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.dependencies import (
    get_current_user_dependency, get_current_admin_dependency,
    get_database_dependency, validate_user_id
)
from ..core.auth import create_access_token
from ..db import crud, schemas
from ..db.schemas import UserCreate, UserLogin, Token, User, UserUpdate

router = APIRouter()


@router.post("/register", response_model=schemas.User)
async def register_user(
    user_data: UserCreate,
    db: Session = Depends(get_database_dependency)
):
    """Register a new user."""
    # Check if user already exists
    existing_user = crud.user_crud.get_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    from ..core.hashing import get_password_hash
    hashed_password = get_password_hash(user_data.password)
    
    user = crud.user_crud.create(db, user_data, hashed_password)
    return user


@router.post("/login", response_model=Token)
async def login_user(
    user_credentials: UserLogin,
    db: Session = Depends(get_database_dependency)
):
    """Login user and return access token."""
    from ..core.auth import authenticate_user
    
    user = authenticate_user(user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(data={"sub": user["email"]})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.User)
async def get_current_user_profile(
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get current user profile."""
    user = crud.user_crud.get_by_id(db, current_user["id"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/me", response_model=schemas.User)
async def update_current_user_profile(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Update current user profile."""
    user = crud.user_crud.update(db, current_user["id"], user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.get("/me/vehicles", response_model=List[schemas.Vehicle])
async def get_user_vehicles(
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get current user's vehicles."""
    vehicles = crud.vehicle_crud.get_by_user(db, current_user["id"])
    return vehicles


@router.get("/me/policies", response_model=List[schemas.Policy])
async def get_user_policies(
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get current user's policies."""
    policies = crud.policy_crud.get_by_user(db, current_user["id"])
    return policies


@router.get("/me/trips", response_model=List[schemas.Trip])
async def get_user_trips(
    skip: int = 0,
    limit: int = 100,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get current user's trips."""
    trips = crud.trip_crud.get_by_user(db, current_user["id"], skip, limit)
    return trips


@router.get("/me/dashboard", response_model=schemas.DashboardStats)
async def get_user_dashboard(
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get user dashboard statistics."""
    # Get user's latest risk score
    latest_score = crud.risk_score_crud.get_latest_by_user(db, current_user["id"])
    
    # Get user's active policies
    policies = crud.policy_crud.get_active_by_user(db, current_user["id"])
    
    # Get latest premium adjustment
    current_premium = 0
    premium_delta = 0
    premium_delta_pct = 0
    
    if policies:
        latest_policy = policies[0]  # Assuming one active policy
        current_premium = latest_policy.base_premium
        
        latest_adjustment = crud.premium_adjustment_crud.get_latest_by_policy(db, latest_policy.id)
        if latest_adjustment:
            premium_delta = latest_adjustment.delta_amount
            premium_delta_pct = latest_adjustment.delta_pct
    
    # Get score trend
    score_trend = crud.risk_score_crud.get_score_trend(db, current_user["id"])
    
    # Get user stats
    user_stats = crud.trip_crud.get_user_stats(db, current_user["id"])
    
    return schemas.DashboardStats(
        current_premium=current_premium,
        premium_delta=premium_delta,
        premium_delta_pct=premium_delta_pct,
        current_band=latest_score.band if latest_score else "C",
        current_score=latest_score.score_value if latest_score else 70.0,
        score_trend=score_trend,
        total_trips=user_stats["total_trips"],
        total_distance_km=user_stats["total_distance_km"],
        avg_score=latest_score.score_value if latest_score else 70.0
    )


# Admin routes
@router.get("/admin/users", response_model=List[schemas.User])
async def list_all_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """List all users (admin only)."""
    users = crud.user_crud.list_users(db, skip, limit)
    return users


@router.get("/admin/users/{user_id}", response_model=schemas.User)
async def get_user_by_id(
    user_id: int = Depends(validate_user_id),
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get user by ID (admin only)."""
    user = crud.user_crud.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user


@router.put("/admin/users/{user_id}", response_model=schemas.User)
async def update_user_by_id(
    user_id: int,
    user_update: UserUpdate,
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Update user by ID (admin only)."""
    user = crud.user_crud.update(db, user_id, user_update)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return user
