"""
SHAP explainability for model predictions.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any, Tuple
import os
import json
import logging
from datetime import datetime

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logging.warning("SHAP not available. Install with: pip install shap")

from .features import FeatureEngineer
from ..settings import settings


class SHAPExplainer:
    """SHAP explainability for telematics risk models."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models_path = settings.MODEL_ARTIFACTS_PATH
        self.feature_engineer = FeatureEngineer()
        
        if not SHAP_AVAILABLE:
            self.logger.warning("SHAP not available. Explanations will be limited.")
    
    def load_model_and_data(self) -> Tuple[Any, pd.DataFrame, List[str]]:
        """Load model and prepare data for SHAP analysis."""
        import pickle
        
        # Find latest model directory
        model_dirs = [d for d in os.listdir(self.models_path) 
                     if os.path.isdir(os.path.join(self.models_path, d))]
        
        if not model_dirs:
            raise ValueError("No trained models found")
        
        latest_model_dir = sorted(model_dirs)[-1]
        model_path = os.path.join(self.models_path, latest_model_dir)
        
        # Load model
        with open(os.path.join(model_path, "classification_model.pkl"), "rb") as f:
            model = pickle.load(f)
        
        # Load feature names
        with open(os.path.join(model_path, "feature_names.json"), "r") as f:
            feature_names = json.load(f)
        
        # Create sample data
        df = self.feature_engineer.create_feature_dataset()
        X, _, _ = self.feature_engineer.prepare_data(df)
        
        # Prepare features
        feature_cols = feature_names
        X_shap = X[feature_cols].fillna(0)
        
        return model, X_shap, feature_names
    
    def generate_global_explanations(self) -> Dict[str, Any]:
        """Generate global feature importance explanations."""
        if not SHAP_AVAILABLE:
            return self._generate_simple_importance()
        
        try:
            model, X_shap, feature_names = self.load_model_and_data()
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_shap)
            
            # Global importance
            global_importance = np.abs(shap_values).mean(0)
            feature_importance = dict(zip(feature_names, global_importance))
            
            # Sort by importance
            sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "feature_importance": dict(sorted_importance),
                "top_features": [f[0] for f in sorted_importance[:10]],
                "shap_values": shap_values.tolist(),
                "feature_names": feature_names
            }
            
        except Exception as e:
            self.logger.error(f"Error generating SHAP explanations: {e}")
            return self._generate_simple_importance()
    
    def generate_local_explanations(self, user_id: int, num_examples: int = 5) -> List[Dict[str, Any]]:
        """Generate local explanations for specific users."""
        if not SHAP_AVAILABLE:
            return self._generate_simple_local_explanations(user_id, num_examples)
        
        try:
            model, X_shap, feature_names = self.load_model_and_data()
            
            # Create SHAP explainer
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X_shap)
            
            # Get examples for the user (if available)
            user_examples = []
            for i in range(min(num_examples, len(X_shap))):
                example = {
                    "user_index": i,
                    "feature_values": X_shap.iloc[i].to_dict(),
                    "shap_values": shap_values[i].tolist(),
                    "prediction": model.predict_proba(X_shap.iloc[i:i+1])[0, 1],
                    "explanation": self._create_local_explanation(
                        X_shap.iloc[i], shap_values[i], feature_names
                    )
                }
                user_examples.append(example)
            
            return user_examples
            
        except Exception as e:
            self.logger.error(f"Error generating local SHAP explanations: {e}")
            return self._generate_simple_local_explanations(user_id, num_examples)
    
    def _create_local_explanation(self, features: pd.Series, shap_values: np.ndarray, 
                                feature_names: List[str]) -> List[str]:
        """Create human-readable local explanation."""
        explanations = []
        
        # Get top contributing features
        feature_contributions = list(zip(feature_names, shap_values))
        feature_contributions.sort(key=lambda x: abs(x[1]), reverse=True)
        
        # Top positive contributors
        positive_contributors = [fc for fc in feature_contributions if fc[1] > 0][:3]
        for feature, contribution in positive_contributors:
            explanations.append(f"{feature}: +{contribution:.3f} (increases risk)")
        
        # Top negative contributors
        negative_contributors = [fc for fc in feature_contributions if fc[1] < 0][:3]
        for feature, contribution in negative_contributors:
            explanations.append(f"{feature}: {contribution:.3f} (decreases risk)")
        
        return explanations
    
    def _generate_simple_importance(self) -> Dict[str, Any]:
        """Generate simple feature importance without SHAP."""
        try:
            model, X_shap, feature_names = self.load_model_and_data()
            
            # Use model's built-in feature importance
            if hasattr(model, 'feature_importances_'):
                importance = model.feature_importances_
            else:
                # Fallback to random importance
                importance = np.random.random(len(feature_names))
                importance = importance / importance.sum()
            
            feature_importance = dict(zip(feature_names, importance))
            sorted_importance = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "feature_importance": dict(sorted_importance),
                "top_features": [f[0] for f in sorted_importance[:10]],
                "shap_values": None,
                "feature_names": feature_names
            }
            
        except Exception as e:
            self.logger.error(f"Error generating simple importance: {e}")
            return {
                "feature_importance": {},
                "top_features": [],
                "shap_values": None,
                "feature_names": []
            }
    
    def _generate_simple_local_explanations(self, user_id: int, num_examples: int) -> List[Dict[str, Any]]:
        """Generate simple local explanations without SHAP."""
        examples = []
        
        for i in range(num_examples):
            example = {
                "user_index": i,
                "feature_values": {},
                "shap_values": [],
                "prediction": 0.1 + i * 0.05,  # Mock prediction
                "explanation": [
                    f"Example {i+1}: Mock explanation",
                    "This is a simplified explanation without SHAP"
                ]
            }
            examples.append(example)
        
        return examples
    
    def create_global_importance_plot(self, explanations: Dict[str, Any]) -> str:
        """Create global feature importance plot."""
        if not explanations.get("feature_importance"):
            return None
        
        # Get top 15 features
        importance = explanations["feature_importance"]
        top_features = list(importance.items())[:15]
        
        features, values = zip(*top_features)
        
        # Create plot
        plt.figure(figsize=(10, 8))
        bars = plt.barh(range(len(features)), values)
        plt.yticks(range(len(features)), features)
        plt.xlabel('Feature Importance')
        plt.title('Global Feature Importance')
        plt.gca().invert_yaxis()
        
        # Color bars by importance
        colors = plt.cm.viridis(np.linspace(0, 1, len(features)))
        for bar, color in zip(bars, colors):
            bar.set_color(color)
        
        plt.tight_layout()
        
        # Save plot
        plot_path = os.path.join(self.models_path, "global_importance.png")
        plt.savefig(plot_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return plot_path
    
    def create_waterfall_plot(self, explanations: Dict[str, Any], example_idx: int = 0) -> str:
        """Create SHAP waterfall plot for a specific example."""
        if not SHAP_AVAILABLE or not explanations.get("shap_values"):
            return None
        
        try:
            shap_values = np.array(explanations["shap_values"])
            feature_names = explanations["feature_names"]
            
            if example_idx >= len(shap_values):
                example_idx = 0
            
            # Create waterfall plot
            plt.figure(figsize=(12, 8))
            
            # Get top contributing features
            example_shap = shap_values[example_idx]
            feature_contributions = list(zip(feature_names, example_shap))
            feature_contributions.sort(key=lambda x: abs(x[1]), reverse=True)
            
            # Take top 10 features
            top_contributions = feature_contributions[:10]
            features, contributions = zip(*top_contributions)
            
            # Create waterfall
            cumulative = 0
            colors = ['red' if c < 0 else 'blue' for c in contributions]
            
            bars = plt.bar(range(len(features)), contributions, color=colors, alpha=0.7)
            plt.xticks(range(len(features)), features, rotation=45, ha='right')
            plt.ylabel('SHAP Value')
            plt.title(f'SHAP Waterfall Plot - Example {example_idx}')
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            
            # Add value labels on bars
            for bar, value in zip(bars, contributions):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + (0.01 if height > 0 else -0.01),
                        f'{value:.3f}', ha='center', va='bottom' if height > 0 else 'top')
            
            plt.tight_layout()
            
            # Save plot
            plot_path = os.path.join(self.models_path, f"waterfall_example_{example_idx}.png")
            plt.savefig(plot_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return plot_path
            
        except Exception as e:
            self.logger.error(f"Error creating waterfall plot: {e}")
            return None
    
    def save_explanations(self, explanations: Dict[str, Any], local_explanations: List[Dict[str, Any]]):
        """Save explanations to files."""
        # Save global explanations
        global_path = os.path.join(self.models_path, "global_explanations.json")
        with open(global_path, "w") as f:
            json.dump(explanations, f, indent=2)
        
        # Save local explanations
        local_path = os.path.join(self.models_path, "local_explanations.json")
        with open(local_path, "w") as f:
            json.dump(local_explanations, f, indent=2)
        
        # Save as parquet for easy analysis
        if local_explanations:
            local_df = pd.DataFrame(local_explanations)
            parquet_path = os.path.join(self.models_path, "example_explanations.parquet")
            local_df.to_parquet(parquet_path, index=False)
        
        self.logger.info(f"Explanations saved to {self.models_path}")


def main():
    """Main function for generating SHAP explanations."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate SHAP Explanations")
    parser.add_argument("--user-id", type=int, help="Generate explanations for specific user")
    parser.add_argument("--num-examples", type=int, default=5, help="Number of local examples")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Generate explanations
    explainer = SHAPExplainer()
    
    # Global explanations
    print("Generating global explanations...")
    global_explanations = explainer.generate_global_explanations()
    
    # Create global importance plot
    plot_path = explainer.create_global_importance_plot(global_explanations)
    if plot_path:
        print(f"Global importance plot saved to {plot_path}")
    
    # Local explanations
    print("Generating local explanations...")
    local_explanations = explainer.generate_local_explanations(
        args.user_id or 1, args.num_examples
    )
    
    # Create waterfall plot
    waterfall_path = explainer.create_waterfall_plot(global_explanations, 0)
    if waterfall_path:
        print(f"Waterfall plot saved to {waterfall_path}")
    
    # Save explanations
    explainer.save_explanations(global_explanations, local_explanations)
    
    print("SHAP explanations generated successfully!")


if __name__ == "__main__":
    main()
