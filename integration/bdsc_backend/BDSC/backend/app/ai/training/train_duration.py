"""Training script for Job Duration Prediction (Model 1 - Highest Priority)."""

from __future__ import annotations

import os
os.environ["OMP_NUM_THREADS"] = "1"

import json
from datetime import datetime, timezone
import joblib
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.ai.config import METRICS_DIR, MODELS_DIR, ai_config
from app.ai.data_prep import create_duration_preprocessor, generate_synthetic_historical_dataset


def train_duration_model(n_samples: int = 1500) -> dict:
    """Train baseline Linear Regression, Random Forest, and HistGradientBoosting regressors.

    Selects the best performing model based on validation MAE and saves the artifact.
    """
    print(f"Generating {n_samples} historical training records for Job Duration Prediction...")
    df = generate_synthetic_historical_dataset(n_samples=n_samples, random_seed=ai_config.random_seed)

    feature_cols = [
        "job_type",
        "priority",
        "service_zone",
        "customer_type",
        "skill_count",
        "window_span_min",
        "estimated_duration_min",
        "hour_of_day",
        "day_of_week",
    ]
    target_col = "actual_duration_min"

    X = df[feature_cols]
    y = df[target_col].values

    # 80/20 train/test split with fixed random state for reproducibility
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=ai_config.random_seed
    )

    preprocessor = create_duration_preprocessor()

    candidates = {
        "LinearRegression (Baseline)": LinearRegression(),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=100, max_depth=12, random_state=ai_config.random_seed
        ),
        "HistGradientBoostingRegressor": HistGradientBoostingRegressor(
            max_iter=100, max_depth=8, random_state=ai_config.random_seed
        ),
    }

    results = {}
    best_model_name = None
    best_mae = float("inf")
    best_pipeline = None

    for name, regressor in candidates.items():
        pipeline = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", regressor),
        ])
        pipeline.fit(X_train, y_train)
        y_pred = pipeline.predict(X_test)

        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        r2 = float(r2_score(y_test, y_pred))

        results[name] = {"MAE": round(mae, 2), "RMSE": round(rmse, 2), "R2": round(r2, 4)}
        print(f"  -> {name:32s} | MAE: {mae:.2f} min | RMSE: {rmse:.2f} min | R²: {r2:.4f}")

        if mae < best_mae:
            best_mae = mae
            best_model_name = name
            best_pipeline = pipeline

    # Compute empirical prediction residual standard deviation for prediction intervals
    y_train_pred = best_pipeline.predict(X_train)
    residual_std = float(np.std(y_train - y_train_pred))

    metadata = {
        "model_name": best_model_name,
        "model_type": "job_duration_regressor",
        "version": "1.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "target_variable": target_col,
        "feature_columns": feature_cols,
        "residual_std": round(residual_std, 2),
        "metrics": results[best_model_name],
        "all_candidate_metrics": results,
        "data_provenance": "SYNTHETIC_AUGMENTED",
    }

    # Save artifact containing pipeline and inference metadata
    artifact_payload = {
        "pipeline": best_pipeline,
        "metadata": metadata,
    }
    model_path = MODELS_DIR / ai_config.duration_model_filename
    joblib.dump(artifact_payload, model_path)
    print(f"[OK] Saved best model ({best_model_name}) to {model_path}")

    # Save metrics JSON
    metrics_path = METRICS_DIR / "duration_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


if __name__ == "__main__":
    train_duration_model()
