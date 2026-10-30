"""Training script for Electrical Service Demand Forecasting (Model 3)."""

from __future__ import annotations

import os
os.environ["OMP_NUM_THREADS"] = "1"

import json
from datetime import datetime, timezone
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from app.ai.config import METRICS_DIR, MODELS_DIR, ai_config


def generate_demand_time_series(days: int = 180, random_seed: int = ai_config.random_seed) -> pd.DataFrame:
    """Generate chronological daily electrical service demand per zone."""
    rng = np.random.default_rng(random_seed)
    zones = ["Central", "North", "South", "East", "West"]

    # Base daily rates per zone
    zone_base = {
        "Central": 16.0,
        "North": 11.0,
        "South": 10.0,
        "East": 8.0,
        "West": 7.0,
    }

    records = []
    for day_idx in range(days):
        day_of_week = day_idx % 7  # 0=Mon, ..., 6=Sun
        is_weekend = 1 if day_of_week in [5, 6] else 0

        # Weekend residential uptick vs commercial slowdown
        weekend_mult = 0.85 if is_weekend else 1.05

        # Monthly seasonal cycle (e.g. monsoon electrical outages in months 5-8)
        season_mult = 1.0 + 0.15 * np.sin(2 * np.pi * day_idx / 120.0)

        for z in zones:
            base = zone_base[z] * weekend_mult * season_mult
            noise = rng.normal(0, np.sqrt(base) * 0.7)
            # Occasional spike (e.g. storm outage)
            if rng.random() < 0.05:
                noise += rng.uniform(4.0, 10.0)

            daily_count = float(max(1.0, np.round(base + noise, 1)))

            records.append({
                "day_idx": day_idx,
                "service_zone": z,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "season_sin": float(np.sin(2 * np.pi * day_idx / 120.0)),
                "season_cos": float(np.cos(2 * np.pi * day_idx / 120.0)),
                "daily_job_count": daily_count,
            })

    df = pd.DataFrame(records)
    # Add rolling 7-day average per zone (preventing lookahead by shifting)
    df["rolling_avg_7d"] = (
        df.groupby("service_zone")["daily_job_count"]
        .shift(1)
        .rolling(window=7, min_periods=1)
        .mean()
        .fillna(df["daily_job_count"].mean())
    )
    return df


def train_demand_model(days: int = 180) -> dict:
    """Train demand forecasting models on chronological time-series splits."""
    print(f"Generating {days} days of multi-zone electrical service demand data...")
    df = generate_demand_time_series(days=days, random_seed=ai_config.random_seed)

    feature_cols = [
        "service_zone",
        "day_of_week",
        "is_weekend",
        "season_sin",
        "season_cos",
        "rolling_avg_7d",
    ]
    target_col = "daily_job_count"

    # Strictly chronological train/test split: first 80% of days for training, last 20% for testing
    split_day = int(days * 0.80)
    train_mask = df["day_idx"] < split_day
    test_mask = df["day_idx"] >= split_day

    X_train = df.loc[train_mask, feature_cols]
    y_train = df.loc[train_mask, target_col].values
    X_test = df.loc[test_mask, feature_cols]
    y_test = df.loc[test_mask, target_col].values

    preprocessor = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), ["service_zone"]),
            ("num", StandardScaler(), ["day_of_week", "is_weekend", "season_sin", "season_cos", "rolling_avg_7d"]),
        ]
    )

    candidates = {
        "Ridge (Baseline)": Ridge(alpha=1.0),
        "RandomForestRegressor": RandomForestRegressor(
            n_estimators=100, max_depth=6, random_state=ai_config.random_seed
        ),
        "HistGradientBoostingRegressor": HistGradientBoostingRegressor(
            max_iter=100, max_depth=5, random_state=ai_config.random_seed
        ),
    }

    results = {}
    best_model_name = None
    best_wape = float("inf")
    best_pipeline = None

    for name, regressor in candidates.items():
        pipeline = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", regressor),
        ])
        pipeline.fit(X_train, y_train)

        y_pred = np.maximum(0.0, pipeline.predict(X_test))

        mae = float(mean_absolute_error(y_test, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
        wape = float(np.sum(np.abs(y_test - y_pred)) / np.sum(y_test))

        results[name] = {"MAE": round(mae, 2), "RMSE": round(rmse, 2), "WAPE": round(wape, 4)}
        print(f"  -> {name:32s} | MAE: {mae:.2f} jobs | RMSE: {rmse:.2f} | WAPE: {wape * 100:.2f}%")

        if wape < best_wape:
            best_wape = wape
            best_model_name = name
            best_pipeline = pipeline

    # Zone baseline means for quick reference
    zone_means = df.groupby("service_zone")["daily_job_count"].mean().to_dict()

    metadata = {
        "model_name": best_model_name,
        "model_type": "demand_forecaster",
        "version": "1.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_days": split_day,
        "test_days": days - split_day,
        "target_variable": target_col,
        "feature_columns": feature_cols,
        "zone_baseline_means": {k: round(v, 2) for k, v in zone_means.items()},
        "metrics": results[best_model_name],
        "all_candidate_metrics": results,
        "data_provenance": "SYNTHETIC_AUGMENTED",
    }

    artifact_payload = {
        "pipeline": best_pipeline,
        "metadata": metadata,
    }
    model_path = MODELS_DIR / ai_config.demand_model_filename
    joblib.dump(artifact_payload, model_path)
    print(f"[OK] Saved best model ({best_model_name}) to {model_path}")

    metrics_path = METRICS_DIR / "demand_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


if __name__ == "__main__":
    train_demand_model()
