"""
Pricing tables and configuration for dynamic pricing.
"""
from typing import Dict, List, Any
from datetime import datetime
import json
import os


class PricingTables:
    """Pricing tables and configuration management."""
    
    def __init__(self):
        self.version = "v1.0.0"
        self.last_updated = datetime.now().isoformat()
        
        # Default pricing adjustments by risk band
        self.default_adjustments = {
            "A": -0.15,  # 15% discount for excellent drivers
            "B": -0.05,  # 5% discount for good drivers
            "C": 0.00,   # No adjustment for average drivers
            "D": 0.10,   # 10% increase for below-average drivers
            "E": 0.25    # 25% increase for poor drivers
        }
        
        # Current adjustments (can be updated)
        self.current_adjustments = self.default_adjustments.copy()
        
        # Pricing rules and constraints
        self.rules = {
            "max_adjustment": 0.50,  # Maximum 50% adjustment
            "min_adjustment": -0.30,  # Maximum 30% discount
            "cooldown_days": 30,     # Days between adjustments
            "min_premium": 100.0,    # Minimum premium
            "max_premium": 10000.0   # Maximum premium
        }
    
    def get_adjustment(self, band: str) -> float:
        """Get pricing adjustment for a risk band."""
        return self.current_adjustments.get(band, 0.0)
    
    def get_version(self) -> str:
        """Get current pricing tables version."""
        return self.version
    
    def update_tables(self, new_adjustments: Dict[str, float]):
        """Update pricing adjustments."""
        # Validate adjustments
        for band, adjustment in new_adjustments.items():
            if not (-1.0 <= adjustment <= 1.0):
                raise ValueError(f"Invalid adjustment for band {band}: {adjustment}")
        
        # Update adjustments
        self.current_adjustments.update(new_adjustments)
        self.last_updated = datetime.now().isoformat()
    
    def reset_to_defaults(self):
        """Reset to default pricing adjustments."""
        self.current_adjustments = self.default_adjustments.copy()
        self.last_updated = datetime.now().isoformat()
    
    def get_all_adjustments(self) -> Dict[str, float]:
        """Get all current pricing adjustments."""
        return self.current_adjustments.copy()
    
    def validate_adjustments(self) -> Dict[str, Any]:
        """Validate current pricing adjustments."""
        validation = {
            "is_valid": True,
            "warnings": [],
            "errors": []
        }
        
        # Check each band
        for band, adjustment in self.current_adjustments.items():
            # Check bounds
            if adjustment < self.rules["min_adjustment"]:
                validation["errors"].append(
                    f"Band {band} adjustment {adjustment:.1%} below minimum {self.rules['min_adjustment']:.1%}"
                )
            
            if adjustment > self.rules["max_adjustment"]:
                validation["errors"].append(
                    f"Band {band} adjustment {adjustment:.1%} above maximum {self.rules['max_adjustment']:.1%}"
                )
            
            # Check for extreme adjustments
            if abs(adjustment) > 0.4:
                validation["warnings"].append(
                    f"Band {band} has extreme adjustment: {adjustment:.1%}"
                )
        
        # Check monotonicity (higher risk bands should not have better pricing)
        bands = ["A", "B", "C", "D", "E"]
        for i in range(len(bands) - 1):
            current_band = bands[i]
            next_band = bands[i + 1]
            
            if self.current_adjustments[current_band] < self.current_adjustments[next_band]:
                validation["warnings"].append(
                    f"Band {current_band} has better pricing than {next_band} - may violate risk-based pricing"
                )
        
        validation["is_valid"] = len(validation["errors"]) == 0
        
        return validation
    
    def get_pricing_summary(self) -> Dict[str, Any]:
        """Get summary of current pricing configuration."""
        return {
            "version": self.version,
            "last_updated": self.last_updated,
            "adjustments": self.current_adjustments,
            "rules": self.rules,
            "validation": self.validate_adjustments()
        }
    
    def export_configuration(self, filepath: str):
        """Export pricing configuration to file."""
        config = {
            "version": self.version,
            "last_updated": self.last_updated,
            "adjustments": self.current_adjustments,
            "rules": self.rules,
            "default_adjustments": self.default_adjustments
        }
        
        with open(filepath, "w") as f:
            json.dump(config, f, indent=2)
    
    def import_configuration(self, filepath: str):
        """Import pricing configuration from file."""
        with open(filepath, "r") as f:
            config = json.load(f)
        
        self.version = config.get("version", self.version)
        self.last_updated = config.get("last_updated", self.last_updated)
        self.current_adjustments = config.get("adjustments", self.default_adjustments)
        self.rules = config.get("rules", self.rules)
    
    def create_scenario_analysis(self, base_premium: float = 1000.0) -> Dict[str, Any]:
        """Create scenario analysis for different risk bands."""
        scenarios = {}
        
        for band, adjustment in self.current_adjustments.items():
            new_premium = base_premium * (1 + adjustment)
            scenarios[band] = {
                "adjustment_pct": adjustment,
                "adjustment_amount": base_premium * adjustment,
                "new_premium": new_premium,
                "premium_change": new_premium - base_premium
            }
        
        return {
            "base_premium": base_premium,
            "scenarios": scenarios,
            "summary": {
                "min_premium": min(s["new_premium"] for s in scenarios.values()),
                "max_premium": max(s["new_premium"] for s in scenarios.values()),
                "premium_range": max(s["new_premium"] for s in scenarios.values()) - 
                               min(s["new_premium"] for s in scenarios.values())
            }
        }
    
    def get_band_statistics(self) -> Dict[str, Any]:
        """Get statistics about risk bands."""
        bands = ["A", "B", "C", "D", "E"]
        
        return {
            "total_bands": len(bands),
            "band_descriptions": {
                "A": "Excellent drivers (85-100 score)",
                "B": "Good drivers (70-84 score)",
                "C": "Average drivers (55-69 score)",
                "D": "Below-average drivers (40-54 score)",
                "E": "Poor drivers (0-39 score)"
            },
            "score_ranges": {
                "A": (85, 100),
                "B": (70, 84),
                "C": (55, 69),
                "D": (40, 54),
                "E": (0, 39)
            },
            "adjustments": self.current_adjustments
        }
    
    def calculate_premium_impact(self, score_distribution: Dict[str, int]) -> Dict[str, Any]:
        """Calculate premium impact for a given score distribution."""
        total_policies = sum(score_distribution.values())
        
        if total_policies == 0:
            return {"error": "No policies in distribution"}
        
        # Calculate weighted average adjustment
        weighted_adjustment = 0
        for band, count in score_distribution.items():
            adjustment = self.current_adjustments.get(band, 0)
            weighted_adjustment += adjustment * (count / total_policies)
        
        # Calculate revenue impact
        revenue_impact = {
            "weighted_average_adjustment": weighted_adjustment,
            "total_policies": total_policies,
            "band_distribution": {
                band: count / total_policies 
                for band, count in score_distribution.items()
            }
        }
        
        return revenue_impact
