"""
Feature engineering for telematics risk scoring.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
import logging

from ..db.base import SessionLocal
from ..db import crud, models
from ..settings import settings


class FeatureEngineer:
    """Feature engineering for telematics risk scoring."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.feature_store_path = settings.FEATURE_STORE_PATH
    
    def extract_trip_features(self, trip: models.Trip) -> Dict[str, float]:
        """Extract features from a single trip."""
        features = {}
        
        # Basic trip features
        features['distance_km'] = trip.distance_km
        features['duration_minutes'] = trip.duration_minutes
        features['mean_speed_kph'] = trip.mean_speed_kph
        features['max_speed_kph'] = trip.max_speed_kph
        
        # Driving behavior features
        features['speeding_ratio'] = trip.speeding_events / max(trip.duration_minutes, 1)
        features['harsh_brake_rate'] = trip.harsh_brake_events / max(trip.distance_km, 1)
        features['harsh_accel_rate'] = trip.harsh_accel_events / max(trip.distance_km, 1)
        features['cornering_rate'] = 0.0  # Would be calculated from GPS data
        
        # Time-based features
        features['night_fraction'] = trip.night_fraction
        features['weekend_fraction'] = trip.weekend_fraction
        features['urban_fraction'] = trip.urban_fraction
        
        # Risk factors
        features['phone_distraction_prob'] = trip.phone_distraction_prob
        features['weather_exposure'] = trip.weather_exposure
        
        # Derived features
        features['speed_variance'] = self._calculate_speed_variance(trip)
        features['accel_variance'] = self._calculate_accel_variance(trip)
        features['brake_intensity_avg'] = self._calculate_avg_brake_intensity(trip)
        
        return features
    
    def extract_daily_features(self, user_id: int, date: datetime, 
                              db: SessionLocal) -> Dict[str, float]:
        """Extract daily aggregated features for a user."""
        features = {}
        
        # Get trips for the day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        trips = db.query(models.Trip).filter(
            models.Trip.user_id == user_id,
            models.Trip.start_ts >= start_of_day,
            models.Trip.start_ts < end_of_day
        ).all()
        
        if not trips:
            return self._get_default_daily_features()
        
        # Aggregate trip features
        trip_features = [self.extract_trip_features(trip) for trip in trips]
        
        # Distance and time features
        features['total_distance_km'] = sum(tf['distance_km'] for tf in trip_features)
        features['total_duration_minutes'] = sum(tf['duration_minutes'] for tf in trip_features)
        features['num_trips'] = len(trips)
        
        # Speed features
        features['avg_speed_kph'] = np.mean([tf['mean_speed_kph'] for tf in trip_features])
        features['max_speed_kph'] = max([tf['max_speed_kph'] for tf in trip_features])
        features['speed_variance'] = np.var([tf['mean_speed_kph'] for tf in trip_features])
        
        # Behavior features
        features['total_harsh_brakes'] = sum(tf['harsh_brake_events'] for tf in trip_features)
        features['total_harsh_accels'] = sum(tf['harsh_accel_events'] for tf in trip_features)
        features['total_speeding_events'] = sum(tf['speeding_events'] for tf in trip_features)
        
        features['harsh_brake_rate'] = features['total_harsh_brakes'] / max(features['total_distance_km'], 1)
        features['harsh_accel_rate'] = features['total_harsh_accels'] / max(features['total_distance_km'], 1)
        features['speeding_ratio'] = features['total_speeding_events'] / max(features['total_duration_minutes'], 1)
        
        # Time-based features
        features['night_fraction'] = np.mean([tf['night_fraction'] for tf in trip_features])
        features['weekend_fraction'] = np.mean([tf['weekend_fraction'] for tf in trip_features])
        features['urban_fraction'] = np.mean([tf['urban_fraction'] for tf in trip_features])
        
        # Risk factors
        features['phone_distraction_prob'] = np.mean([tf['phone_distraction_prob'] for tf in trip_features])
        features['weather_exposure'] = np.mean([tf['weather_exposure'] for tf in trip_features])
        
        # Contextual features
        features.update(self._extract_contextual_features(user_id, date, db))
        
        return features
    
    def extract_user_features(self, user_id: int, db: SessionLocal, 
                            days_back: int = 30) -> Dict[str, float]:
        """Extract user-level features over a time window."""
        features = {}
        
        # Get user's recent trips
        cutoff_date = datetime.utcnow() - timedelta(days=days_back)
        trips = db.query(models.Trip).filter(
            models.Trip.user_id == user_id,
            models.Trip.start_ts >= cutoff_date
        ).all()
        
        if not trips:
            return self._get_default_user_features()
        
        # Extract trip features
        trip_features = [self.extract_trip_features(trip) for trip in trips]
        
        # Aggregate features
        features['total_distance_km'] = sum(tf['distance_km'] for tf in trip_features)
        features['total_duration_minutes'] = sum(tf['duration_minutes'] for tf in trip_features)
        features['num_trips'] = len(trips)
        
        # Average metrics
        features['avg_distance_per_trip'] = features['total_distance_km'] / len(trips)
        features['avg_duration_per_trip'] = features['total_duration_minutes'] / len(trips)
        features['avg_speed_kph'] = np.mean([tf['mean_speed_kph'] for tf in trip_features])
        
        # Behavior patterns
        features['avg_harsh_brake_rate'] = np.mean([tf['harsh_brake_rate'] for tf in trip_features])
        features['avg_harsh_accel_rate'] = np.mean([tf['harsh_accel_rate'] for tf in trip_features])
        features['avg_speeding_ratio'] = np.mean([tf['speeding_ratio'] for tf in trip_features])
        
        # Time patterns
        features['avg_night_fraction'] = np.mean([tf['night_fraction'] for tf in trip_features])
        features['avg_weekend_fraction'] = np.mean([tf['weekend_fraction'] for tf in trip_features])
        features['avg_urban_fraction'] = np.mean([tf['urban_fraction'] for tf in trip_features])
        
        # Risk factors
        features['avg_phone_distraction'] = np.mean([tf['phone_distraction_prob'] for tf in trip_features])
        features['avg_weather_exposure'] = np.mean([tf['weather_exposure'] for tf in trip_features])
        
        # Consistency metrics
        features['speed_consistency'] = 1.0 - np.std([tf['mean_speed_kph'] for tf in trip_features]) / max(np.mean([tf['mean_speed_kph'] for tf in trip_features]), 1)
        features['behavior_consistency'] = 1.0 - np.std([tf['harsh_brake_rate'] + tf['harsh_accel_rate'] for tf in trip_features])
        
        return features
    
    def _calculate_speed_variance(self, trip: models.Trip) -> float:
        """Calculate speed variance for a trip."""
        # This would typically use telematics events
        # For now, use a simplified calculation
        return 0.0
    
    def _calculate_accel_variance(self, trip: models.Trip) -> float:
        """Calculate acceleration variance for a trip."""
        # This would typically use telematics events
        # For now, use a simplified calculation
        return 0.0
    
    def _calculate_avg_brake_intensity(self, trip: models.Trip) -> float:
        """Calculate average brake intensity for a trip."""
        # This would typically use telematics events
        # For now, use a simplified calculation
        return 0.0
    
    def _extract_contextual_features(self, user_id: int, date: datetime, 
                                    db: SessionLocal) -> Dict[str, float]:
        """Extract contextual features (weather, road conditions, etc.)."""
        features = {}
        
        # Get context data for the day
        start_of_day = date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = start_of_day + timedelta(days=1)
        
        contexts = db.query(models.Context).filter(
            models.Context.ts >= start_of_day,
            models.Context.ts < end_of_day
        ).all()
        
        if contexts:
            features['avg_temperature_c'] = np.mean([c.temperature_c for c in contexts if c.temperature_c])
            features['avg_precipitation_mm'] = np.mean([c.precipitation_mm for c in contexts if c.precipitation_mm])
            features['avg_visibility_km'] = np.mean([c.visibility_km for c in contexts if c.visibility_km])
            features['avg_crime_index'] = np.mean([c.crime_index for c in contexts if c.crime_index])
            features['avg_accident_density'] = np.mean([c.accident_density for c in contexts if c.accident_density])
        else:
            # Default values
            features['avg_temperature_c'] = 20.0
            features['avg_precipitation_mm'] = 0.0
            features['avg_visibility_km'] = 10.0
            features['avg_crime_index'] = 50.0
            features['avg_accident_density'] = 2.0
        
        return features
    
    def _get_default_daily_features(self) -> Dict[str, float]:
        """Get default features for days with no trips."""
        return {
            'total_distance_km': 0.0,
            'total_duration_minutes': 0.0,
            'num_trips': 0,
            'avg_speed_kph': 0.0,
            'max_speed_kph': 0.0,
            'speed_variance': 0.0,
            'total_harsh_brakes': 0,
            'total_harsh_accels': 0,
            'total_speeding_events': 0,
            'harsh_brake_rate': 0.0,
            'harsh_accel_rate': 0.0,
            'speeding_ratio': 0.0,
            'night_fraction': 0.0,
            'weekend_fraction': 0.0,
            'urban_fraction': 0.0,
            'phone_distraction_prob': 0.0,
            'weather_exposure': 0.0,
            'avg_temperature_c': 20.0,
            'avg_precipitation_mm': 0.0,
            'avg_visibility_km': 10.0,
            'avg_crime_index': 50.0,
            'avg_accident_density': 2.0
        }
    
    def _get_default_user_features(self) -> Dict[str, float]:
        """Get default features for users with no recent trips."""
        return {
            'total_distance_km': 0.0,
            'total_duration_minutes': 0.0,
            'num_trips': 0,
            'avg_distance_per_trip': 0.0,
            'avg_duration_per_trip': 0.0,
            'avg_speed_kph': 0.0,
            'avg_harsh_brake_rate': 0.0,
            'avg_harsh_accel_rate': 0.0,
            'avg_speeding_ratio': 0.0,
            'avg_night_fraction': 0.0,
            'avg_weekend_fraction': 0.0,
            'avg_urban_fraction': 0.0,
            'avg_phone_distraction': 0.0,
            'avg_weather_exposure': 0.0,
            'speed_consistency': 1.0,
            'behavior_consistency': 1.0
        }
    
    def create_feature_dataset(self, days_back: int = 90) -> pd.DataFrame:
        """Create a feature dataset for model training."""
        db = SessionLocal()
        
        try:
            features_list = []
            
            # Get all users
            users = db.query(models.User).all()
            
            for user in users:
                # Get user features
                user_features = self.extract_user_features(user.id, db, days_back)
                
                # Add user ID
                user_features['user_id'] = user.id
                
                # Generate synthetic target (in production, this would come from claims data)
                user_features.update(self._generate_synthetic_targets(user_features))
                
                features_list.append(user_features)
            
            # Create DataFrame
            df = pd.DataFrame(features_list)
            
            # Save to feature store
            self._save_to_feature_store(df)
            
            return df
            
        finally:
            db.close()
    
    def _generate_synthetic_targets(self, features: Dict[str, float]) -> Dict[str, float]:
        """Generate synthetic targets for model training."""
        # Claim probability (correlated with risky behavior)
        claim_prob = 0.01  # Base probability
        
        # Increase probability based on risky behavior
        if features.get('avg_harsh_brake_rate', 0) > 0.1:
            claim_prob += 0.02
        if features.get('avg_harsh_accel_rate', 0) > 0.1:
            claim_prob += 0.02
        if features.get('avg_speeding_ratio', 0) > 0.05:
            claim_prob += 0.03
        if features.get('avg_night_fraction', 0) > 0.3:
            claim_prob += 0.02
        
        # Add some randomness
        claim_prob += np.random.normal(0, 0.01)
        claim_prob = max(0.001, min(0.2, claim_prob))  # Clamp between 0.1% and 20%
        
        # Generate binary claim outcome
        claim_within_12m = 1 if np.random.random() < claim_prob else 0
        
        # Generate claim cost (if claim occurs)
        if claim_within_12m:
            claim_cost = np.random.lognormal(8, 1)  # Log-normal distribution
            claim_cost = max(1000, min(50000, claim_cost))  # Clamp between $1k and $50k
        else:
            claim_cost = 0.0
        
        return {
            'claim_within_12m': claim_within_12m,
            'claim_cost': claim_cost
        }
    
    def _save_to_feature_store(self, df: pd.DataFrame):
        """Save features to the feature store."""
        import os
        
        # Create feature store directory
        os.makedirs(self.feature_store_path, exist_ok=True)
        
        # Save as parquet
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.feature_store_path, f"features_{timestamp}.parquet")
        df.to_parquet(filepath, index=False)
        
        # Save feature list
        feature_list = list(df.columns)
        feature_list.remove('user_id')
        feature_list.remove('claim_within_12m')
        feature_list.remove('claim_cost')
        
        import json
        with open(os.path.join(self.feature_store_path, "feature_list.json"), "w") as f:
            json.dump(feature_list, f, indent=2)
        
        self.logger.info(f"Saved features to {filepath}")
        self.logger.info(f"Feature list: {len(feature_list)} features")
    
    def get_feature_list(self) -> List[str]:
        """Get the list of features used for modeling."""
        import json
        import os
        
        feature_file = os.path.join(self.feature_store_path, "feature_list.json")
        
        if os.path.exists(feature_file):
            with open(feature_file, "r") as f:
                return json.load(f)
        else:
            # Return default feature list
            return [
                'total_distance_km', 'total_duration_minutes', 'num_trips',
                'avg_distance_per_trip', 'avg_duration_per_trip', 'avg_speed_kph',
                'avg_harsh_brake_rate', 'avg_harsh_accel_rate', 'avg_speeding_ratio',
                'avg_night_fraction', 'avg_weekend_fraction', 'avg_urban_fraction',
                'avg_phone_distraction', 'avg_weather_exposure', 'speed_consistency',
                'behavior_consistency'
            ]
