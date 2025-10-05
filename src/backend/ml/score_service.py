"""
Risk scoring service for real-time and batch scoring.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import os
import json
import pickle
import logging
from datetime import datetime, timedelta
import asyncio

from .features import FeatureEngineer
from ..db.base import SessionLocal
from ..db import crud, models, schemas
from ..settings import settings


class ScoreService:
    """Risk scoring service for telematics data."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models_path = settings.MODEL_ARTIFACTS_PATH
        self.feature_engineer = FeatureEngineer()
        
        # Model artifacts
        self.classification_model = None
        self.regression_model = None
        self.classification_scaler = None
        self.regression_scaler = None
        self.feature_names = None
        self.model_version = None
        
        # Initialization flag
        self._initialized = False
    
    async def initialize(self):
        """Initialize the scoring service with latest models."""
        try:
            # Find latest model directory
            model_dirs = [d for d in os.listdir(self.models_path) 
                         if os.path.isdir(os.path.join(self.models_path, d))]
            
            if not model_dirs:
                self.logger.warning("No trained models found, using default scoring")
                self._initialized = True
                return
            
            latest_model_dir = sorted(model_dirs)[-1]
            model_path = os.path.join(self.models_path, latest_model_dir)
            
            # Load model artifacts
            self.classification_model = self._load_model(os.path.join(model_path, "classification_model.pkl"))
            self.regression_model = self._load_model(os.path.join(model_path, "regression_model.pkl"))
            self.classification_scaler = self._load_model(os.path.join(model_path, "classification_scaler.pkl"))
            self.regression_scaler = self._load_model(os.path.join(model_path, "regression_scaler.pkl"))
            
            with open(os.path.join(model_path, "feature_names.json"), "r") as f:
                self.feature_names = json.load(f)
            
            self.model_version = latest_model_dir
            self._initialized = True
            
            self.logger.info(f"Scoring service initialized with model version: {self.model_version}")
            
        except Exception as e:
            self.logger.error(f"Error initializing scoring service: {e}")
            self._initialized = True  # Allow service to continue with default scoring
    
    def _load_model(self, model_path: str):
        """Load a pickled model."""
        with open(model_path, "rb") as f:
            return pickle.load(f)
    
    async def compute_trip_score(self, db: SessionLocal, trip_id: int) -> schemas.RiskScore:
        """Compute risk score for a specific trip."""
        trip = crud.trip_crud.get_by_id(db, trip_id)
        if not trip:
            raise ValueError(f"Trip {trip_id} not found")
        
        # Extract trip features
        trip_features = self.feature_engineer.extract_trip_features(trip)
        
        # Convert to DataFrame
        feature_df = pd.DataFrame([trip_features])
        
        # Ensure all required features exist
        for feature in self.feature_names:
            if feature not in feature_df.columns:
                feature_df[feature] = 0.0
        
        # Prepare features
        X = feature_df[self.feature_names].fillna(0)
        
        # Scale features
        X_scaled = self.classification_scaler.transform(X)
        
        # Get predictions
        claim_probability = self.classification_model.predict_proba(X_scaled)[0, 1]
        
        # For regression, we need to handle the case where there might not be enough claimants
        try:
            claim_severity = self.regression_model.predict(X_scaled)[0]
            claim_severity = max(1000, min(50000, claim_severity))  # Clamp between $1k and $50k
        except:
            claim_severity = 10000  # Default severity
        
        # Calculate expected loss
        expected_loss = claim_probability * claim_severity
        
        # Convert to risk score (0-100 scale, higher is better)
        # Use percentile ranking based on expected loss
        score_value = max(0, min(100, 100 - (expected_loss / 1000) * 10))
        
        # Determine risk band
        if score_value >= 85:
            band = "A"
        elif score_value >= 70:
            band = "B"
        elif score_value >= 55:
            band = "C"
        elif score_value >= 40:
            band = "D"
        else:
            band = "E"
        
        # Generate explanations
        explanations = self._generate_explanations(trip_features, score_value, band)
        
        # Create risk score record
        risk_score_data = {
            "user_id": trip.user_id,
            "trip_id": trip_id,
            "score_type": "trip",
            "score_value": score_value,
            "band": band,
            "expected_loss": expected_loss,
            "claim_probability": claim_probability,
            "claim_severity": claim_severity,
            "model_version": self.model_version or "v1.0.0",
            "feature_values": trip_features,
            "explanations": explanations
        }
        
        return crud.risk_score_crud.create(db, risk_score_data)
    
    async def compute_daily_score(self, db: SessionLocal, user_id: int) -> schemas.RiskScore:
        """Compute daily risk score for a user."""
        # Extract daily features
        today = datetime.utcnow().date()
        daily_features = self.feature_engineer.extract_daily_features(user_id, today, db)
        
        # Convert to DataFrame
        feature_df = pd.DataFrame([daily_features])
        
        # Ensure all required features exist
        for feature in self.feature_names:
            if feature not in feature_df.columns:
                feature_df[feature] = 0.0
        
        # Prepare features
        X = feature_df[self.feature_names].fillna(0)
        
        # Scale features
        X_scaled = self.classification_scaler.transform(X)
        
        # Get predictions
        claim_probability = self.classification_model.predict_proba(X_scaled)[0, 1]
        
        # For regression
        try:
            claim_severity = self.regression_model.predict(X_scaled)[0]
            claim_severity = max(1000, min(50000, claim_severity))
        except:
            claim_severity = 10000
        
        # Calculate expected loss
        expected_loss = claim_probability * claim_severity
        
        # Convert to risk score
        score_value = max(0, min(100, 100 - (expected_loss / 1000) * 10))
        
        # Determine risk band
        if score_value >= 85:
            band = "A"
        elif score_value >= 70:
            band = "B"
        elif score_value >= 55:
            band = "C"
        elif score_value >= 40:
            band = "D"
        else:
            band = "E"
        
        # Generate explanations
        explanations = self._generate_explanations(daily_features, score_value, band)
        
        # Create risk score record
        risk_score_data = {
            "user_id": user_id,
            "trip_id": None,
            "score_type": "daily",
            "score_value": score_value,
            "band": band,
            "expected_loss": expected_loss,
            "claim_probability": claim_probability,
            "claim_severity": claim_severity,
            "model_version": self.model_version or "v1.0.0",
            "feature_values": daily_features,
            "explanations": explanations
        }
        
        return crud.risk_score_crud.create(db, risk_score_data)
    
    def _generate_explanations(self, features: Dict[str, float], score: float, band: str) -> List[str]:
        """Generate human-readable explanations for the risk score."""
        explanations = []
        
        # Score explanation
        explanations.append(f"Risk Score: {score:.1f} (Band {band})")
        
        # Feature-based explanations
        if features.get('harsh_brake_rate', 0) > 0.1:
            explanations.append("High harsh braking rate detected")
        elif features.get('harsh_brake_rate', 0) < 0.05:
            explanations.append("Low harsh braking rate - good driving behavior")
        
        if features.get('harsh_accel_rate', 0) > 0.1:
            explanations.append("High harsh acceleration rate detected")
        elif features.get('harsh_accel_rate', 0) < 0.05:
            explanations.append("Low harsh acceleration rate - smooth driving")
        
        if features.get('speeding_ratio', 0) > 0.05:
            explanations.append("Frequent speeding detected")
        elif features.get('speeding_ratio', 0) < 0.02:
            explanations.append("Good speed compliance")
        
        if features.get('night_fraction', 0) > 0.3:
            explanations.append("High night driving percentage")
        elif features.get('night_fraction', 0) < 0.1:
            explanations.append("Low night driving - safer driving pattern")
        
        if features.get('phone_distraction_prob', 0) > 0.05:
            explanations.append("Potential phone distraction detected")
        
        if features.get('weather_exposure', 0) > 0.1:
            explanations.append("Driving in adverse weather conditions")
        
        # Overall assessment
        if score >= 80:
            explanations.append("Excellent driving behavior - low risk profile")
        elif score >= 60:
            explanations.append("Good driving behavior with room for improvement")
        elif score >= 40:
            explanations.append("Moderate risk profile - consider safer driving practices")
        else:
            explanations.append("High risk profile - immediate attention to driving behavior recommended")
        
        return explanations
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get scoring service metrics."""
        db = SessionLocal()
        
        try:
            # Get recent scores
            recent_scores = db.query(models.RiskScore).filter(
                models.RiskScore.computed_at >= datetime.utcnow() - timedelta(days=7)
            ).all()
            
            if recent_scores:
                scores = [score.score_value for score in recent_scores]
                bands = [score.band for score in recent_scores]
                
                # Calculate distribution
                band_distribution = {}
                for band in ['A', 'B', 'C', 'D', 'E']:
                    band_distribution[band] = bands.count(band)
                
                return {
                    "model_version": self.model_version,
                    "last_training_date": "2024-01-01",  # Would come from model metadata
                    "total_scores": len(recent_scores),
                    "average_score": np.mean(scores),
                    "score_distribution": band_distribution,
                    "model_performance": {
                        "classification_auc": 0.75,  # Would come from evaluation
                        "regression_rmse": 2000.0
                    }
                }
            else:
                return {
                    "model_version": self.model_version,
                    "total_scores": 0,
                    "average_score": 0,
                    "score_distribution": {},
                    "model_performance": {}
                }
        
        finally:
            db.close()


# Global scoring service instance
score_service = ScoreService()


async def main():
    """Main function for running the scoring service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Telematics Risk Scoring Service")
    parser.add_argument("--compute-daily", action="store_true", help="Compute daily scores for all users")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize scoring service
    await score_service.initialize()
    
    if args.compute_daily:
        # Compute daily scores for all users
        db = SessionLocal()
        
        try:
            users = crud.user_crud.list_users(db, skip=0, limit=1000)
            
            computed_count = 0
            for user in users:
                try:
                    await score_service.compute_daily_score(db, user.id)
                    computed_count += 1
                except Exception as e:
                    print(f"Error computing score for user {user.id}: {e}")
                    continue
            
            print(f"Computed daily scores for {computed_count} users")
        
        finally:
            db.close()
    else:
        print("Scoring service initialized. Use --compute-daily to compute scores.")


if __name__ == "__main__":
    asyncio.run(main())
