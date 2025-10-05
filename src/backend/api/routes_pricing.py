"""
Dynamic pricing API routes.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from ..core.dependencies import (
    get_current_user_dependency, get_current_admin_dependency,
    get_database_dependency, validate_policy_access
)
from ..db import crud, schemas
from ..db.schemas import PricingQuoteRequest, PricingQuoteResponse, PremiumAdjustment

router = APIRouter()


@router.post("/quote", response_model=schemas.PricingQuoteResponse)
async def get_pricing_quote(
    quote_request: PricingQuoteRequest,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get dynamic pricing quote based on risk score."""
    try:
        from ..pricing.engine import PricingEngine
        
        # Initialize pricing engine
        pricing_engine = PricingEngine()
        
        # Get base premium
        if quote_request.policy_id:
            policy = crud.policy_crud.get_by_id(db, quote_request.policy_id)
            if not policy:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Policy not found"
                )
            
            # Check policy access
            if policy.user_id != current_user["id"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this policy"
                )
            
            base_premium = policy.base_premium
        else:
            if not quote_request.base_premium:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either policy_id or base_premium must be provided"
                )
            base_premium = quote_request.base_premium
        
        # Calculate pricing adjustment
        quote = pricing_engine.calculate_quote(
            score=quote_request.score,
            base_premium=base_premium,
            policy_id=quote_request.policy_id
        )
        
        return quote
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating pricing quote: {str(e)}"
        )


@router.get("/policy/{policy_id}/adjustments", response_model=List[schemas.PremiumAdjustment])
async def get_policy_adjustments(
    policy_id: int,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get premium adjustments for a policy."""
    # Validate policy access
    policy = crud.policy_crud.get_by_id(db, policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )
    
    if policy.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this policy"
        )
    
    adjustments = crud.premium_adjustment_crud.get_by_policy(db, policy_id)
    return adjustments


@router.get("/policy/{policy_id}/current-premium")
async def get_current_premium(
    policy_id: int,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get current premium for a policy."""
    # Validate policy access
    policy = crud.policy_crud.get_by_id(db, policy_id)
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Policy not found"
        )
    
    if policy.user_id != current_user["id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this policy"
        )
    
    # Get latest adjustment
    latest_adjustment = crud.premium_adjustment_crud.get_latest_by_policy(db, policy_id)
    
    if latest_adjustment:
        current_premium = latest_adjustment.new_premium
        delta_pct = latest_adjustment.delta_pct
    else:
        current_premium = policy.base_premium
        delta_pct = 0.0
    
    return {
        "policy_id": policy_id,
        "base_premium": policy.base_premium,
        "current_premium": current_premium,
        "delta_pct": delta_pct,
        "last_adjustment_date": latest_adjustment.created_at if latest_adjustment else None
    }


@router.post("/apply-adjustment")
async def apply_premium_adjustment(
    policy_id: int,
    score: float,
    current_user: dict = Depends(get_current_user_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Apply premium adjustment based on risk score."""
    try:
        from ..pricing.engine import PricingEngine
        
        # Validate policy access
        policy = crud.policy_crud.get_by_id(db, policy_id)
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Policy not found"
            )
        
        if policy.user_id != current_user["id"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this policy"
            )
        
        # Initialize pricing engine
        pricing_engine = PricingEngine()
        
        # Calculate adjustment
        quote = pricing_engine.calculate_quote(
            score=score,
            base_premium=policy.base_premium,
            policy_id=policy_id
        )
        
        # Create premium adjustment record
        adjustment_data = {
            "policy_id": policy_id,
            "period_start": policy.start_date,
            "period_end": policy.end_date,
            "delta_pct": quote.delta_pct,
            "delta_amount": quote.delta_amount,
            "new_premium": quote.new_premium,
            "reason": quote.rationale,
            "score_version": "v1.0.0"
        }
        
        adjustment = crud.premium_adjustment_crud.create(db, adjustment_data)
        
        return {
            "message": "Premium adjustment applied successfully",
            "adjustment_id": adjustment.id,
            "new_premium": adjustment.new_premium,
            "delta_pct": adjustment.delta_pct
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying premium adjustment: {str(e)}"
        )


# Admin routes
@router.get("/admin/adjustments", response_model=List[schemas.PremiumAdjustment])
async def list_all_adjustments(
    skip: int = 0,
    limit: int = 100,
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """List all premium adjustments (admin only)."""
    # This would need to be implemented in CRUD
    # For now, return empty list
    return []


@router.post("/admin/bulk-adjust")
async def bulk_adjust_premiums(
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Apply premium adjustments for all active policies (admin only)."""
    try:
        from ..pricing.engine import PricingEngine
        
        # Initialize pricing engine
        pricing_engine = PricingEngine()
        
        # Get all active policies
        policies = []
        users = crud.user_crud.list_users(db, skip=0, limit=1000)
        
        for user in users:
            user_policies = crud.policy_crud.get_active_by_user(db, user.id)
            policies.extend(user_policies)
        
        adjusted_count = 0
        for policy in policies:
            try:
                # Get latest risk score for policy owner
                latest_score = crud.risk_score_crud.get_latest_by_user(db, policy.user_id)
                
                if latest_score:
                    # Calculate adjustment
                    quote = pricing_engine.calculate_quote(
                        score=latest_score.score_value,
                        base_premium=policy.base_premium,
                        policy_id=policy.id
                    )
                    
                    # Create adjustment record
                    adjustment_data = {
                        "policy_id": policy.id,
                        "period_start": policy.start_date,
                        "period_end": policy.end_date,
                        "delta_pct": quote.delta_pct,
                        "delta_amount": quote.delta_amount,
                        "new_premium": quote.new_premium,
                        "reason": quote.rationale,
                        "score_version": latest_score.model_version,
                        "risk_score_id": latest_score.id
                    }
                    
                    crud.premium_adjustment_crud.create(db, adjustment_data)
                    adjusted_count += 1
                
            except Exception as e:
                print(f"Error adjusting premium for policy {policy.id}: {e}")
                continue
        
        return {
            "message": f"Applied premium adjustments to {adjusted_count} policies",
            "total_policies": len(policies),
            "successful": adjusted_count
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error applying bulk premium adjustments: {str(e)}"
        )


@router.get("/admin/pricing-metrics")
async def get_pricing_metrics(
    admin_user: dict = Depends(get_current_admin_dependency),
    db: Session = Depends(get_database_dependency)
):
    """Get pricing system metrics (admin only)."""
    try:
        from ..pricing.engine import PricingEngine
        
        pricing_engine = PricingEngine()
        metrics = pricing_engine.get_metrics()
        
        return {
            "pricing_rules_version": metrics.get("rules_version", "v1.0.0"),
            "total_adjustments": metrics.get("total_adjustments", 0),
            "average_adjustment_pct": metrics.get("average_adjustment_pct", 0),
            "adjustment_distribution": metrics.get("adjustment_distribution", {}),
            "revenue_impact": metrics.get("revenue_impact", {}),
            "last_bulk_adjustment": metrics.get("last_bulk_adjustment")
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error getting pricing metrics: {str(e)}"
        )
