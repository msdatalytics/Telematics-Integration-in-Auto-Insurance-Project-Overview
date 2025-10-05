"""
Test suite for ML features and scoring.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.backend.ml.features import FeatureEngineer
from src.backend.ml.train import ModelTrainer
from src.backend.pricing.engine import PricingEngine
from src.backend.pricing.tables import PricingTables


class TestFeatureEngineer:
    """Test feature engineering functionality."""
    
    def test_extract_trip_features(self):
        """Test trip feature extraction."""
        from src.backend.db.models import Trip
        
        # Create mock trip
        trip = Trip(
            id=1,
            user_id=1,
            vehicle_id=1,
            trip_uuid="test-trip",
            start_ts=datetime.now(),
            end_ts=datetime.now() + timedelta(minutes=30),
            distance_km=15.5,
            duration_minutes=30,
            mean_speed_kph=31.0,
            max_speed_kph=45.0,
            night_fraction=0.2,
            weekend_fraction=0.0,
            urban_fraction=0.8,
            harsh_brake_events=2,
            harsh_accel_events=1,
            speeding_events=3,
            phone_distraction_prob=0.05,
            weather_exposure=0.1
        )
        
        engineer = FeatureEngineer()
        features = engineer.extract_trip_features(trip)
        
        assert "distance_km" in features
        assert "duration_minutes" in features
        assert "mean_speed_kph" in features
        assert "harsh_brake_rate" in features
        assert "harsh_accel_rate" in features
        assert "speeding_ratio" in features
        assert features["distance_km"] == 15.5
        assert features["duration_minutes"] == 30

    def test_create_feature_dataset(self):
        """Test feature dataset creation."""
        engineer = FeatureEngineer()
        
        # This will create synthetic data
        df = engineer.create_feature_dataset(days_back=7)
        
        assert isinstance(df, pd.DataFrame)
        assert len(df) > 0
        assert "user_id" in df.columns
        assert "claim_within_12m" in df.columns
        assert "claim_cost" in df.columns

    def test_get_feature_list(self):
        """Test feature list retrieval."""
        engineer = FeatureEngineer()
        feature_list = engineer.get_feature_list()
        
        assert isinstance(feature_list, list)
        assert len(feature_list) > 0
        assert all(isinstance(f, str) for f in feature_list)


class TestModelTrainer:
    """Test model training functionality."""
    
    def test_prepare_data(self):
        """Test data preparation for training."""
        trainer = ModelTrainer()
        
        # Create mock data
        df = pd.DataFrame({
            'user_id': [1, 2, 3],
            'total_distance_km': [100, 200, 150],
            'avg_speed_kph': [50, 60, 55],
            'harsh_brake_rate': [0.1, 0.2, 0.15],
            'claim_within_12m': [0, 1, 0],
            'claim_cost': [0, 5000, 0]
        })
        
        X, y_classification, y_regression = trainer.prepare_data(df)
        
        assert isinstance(X, pd.DataFrame)
        assert isinstance(y_classification, pd.Series)
        assert isinstance(y_regression, pd.Series)
        assert len(X) == len(y_classification) == len(y_regression)

    def test_train_classification_model(self):
        """Test classification model training."""
        trainer = ModelTrainer()
        
        # Create mock data
        X = pd.DataFrame({
            'total_distance_km': [100, 200, 150, 300, 250],
            'avg_speed_kph': [50, 60, 55, 70, 65],
            'harsh_brake_rate': [0.1, 0.2, 0.15, 0.3, 0.25]
        })
        y = pd.Series([0, 1, 0, 1, 1])
        
        results = trainer.train_classification_model(X, y)
        
        assert "model" in results
        assert "scaler" in results
        assert "metrics" in results
        assert "feature_importance" in results
        assert "test_predictions" in results

    def test_train_regression_model(self):
        """Test regression model training."""
        trainer = ModelTrainer()
        
        # Create mock data for claimants only
        X = pd.DataFrame({
            'total_distance_km': [200, 300, 250],
            'avg_speed_kph': [60, 70, 65],
            'harsh_brake_rate': [0.2, 0.3, 0.25]
        })
        y = pd.Series([5000, 8000, 6000])
        
        results = trainer.train_regression_model(X, y)
        
        assert "model" in results
        assert "scaler" in results
        assert "metrics" in results
        assert "feature_importance" in results
        assert "test_predictions" in results


class TestPricingEngine:
    """Test pricing engine functionality."""
    
    def test_calculate_quote(self):
        """Test pricing quote calculation."""
        engine = PricingEngine()
        
        quote = engine.calculate_quote(score=75.0, base_premium=1000.0)
        
        assert quote.band in ["A", "B", "C", "D", "E"]
        assert isinstance(quote.delta_pct, float)
        assert isinstance(quote.new_premium, float)
        assert quote.new_premium > 0
        assert "rationale" in quote.rationale

    def test_score_to_band(self):
        """Test score to band conversion."""
        engine = PricingEngine()
        
        assert engine._score_to_band(95) == "A"
        assert engine._score_to_band(80) == "B"
        assert engine._score_to_band(65) == "C"
        assert engine._score_to_band(45) == "D"
        assert engine._score_to_band(25) == "E"

    def test_validate_pricing_rules(self):
        """Test pricing rules validation."""
        engine = PricingEngine()
        
        validation = engine.validate_pricing_rules()
        
        assert "is_valid" in validation
        assert "warnings" in validation
        assert "errors" in validation
        assert isinstance(validation["is_valid"], bool)

    def test_simulate_pricing_scenarios(self):
        """Test pricing scenario simulation."""
        engine = PricingEngine()
        
        scenarios = engine.simulate_pricing_scenarios(base_premium=1000.0)
        
        assert "Excellent" in scenarios
        assert "Good" in scenarios
        assert "Average" in scenarios
        assert "Below Average" in scenarios
        assert "Poor" in scenarios
        
        for scenario in scenarios.values():
            if isinstance(scenario, dict) and "band" in scenario:
                assert scenario["band"] in ["A", "B", "C", "D", "E"]


class TestPricingTables:
    """Test pricing tables functionality."""
    
    def test_get_adjustment(self):
        """Test adjustment retrieval."""
        tables = PricingTables()
        
        assert isinstance(tables.get_adjustment("A"), float)
        assert isinstance(tables.get_adjustment("B"), float)
        assert isinstance(tables.get_adjustment("C"), float)
        assert isinstance(tables.get_adjustment("D"), float)
        assert isinstance(tables.get_adjustment("E"), float)

    def test_validate_adjustments(self):
        """Test adjustments validation."""
        tables = PricingTables()
        
        validation = tables.validate_adjustments()
        
        assert "is_valid" in validation
        assert "warnings" in validation
        assert "errors" in validation
        assert isinstance(validation["is_valid"], bool)

    def test_create_scenario_analysis(self):
        """Test scenario analysis creation."""
        tables = PricingTables()
        
        analysis = tables.create_scenario_analysis(base_premium=1000.0)
        
        assert "base_premium" in analysis
        assert "scenarios" in analysis
        assert "summary" in analysis
        assert analysis["base_premium"] == 1000.0

    def test_update_tables(self):
        """Test tables update."""
        tables = PricingTables()
        
        new_adjustments = {
            "A": -0.20,
            "B": -0.10,
            "C": 0.00,
            "D": 0.15,
            "E": 0.30
        }
        
        tables.update_tables(new_adjustments)
        
        assert tables.get_adjustment("A") == -0.20
        assert tables.get_adjustment("B") == -0.10
        assert tables.get_adjustment("C") == 0.00
        assert tables.get_adjustment("D") == 0.15
        assert tables.get_adjustment("E") == 0.30


if __name__ == "__main__":
    pytest.main([__file__])
