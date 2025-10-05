"""
Risk scoring API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.dependencies import (
    get_current_user_dependency, get_current_admin_dependency,
    get_database_dependency, validate_user_id
)
from ..db import crud, schemas
from ..db.schemas import UserScoreResponse, TripScoreResponse, RiskScore

router = APIRouter()


@router.get("/user/{user_id}/latest", response_model=schemas.UserScoreResponse)
async def get_user_latest_score(
    user_id: int = Depends(validate_user_id),
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get latest risk score for a user."""
    # Get latest daily score
    latest_score = crud.risk_score_crud.get_latest_by_user(db, user_id, "daily")
    
    if not latest_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk score found for user"
        )
    
    return schemas.UserScoreResponse(
        user_id=user_id,
        score=latest_score.score_value,
        band=latest_score.band,
        expected_loss=latest_score.expected_loss,
        explanations=latest_score.explanations or [],
        computed_at=latest_score.computed_at
    )


@router.get("/trip/{trip_id}", response_model=schemas.TripScoreResponse)
async def get_trip_score(
    trip_id: int,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get risk score for a specific trip."""
    # Validate trip access
    trip = crud.trip_crud.get_by_id(db, trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Trip not found"
        )
    
    if trip.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this trip"
        )
    
    # Get trip score
    trip_score = crud.risk_score_crud.get_by_trip(db, trip_id)
    
    if not trip_score:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No risk score found for trip"
        )
    
    return schemas.TripScoreResponse(
        trip_id=trip_id,
        score=trip_score.score_value,
        band=trip_score.band,
        expected_loss=trip_score.expected_loss,
        explanations=trip_score.explanations or [],
        computed_at=trip_score.computed_at
    )


@router.get("/user/{user_id}/history", response_model=List[schemas.RiskScore])
async def get_user_score_history(
    user_id: int = Depends(validate_user_id),
    days: int = 30,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get risk score history for a user."""
    scores = crud.risk_score_crud.get_user_score_history(db, user_id, days)
    return scores


@router.get("/user/{user_id}/trend")
async def get_user_score_trend(
    user_id: int = Depends(validate_user_id),
    days: int = 30,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get score trend data for dashboard."""
    trend_data = crud.risk_score_crud.get_score_trend(db, user_id, days)
    return {"user_id": user_id, "trend": trend_data}


@router.post("/compute/daily")
async def compute_daily_scores(
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Compute daily risk scores for all users (admin only)."""
    try:
        from ..ml.score_service import ScoreService
        
        # Initialize score service
        score_service = ScoreService()
        await score_service.initialize()
        
        # Get all active users
        users = crud.user_crud.list_users(db, skip=0, limit=1000)
        
        computed_count = 0
        for user in users:
            try:
                # Compute daily score for user
                await score_service.compute_daily_score(db, user.id)
                computed_count += 1
            except Exception as e:
                print(f"Error computing score for user {user.id}: {e}")
                continue
        
        return {
            "message": f"Computed daily scores for {computed_count} users",
            "total_users": len(users),
            "successful": computed_count
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing daily scores: {str(e)}"
        )


@router.post("/compute/trip/{trip_id}")
async def compute_trip_score(
    trip_id: int,
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Compute risk score for a specific trip (admin only)."""
    try:
        from ..ml.score_service import ScoreService
        
        # Validate trip exists
        trip = crud.trip_crud.get_by_id(db, trip_id)
        if not trip:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Trip not found"
            )
        
        # Initialize score service
        score_service = ScoreService()
        await score_service.initialize()
        
        # Compute trip score
        score = await score_service.compute_trip_score(db, trip_id)
        
        return {
            "message": "Trip score computed successfully",
            "trip_id": trip_id,
            "score": score.score_value,
            "band": score.band
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error computing trip score: {str(e)}"
        )


@router.get("/admin/scores", response_model=List[schemas.RiskScore])
async def list_all_scores(
    skip: int = 0,
    limit: int = 100,
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """List all risk scores (admin only)."""
    # This would need to be implemented in CRUD
    # For now, return empty list
    return []


@router.get("/admin/metrics")
async def get_scoring_metrics(
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get scoring system metrics (admin only)."""
    try:
        from ..ml.score_service import ScoreService
        
        score_service = ScoreService()
        await score_service.initialize()
        
        metrics = await score_service.get_metrics()
        
        return {
            "model_version": metrics.get("model_version", "unknown"),
            "last_training_date": metrics.get("last_training_date"),
            "total_scores_computed": metrics.get("total_scores", 0),
            "average_score": metrics.get("average_score", 0),
            "score_distribution": metrics.get("score_distribution", {}),
            "model_performance": metrics.get("model_performance", {})
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting scoring metrics: {str(e)}"
        )
