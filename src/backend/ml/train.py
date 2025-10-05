"""
Model training pipeline for telematics risk scoring.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime
import os
import json
import pickle
import logging

from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score, precision_recall_curve, roc_curve,
    mean_squared_error, mean_absolute_error, r2_score
)
from sklearn.calibration import CalibratedClassifierCV
import xgboost as xgb
import lightgbm as lgb

from .features import FeatureEngineer
from ..settings import settings


class ModelTrainer:
    """Model training pipeline for risk scoring."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models_path = settings.MODEL_ARTIFACTS_PATH
        self.feature_engineer = FeatureEngineer()
        
        # Model parameters
        self.classification_params = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42
        }
        
        self.regression_params = {
            'n_estimators': 100,
            'max_depth': 6,
            'learning_rate': 0.1,
            'subsample': 0.8,
            'colsample_bytree': 0.8,
            'random_state': 42
        }
    
    def prepare_data(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """Prepare data for training."""
        # Separate features and targets
        feature_cols = self.feature_engineer.get_feature_list()
        
        # Ensure all features exist
        missing_features = set(feature_cols) - set(df.columns)
        if missing_features:
            self.logger.warning(f"Missing features: {missing_features}")
            for feature in missing_features:
                df[feature] = 0.0
        
        X = df[feature_cols].fillna(0)
        y_classification = df['claim_within_12m']
        y_regression = df['claim_cost']
        
        # Remove users with no trips (all zeros)
        valid_users = X.sum(axis=1) > 0
        X = X[valid_users]
        y_classification = y_classification[valid_users]
        y_regression = y_regression[valid_users]
        
        self.logger.info(f"Prepared data: {X.shape[0]} samples, {X.shape[1]} features")
        self.logger.info(f"Classification target distribution: {y_classification.value_counts().to_dict()}")
        
        return X, y_classification, y_regression
    
    def train_classification_model(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Train classification model for claim probability."""
        self.logger.info("Training classification model...")
        
        # Split data by user to prevent leakage
        user_ids = X.index
        unique_users = user_ids.unique()
        
        train_users, test_users = train_test_split(
            unique_users, test_size=0.2, random_state=42, stratify=None
        )
        
        train_mask = user_ids.isin(train_users)
        test_mask = user_ids.isin(test_users)
        
        X_train, X_test = X[train_mask], X[test_mask]
        y_train, y_test = y[train_mask], y[test_mask]
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train XGBoost classifier
        model = xgb.XGBClassifier(**self.classification_params)
        model.fit(X_train_scaled, y_train)
        
        # Calibrate probabilities
        calibrated_model = CalibratedClassifierCV(model, method='isotonic', cv=3)
        calibrated_model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred_proba = calibrated_model.predict_proba(X_test_scaled)[:, 1]
        y_pred = calibrated_model.predict(X_test_scaled)
        
        metrics = self._calculate_classification_metrics(y_test, y_pred, y_pred_proba)
        
        # Feature importance
        feature_importance = dict(zip(X.columns, model.feature_importances_))
        
        return {
            'model': calibrated_model,
            'scaler': scaler,
            'metrics': metrics,
            'feature_importance': feature_importance,
            'test_predictions': y_pred_proba
        }
    
    def train_regression_model(self, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
        """Train regression model for claim severity."""
        self.logger.info("Training regression model...")
        
        # Filter to only claimants
        claimant_mask = y > 0
        X_claimants = X[claimant_mask]
        y_claimants = y[claimant_mask]
        
        if len(X_claimants) < 10:
            self.logger.warning("Not enough claimants for regression model")
            return self._create_dummy_regression_model()
        
        # Split data
        X_train, X_test, y_train, y_test = train_test_split(
            X_claimants, y_claimants, test_size=0.2, random_state=42
        )
        
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Train XGBoost regressor
        model = xgb.XGBRegressor(**self.regression_params)
        model.fit(X_train_scaled, y_train)
        
        # Evaluate model
        y_pred = model.predict(X_test_scaled)
        
        metrics = self._calculate_regression_metrics(y_test, y_pred)
        
        # Feature importance
        feature_importance = dict(zip(X.columns, model.feature_importances_))
        
        return {
            'model': model,
            'scaler': scaler,
            'metrics': metrics,
            'feature_importance': feature_importance,
            'test_predictions': y_pred
        }
    
    def _create_dummy_regression_model(self) -> Dict[str, Any]:
        """Create a dummy regression model when there's insufficient data."""
        from sklearn.dummy import DummyRegressor
        
        model = DummyRegressor(strategy='mean')
        scaler = StandardScaler()
        
        return {
            'model': model,
            'scaler': scaler,
            'metrics': {'rmse': 0, 'mae': 0, 'r2': 0},
            'feature_importance': {},
            'test_predictions': []
        }
    
    def _calculate_classification_metrics(self, y_true: pd.Series, y_pred: np.ndarray, 
                                         y_pred_proba: np.ndarray) -> Dict[str, float]:
        """Calculate classification metrics."""
        try:
            auc = roc_auc_score(y_true, y_pred_proba)
        except ValueError:
            auc = 0.5  # Default for single class
        
        # Precision-Recall AUC
        try:
            precision, recall, _ = precision_recall_curve(y_true, y_pred_proba)
            pr_auc = np.trapz(precision, recall)
        except ValueError:
            pr_auc = 0.0
        
        # Brier score
        brier_score = np.mean((y_pred_proba - y_true) ** 2)
        
        return {
            'auc': auc,
            'pr_auc': pr_auc,
            'brier_score': brier_score,
            'accuracy': np.mean(y_pred == y_true)
        }
    
    def _calculate_regression_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
        """Calculate regression metrics."""
        rmse = np.sqrt(mean_squared_error(y_true, y_pred))
        mae = mean_absolute_error(y_true, y_pred)
        
        try:
            r2 = r2_score(y_true, y_pred)
        except ValueError:
            r2 = 0.0
        
        return {
            'rmse': rmse,
            'mae': mae,
            'r2': r2
        }
    
    def train_models(self, days_back: int = 90) -> Dict[str, Any]:
        """Train both classification and regression models."""
        self.logger.info("Starting model training...")
        
        # Create feature dataset
        df = self.feature_engineer.create_feature_dataset(days_back)
        
        # Prepare data
        X, y_classification, y_regression = self.prepare_data(df)
        
        # Train models
        classification_results = self.train_classification_model(X, y_classification)
        regression_results = self.train_regression_model(X, y_regression)
        
        # Create model artifacts
        model_version = datetime.now().strftime("%Y%m%d_%H%M%S")
        artifacts = self._save_model_artifacts(
            model_version, classification_results, regression_results, X.columns
        )
        
        self.logger.info("Model training completed successfully")
        
        return {
            'model_version': model_version,
            'classification_metrics': classification_results['metrics'],
            'regression_metrics': regression_results['metrics'],
            'artifacts': artifacts
        }
    
    def _save_model_artifacts(self, model_version: str, classification_results: Dict[str, Any],
                            regression_results: Dict[str, Any], feature_names: List[str]) -> Dict[str, str]:
        """Save model artifacts to disk."""
        # Create model directory
        model_dir = os.path.join(self.models_path, model_version)
        os.makedirs(model_dir, exist_ok=True)
        
        artifacts = {}
        
        # Save classification model
        classification_model_path = os.path.join(model_dir, "classification_model.pkl")
        with open(classification_model_path, "wb") as f:
            pickle.dump(classification_results['model'], f)
        artifacts['classification_model'] = classification_model_path
        
        # Save regression model
        regression_model_path = os.path.join(model_dir, "regression_model.pkl")
        with open(regression_model_path, "wb") as f:
            pickle.dump(regression_results['model'], f)
        artifacts['regression_model'] = regression_model_path
        
        # Save scalers
        classification_scaler_path = os.path.join(model_dir, "classification_scaler.pkl")
        with open(classification_scaler_path, "wb") as f:
            pickle.dump(classification_results['scaler'], f)
        artifacts['classification_scaler'] = classification_scaler_path
        
        regression_scaler_path = os.path.join(model_dir, "regression_scaler.pkl")
        with open(regression_scaler_path, "wb") as f:
            pickle.dump(regression_results['scaler'], f)
        artifacts['regression_scaler'] = regression_scaler_path
        
        # Save feature names
        feature_names_path = os.path.join(model_dir, "feature_names.json")
        with open(feature_names_path, "w") as f:
            json.dump(list(feature_names), f, indent=2)
        artifacts['feature_names'] = feature_names_path
        
        # Save metrics
        metrics = {
            'classification': classification_results['metrics'],
            'regression': regression_results['metrics'],
            'feature_importance': {
                'classification': classification_results['feature_importance'],
                'regression': regression_results['feature_importance']
            },
            'training_date': datetime.now().isoformat(),
            'model_version': model_version
        }
        
        metrics_path = os.path.join(model_dir, "metrics.json")
        with open(metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)
        artifacts['metrics'] = metrics_path
        
        # Save model metadata
        metadata = {
            'model_version': model_version,
            'training_date': datetime.now().isoformat(),
            'feature_count': len(feature_names),
            'classification_params': self.classification_params,
            'regression_params': self.regression_params
        }
        
        metadata_path = os.path.join(model_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)
        artifacts['metadata'] = metadata_path
        
        return artifacts


def main():
    """Main function for training models."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Train Telematics Risk Models")
    parser.add_argument("--days", type=int, default=90, help="Days of data to use for training")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Train models
    trainer = ModelTrainer()
    results = trainer.train_models(args.days)
    
    print(f"Model training completed!")
    print(f"Model version: {results['model_version']}")
    print(f"Classification AUC: {results['classification_metrics']['auc']:.3f}")
    print(f"Regression RMSE: {results['regression_metrics']['rmse']:.2f}")


if __name__ == "__main__":
    main()
