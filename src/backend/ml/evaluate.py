"""
Model evaluation and reporting.
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Any
import os
import json
import logging
from datetime import datetime

from sklearn.metrics import (
    roc_curve, precision_recall_curve, calibration_curve,
    confusion_matrix, classification_report
)
from sklearn.calibration import CalibratedClassifierCV

from .features import FeatureEngineer
from ..settings import settings


class ModelEvaluator:
    """Model evaluation and reporting."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.models_path = settings.MODEL_ARTIFACTS_PATH
        self.feature_engineer = FeatureEngineer()
    
    def load_latest_model(self) -> Dict[str, Any]:
        """Load the latest trained model."""
        # Find latest model directory
        model_dirs = [d for d in os.listdir(self.models_path) 
                     if os.path.isdir(os.path.join(self.models_path, d))]
        
        if not model_dirs:
            raise ValueError("No trained models found")
        
        latest_model_dir = sorted(model_dirs)[-1]
        model_path = os.path.join(self.models_path, latest_model_dir)
        
        # Load model artifacts
        import pickle
        
        with open(os.path.join(model_path, "classification_model.pkl"), "rb") as f:
            classification_model = pickle.load(f)
        
        with open(os.path.join(model_path, "regression_model.pkl"), "rb") as f:
            regression_model = pickle.load(f)
        
        with open(os.path.join(model_path, "classification_scaler.pkl"), "rb") as f:
            classification_scaler = pickle.load(f)
        
        with open(os.path.join(model_path, "regression_scaler.pkl"), "rb") as f:
            regression_scaler = pickle.load(f)
        
        with open(os.path.join(model_path, "feature_names.json"), "r") as f:
            feature_names = json.load(f)
        
        with open(os.path.join(model_path, "metrics.json"), "r") as f:
            metrics = json.load(f)
        
        return {
            'model_version': latest_model_dir,
            'classification_model': classification_model,
            'regression_model': regression_model,
            'classification_scaler': classification_scaler,
            'regression_scaler': regression_scaler,
            'feature_names': feature_names,
            'metrics': metrics
        }
    
    def evaluate_model(self, model_version: str = None) -> Dict[str, Any]:
        """Evaluate model performance."""
        if model_version:
            model_path = os.path.join(self.models_path, model_version)
        else:
            model_artifacts = self.load_latest_model()
            model_path = os.path.join(self.models_path, model_artifacts['model_version'])
        
        # Load test data
        df = self.feature_engineer.create_feature_dataset()
        X, y_classification, y_regression = self.feature_engineer.prepare_data(df)
        
        # Load model
        model_artifacts = self.load_latest_model()
        
        # Prepare features
        feature_cols = model_artifacts['feature_names']
        X_eval = X[feature_cols].fillna(0)
        
        # Scale features
        X_classification_scaled = model_artifacts['classification_scaler'].transform(X_eval)
        X_regression_scaled = model_artifacts['regression_scaler'].transform(X_eval)
        
        # Get predictions
        y_pred_proba = model_artifacts['classification_model'].predict_proba(X_classification_scaled)[:, 1]
        y_pred_class = model_artifacts['classification_model'].predict(X_classification_scaled)
        
        # Regression predictions (only for claimants)
        claimant_mask = y_regression > 0
        if claimant_mask.sum() > 0:
            y_pred_regression = model_artifacts['regression_model'].predict(X_regression_scaled[claimant_mask])
        else:
            y_pred_regression = np.array([])
        
        # Calculate metrics
        classification_metrics = self._calculate_classification_metrics(
            y_classification, y_pred_class, y_pred_proba
        )
        
        regression_metrics = self._calculate_regression_metrics(
            y_regression[claimant_mask], y_pred_regression
        )
        
        # Generate plots
        plots = self._generate_evaluation_plots(
            y_classification, y_pred_proba, y_regression[claimant_mask], y_pred_regression
        )
        
        return {
            'model_version': model_artifacts['model_version'],
            'classification_metrics': classification_metrics,
            'regression_metrics': regression_metrics,
            'plots': plots,
            'feature_importance': model_artifacts['metrics']['feature_importance']
        }
    
    def _calculate_classification_metrics(self, y_true: pd.Series, y_pred: np.ndarray, 
                                        y_pred_proba: np.ndarray) -> Dict[str, Any]:
        """Calculate comprehensive classification metrics."""
        from sklearn.metrics import roc_auc_score, precision_recall_curve, roc_curve
        
        # Basic metrics
        try:
            auc = roc_auc_score(y_true, y_pred_proba)
        except ValueError:
            auc = 0.5
        
        # Precision-Recall curve
        precision, recall, pr_thresholds = precision_recall_curve(y_true, y_pred_proba)
        pr_auc = np.trapz(precision, recall)
        
        # ROC curve
        fpr, tpr, roc_thresholds = roc_curve(y_true, y_pred_proba)
        
        # Calibration
        fraction_of_positives, mean_predicted_value = calibration_curve(
            y_true, y_pred_proba, n_bins=10
        )
        
        # Brier score
        brier_score = np.mean((y_pred_proba - y_true) ** 2)
        
        # Confusion matrix
        cm = confusion_matrix(y_true, y_pred)
        
        return {
            'auc': auc,
            'pr_auc': pr_auc,
            'brier_score': brier_score,
            'accuracy': np.mean(y_pred == y_true),
            'precision': np.mean(y_pred[y_pred == 1] == y_true[y_pred == 1]) if np.sum(y_pred) > 0 else 0,
            'recall': np.mean(y_true[y_pred == 1]) if np.sum(y_pred) > 0 else 0,
            'f1_score': 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0,
            'calibration_curve': {
                'fraction_of_positives': fraction_of_positives.tolist(),
                'mean_predicted_value': mean_predicted_value.tolist()
            },
            'roc_curve': {
                'fpr': fpr.tolist(),
                'tpr': tpr.tolist()
            },
            'pr_curve': {
                'precision': precision.tolist(),
                'recall': recall.tolist()
            },
            'confusion_matrix': cm.tolist()
        }
    
    def _calculate_regression_metrics(self, y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, Any]:
        """Calculate regression metrics."""
        if len(y_true) == 0 or len(y_pred) == 0:
            return {'rmse': 0, 'mae': 0, 'r2': 0, 'mape': 0}
        
        rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
        mae = np.mean(np.abs(y_true - y_pred))
        
        try:
            r2 = 1 - np.sum((y_true - y_pred) ** 2) / np.sum((y_true - np.mean(y_true)) ** 2)
        except ZeroDivisionError:
            r2 = 0
        
        mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100 if np.sum(y_true) > 0 else 0
        
        return {
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'mape': mape
        }
    
    def _generate_evaluation_plots(self, y_classification: pd.Series, y_pred_proba: np.ndarray,
                                 y_regression: pd.Series, y_pred_regression: np.ndarray) -> Dict[str, str]:
        """Generate evaluation plots."""
        plots = {}
        
        # Set style
        plt.style.use('seaborn-v0_8')
        
        # 1. ROC Curve
        fig, ax = plt.subplots(figsize=(8, 6))
        fpr, tpr, _ = roc_curve(y_classification, y_pred_proba)
        ax.plot(fpr, tpr, label=f'ROC Curve (AUC = {roc_auc_score(y_classification, y_pred_proba):.3f})')
        ax.plot([0, 1], [0, 1], 'k--', label='Random')
        ax.set_xlabel('False Positive Rate')
        ax.set_ylabel('True Positive Rate')
        ax.set_title('ROC Curve')
        ax.legend()
        ax.grid(True)
        
        roc_path = os.path.join(self.models_path, "roc_curve.png")
        plt.savefig(roc_path, dpi=300, bbox_inches='tight')
        plt.close()
        plots['roc_curve'] = roc_path
        
        # 2. Precision-Recall Curve
        fig, ax = plt.subplots(figsize=(8, 6))
        precision, recall, _ = precision_recall_curve(y_classification, y_pred_proba)
        ax.plot(recall, precision, label=f'PR Curve (AUC = {np.trapz(precision, recall):.3f})')
        ax.set_xlabel('Recall')
        ax.set_ylabel('Precision')
        ax.set_title('Precision-Recall Curve')
        ax.legend()
        ax.grid(True)
        
        pr_path = os.path.join(self.models_path, "pr_curve.png")
        plt.savefig(pr_path, dpi=300, bbox_inches='tight')
        plt.close()
        plots['pr_curve'] = pr_path
        
        # 3. Calibration Curve
        fig, ax = plt.subplots(figsize=(8, 6))
        fraction_of_positives, mean_predicted_value = calibration_curve(
            y_classification, y_pred_proba, n_bins=10
        )
        ax.plot(mean_predicted_value, fraction_of_positives, 'o-', label='Model')
        ax.plot([0, 1], [0, 1], 'k--', label='Perfect Calibration')
        ax.set_xlabel('Mean Predicted Probability')
        ax.set_ylabel('Fraction of Positives')
        ax.set_title('Calibration Curve')
        ax.legend()
        ax.grid(True)
        
        cal_path = os.path.join(self.models_path, "calibration_curve.png")
        plt.savefig(cal_path, dpi=300, bbox_inches='tight')
        plt.close()
        plots['calibration_curve'] = cal_path
        
        # 4. Regression Scatter Plot
        if len(y_regression) > 0 and len(y_pred_regression) > 0:
            fig, ax = plt.subplots(figsize=(8, 6))
            ax.scatter(y_regression, y_pred_regression, alpha=0.6)
            ax.plot([y_regression.min(), y_regression.max()], 
                   [y_regression.min(), y_regression.max()], 'r--', lw=2)
            ax.set_xlabel('Actual Claim Cost')
            ax.set_ylabel('Predicted Claim Cost')
            ax.set_title('Regression Predictions vs Actual')
            ax.grid(True)
            
            reg_path = os.path.join(self.models_path, "regression_scatter.png")
            plt.savefig(reg_path, dpi=300, bbox_inches='tight')
            plt.close()
            plots['regression_scatter'] = reg_path
        
        return plots
    
    def generate_report(self, evaluation_results: Dict[str, Any]) -> str:
        """Generate evaluation report."""
        report_lines = []
        
        report_lines.append("# Model Evaluation Report")
        report_lines.append(f"**Model Version:** {evaluation_results['model_version']}")
        report_lines.append(f"**Evaluation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")
        
        # Classification metrics
        report_lines.append("## Classification Metrics")
        cm = evaluation_results['classification_metrics']
        report_lines.append(f"- **AUC:** {cm['auc']:.3f}")
        report_lines.append(f"- **PR-AUC:** {cm['pr_auc']:.3f}")
        report_lines.append(f"- **Brier Score:** {cm['brier_score']:.3f}")
        report_lines.append(f"- **Accuracy:** {cm['accuracy']:.3f}")
        report_lines.append(f"- **Precision:** {cm['precision']:.3f}")
        report_lines.append(f"- **Recall:** {cm['recall']:.3f}")
        report_lines.append(f"- **F1-Score:** {cm['f1_score']:.3f}")
        report_lines.append("")
        
        # Regression metrics
        report_lines.append("## Regression Metrics")
        rm = evaluation_results['regression_metrics']
        report_lines.append(f"- **RMSE:** ${rm['rmse']:.2f}")
        report_lines.append(f"- **MAE:** ${rm['mae']:.2f}")
        report_lines.append(f"- **R²:** {rm['r2']:.3f}")
        report_lines.append(f"- **MAPE:** {rm['mape']:.1f}%")
        report_lines.append("")
        
        # Feature importance
        report_lines.append("## Top 10 Feature Importance (Classification)")
        classification_importance = evaluation_results['feature_importance']['classification']
        sorted_features = sorted(classification_importance.items(), key=lambda x: x[1], reverse=True)
        
        for feature, importance in sorted_features[:10]:
            report_lines.append(f"- **{feature}:** {importance:.3f}")
        
        report_lines.append("")
        
        # Plots
        report_lines.append("## Evaluation Plots")
        for plot_name, plot_path in evaluation_results['plots'].items():
            report_lines.append(f"- [{plot_name}]({plot_path})")
        
        report_lines.append("")
        
        # Model performance summary
        report_lines.append("## Performance Summary")
        if cm['auc'] > 0.7:
            report_lines.append("✅ **Good classification performance** (AUC > 0.7)")
        elif cm['auc'] > 0.6:
            report_lines.append("⚠️ **Moderate classification performance** (AUC > 0.6)")
        else:
            report_lines.append("❌ **Poor classification performance** (AUC < 0.6)")
        
        if rm['r2'] > 0.3:
            report_lines.append("✅ **Good regression performance** (R² > 0.3)")
        elif rm['r2'] > 0.1:
            report_lines.append("⚠️ **Moderate regression performance** (R² > 0.1)")
        else:
            report_lines.append("❌ **Poor regression performance** (R² < 0.1)")
        
        return "\n".join(report_lines)
    
    def save_report(self, report: str, model_version: str = None):
        """Save evaluation report."""
        if model_version:
            report_path = os.path.join(self.models_path, model_version, "evaluation_report.md")
        else:
            model_artifacts = self.load_latest_model()
            report_path = os.path.join(self.models_path, model_artifacts['model_version'], "evaluation_report.md")
        
        with open(report_path, "w") as f:
            f.write(report)
        
        self.logger.info(f"Evaluation report saved to {report_path}")


def main():
    """Main function for model evaluation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Evaluate Telematics Risk Models")
    parser.add_argument("--model-version", type=str, help="Specific model version to evaluate")
    
    args = parser.parse_args()
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Evaluate model
    evaluator = ModelEvaluator()
    results = evaluator.evaluate_model(args.model_version)
    
    # Generate and save report
    report = evaluator.generate_report(results)
    evaluator.save_report(report, args.model_version)
    
    print("Model evaluation completed!")
    print(f"Classification AUC: {results['classification_metrics']['auc']:.3f}")
    print(f"Regression RMSE: ${results['regression_metrics']['rmse']:.2f}")


if __name__ == "__main__":
    main()
