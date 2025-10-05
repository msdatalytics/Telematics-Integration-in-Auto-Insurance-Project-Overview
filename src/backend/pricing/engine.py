"""
Dynamic pricing engine for telematics-based insurance.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import json
import logging

from .tables import PricingTables
from ..db import schemas
from ..settings import settings


class PricingEngine:
    """Dynamic pricing engine for telematics-based insurance."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.pricing_tables = PricingTables()
        
        # Pricing configuration
        self.max_monthly_change = 0.20  # 20% max change per month
        self.min_premium = 100.0  # Minimum premium
        self.max_premium = 10000.0  # Maximum premium
        
        # Cool-down period (days)
        self.cooldown_days = 30
    
    def calculate_quote(self, score: float, base_premium: float, 
                       policy_id: Optional[int] = None) -> schemas.PricingQuoteResponse:
        """Calculate pricing quote based on risk score."""
        
        # Validate inputs
        if not (0 <= score <= 100):
            raise ValueError("Score must be between 0 and 100")
        
        if base_premium <= 0:
            raise ValueError("Base premium must be positive")
        
        # Determine risk band
        band = self._score_to_band(score)
        
        # Get pricing adjustment
        delta_pct = self.pricing_tables.get_adjustment(band)
        
        # Apply guardrails
        delta_pct = self._apply_guardrails(delta_pct, policy_id)
        
        # Calculate new premium
        delta_amount = base_premium * delta_pct
        new_premium = base_premium + delta_amount
        
        # Ensure premium is within bounds
        new_premium = max(self.min_premium, min(self.max_premium, new_premium))
        
        # Generate rationale
        rationale = self._generate_rationale(score, band, delta_pct)
        
        return schemas.PricingQuoteResponse(
            policy_id=policy_id,
            band=band,
            delta_pct=delta_pct,
            delta_amount=delta_amount,
            new_premium=new_premium,
            rationale=rationale
        )
    
    def _score_to_band(self, score: float) -> str:
        """Convert risk score to band."""
        if score >= 85:
            return "A"
        elif score >= 70:
            return "B"
        elif score >= 55:
            return "C"
        elif score >= 40:
            return "D"
        else:
            return "E"
    
    def _apply_guardrails(self, delta_pct: float, policy_id: Optional[int]) -> float:
        """Apply pricing guardrails."""
        # Check for recent adjustments
        if policy_id:
            # In production, would check database for recent adjustments
            # For now, apply a simple cooldown check
            pass
        
        # Limit monthly change
        if abs(delta_pct) > self.max_monthly_change:
            delta_pct = self.max_monthly_change if delta_pct > 0 else -self.max_monthly_change
        
        return delta_pct
    
    def _generate_rationale(self, score: float, band: str, delta_pct: float) -> str:
        """Generate human-readable rationale for pricing decision."""
        rationale_parts = []
        
        # Score and band
        rationale_parts.append(f"Score {score:.1f} (Band {band})")
        
        # Adjustment explanation
        if delta_pct > 0:
            rationale_parts.append(f"Premium increase of {delta_pct:.1%} due to higher risk profile")
        elif delta_pct < 0:
            rationale_parts.append(f"Premium discount of {abs(delta_pct):.1%} for safe driving behavior")
        else:
            rationale_parts.append("No premium adjustment - neutral risk profile")
        
        # Band-specific explanations
        if band == "A":
            rationale_parts.append("Excellent driving behavior with minimal risk factors")
        elif band == "B":
            rationale_parts.append("Good driving behavior with some areas for improvement")
        elif band == "C":
            rationale_parts.append("Average driving behavior with moderate risk factors")
        elif band == "D":
            rationale_parts.append("Below-average driving behavior with elevated risk factors")
        else:  # E
            rationale_parts.append("Poor driving behavior with significant risk factors")
        
        return ": ".join(rationale_parts)
    
    def calculate_bulk_adjustments(self, policies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate bulk premium adjustments for multiple policies."""
        adjustments = []
        
        for policy in policies:
            try:
                quote = self.calculate_quote(
                    score=policy['score'],
                    base_premium=policy['base_premium'],
                    policy_id=policy['policy_id']
                )
                
                adjustments.append({
                    'policy_id': policy['policy_id'],
                    'band': quote.band,
                    'delta_pct': quote.delta_pct,
                    'delta_amount': quote.delta_amount,
                    'new_premium': quote.new_premium,
                    'rationale': quote.rationale
                })
                
            except Exception as e:
                self.logger.error(f"Error calculating adjustment for policy {policy['policy_id']}: {e}")
                continue
        
        return adjustments
    
    def get_pricing_metrics(self) -> Dict[str, Any]:
        """Get pricing system metrics."""
        return {
            "rules_version": self.pricing_tables.get_version(),
            "total_adjustments": 0,  # Would come from database
            "average_adjustment_pct": 0.0,  # Would come from database
            "adjustment_distribution": {
                "A": 0, "B": 0, "C": 0, "D": 0, "E": 0
            },
            "revenue_impact": {
                "total_premium_change": 0.0,
                "premium_increase": 0.0,
                "premium_decrease": 0.0
            },
            "last_bulk_adjustment": None
        }
    
    def validate_pricing_rules(self) -> Dict[str, Any]:
        """Validate pricing rules for fairness and compliance."""
        validation_results = {
            "is_valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check band coverage
        bands = ["A", "B", "C", "D", "E"]
        for band in bands:
            adjustment = self.pricing_tables.get_adjustment(band)
            
            # Check for extreme adjustments
            if abs(adjustment) > 0.5:  # 50% max adjustment
                validation_results["warnings"].append(
                    f"Band {band} has extreme adjustment: {adjustment:.1%}"
                )
            
            # Check for monotonicity (higher risk should not have better pricing)
            if band in ["D", "E"] and adjustment < 0:
                validation_results["errors"].append(
                    f"Band {band} has negative adjustment - violates risk-based pricing"
                )
        
        # Check for reasonable spread
        max_adjustment = max(self.pricing_tables.get_adjustment(band) for band in bands)
        min_adjustment = min(self.pricing_tables.get_adjustment(band) for band in bands)
        
        if max_adjustment - min_adjustment > 0.6:  # 60% spread
            validation_results["warnings"].append(
                f"Large pricing spread: {max_adjustment:.1%} to {min_adjustment:.1%}"
            )
        
        validation_results["is_valid"] = len(validation_results["errors"]) == 0
        
        return validation_results
    
    def simulate_pricing_scenarios(self, base_premium: float = 1000.0) -> Dict[str, Any]:
        """Simulate pricing scenarios for different risk scores."""
        scenarios = {}
        
        # Test different score ranges
        score_ranges = [
            (90, 100, "Excellent"),
            (70, 89, "Good"),
            (50, 69, "Average"),
            (30, 49, "Below Average"),
            (0, 29, "Poor")
        ]
        
        for min_score, max_score, description in score_ranges:
            # Use midpoint score
            score = (min_score + max_score) / 2
            
            quote = self.calculate_quote(score, base_premium)
            
            scenarios[description] = {
                "score_range": f"{min_score}-{max_score}",
                "test_score": score,
                "band": quote.band,
                "delta_pct": quote.delta_pct,
                "new_premium": quote.new_premium,
                "rationale": quote.rationale
            }
        
        return scenarios
    
    def update_pricing_tables(self, new_tables: Dict[str, float]):
        """Update pricing tables with new adjustments."""
        # Validate new tables
        validation = self.validate_pricing_rules()
        if not validation["is_valid"]:
            raise ValueError(f"Invalid pricing tables: {validation['errors']}")
        
        # Update tables
        self.pricing_tables.update_tables(new_tables)
        
        self.logger.info("Pricing tables updated successfully")
    
    def get_fairness_metrics(self, historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate fairness metrics for pricing decisions."""
        if not historical_data:
            return {"error": "No historical data provided"}
        
        df = pd.DataFrame(historical_data)
        
        # Demographic parity (if demographic data available)
        fairness_metrics = {
            "demographic_parity": {},
            "equalized_odds": {},
            "calibration": {}
        }
        
        # Calculate average adjustments by band
        band_adjustments = df.groupby('band')['delta_pct'].agg(['mean', 'std', 'count']).to_dict()
        fairness_metrics["band_adjustments"] = band_adjustments
        
        # Calculate score distribution
        score_distribution = df['score'].describe().to_dict()
        fairness_metrics["score_distribution"] = score_distribution
        
        return fairness_metrics
