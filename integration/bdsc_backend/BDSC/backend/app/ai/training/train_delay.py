"""Training script for SLA Delay Risk Prediction (Model 2)."""

from __future__ import annotations

import os
os.environ["OMP_NUM_THREADS"] = "1"

import json
from datetime import datetime, timezone
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from app.ai.config import METRICS_DIR, MODELS_DIR, ai_config
from app.ai.data_prep import (
    create_delay_preprocessor,
    engineer_delay_features,
    generate_synthetic_historical_dataset,
)


def train_delay_model(n_samples: int = 1500) -> dict:
    """Train baseline Logistic Regression, Random Forest, and HistGradientBoosting classifiers for SLA delay."""
    print(f"Generating {n_samples} historical training records for SLA Delay Risk Prediction...")
    raw_df = generate_synthetic_historical_dataset(n_samples=n_samples, random_seed=ai_config.random_seed)
    df = engineer_delay_features(raw_df)

    feature_cols = [
        "job_type",
        "priority",
        "service_zone",
        "predicted_duration_min",
        "sla_slack_min",
        "estimated_travel_min",
        "duration_to_slack_ratio",
        "buffer_slack_min",
    ]
    target_col = "sla_delayed"

    X = df[feature_cols]
    y = df[target_col].values

    # Stratified 80/20 train/test split to preserve delay positive rate
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=ai_config.random_seed, stratify=y
    )

    preprocessor = create_delay_preprocessor()

    candidates = {
        "LogisticRegression (Baseline)": LogisticRegression(max_iter=1000, random_state=ai_config.random_seed),
        "RandomForestClassifier": RandomForestClassifier(
            n_estimators=100, max_depth=8, random_state=ai_config.random_seed
        ),
        "HistGradientBoostingClassifier": HistGradientBoostingClassifier(
            max_iter=100, max_depth=6, random_state=ai_config.random_seed
        ),
    }

    results = {}
    best_model_name = None
    best_f1 = -1.0
    best_pipeline = None

    for name, classifier in candidates.items():
        pipeline = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ])
        pipeline.fit(X_train, y_train)

        y_pred = pipeline.predict(X_test)
        y_prob = pipeline.predict_proba(X_test)[:, 1]

        precision = float(precision_score(y_test, y_pred, zero_division=0))
        recall = float(recall_score(y_test, y_pred, zero_division=0))
        f1 = float(f1_score(y_test, y_pred, zero_division=0))
        roc_auc = float(roc_auc_score(y_test, y_prob))
        pr_auc = float(average_precision_score(y_test, y_prob))

        results[name] = {
            "Precision": round(precision, 4),
            "Recall": round(recall, 4),
            "F1": round(f1, 4),
            "ROC_AUC": round(roc_auc, 4),
            "PR_AUC": round(pr_auc, 4),
        }
        print(f"  -> {name:32s} | F1: {f1:.4f} | Recall: {recall:.4f} | Precision: {precision:.4f} | ROC-AUC: {roc_auc:.4f}")

        if f1 > best_f1:
            best_f1 = f1
            best_model_name = name
            best_pipeline = pipeline

    metadata = {
        "model_name": best_model_name,
        "model_type": "sla_delay_classifier",
        "version": "1.0.0",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_samples": len(X_train),
        "test_samples": len(X_test),
        "target_variable": target_col,
        "feature_columns": feature_cols,
        "metrics": results[best_model_name],
        "all_candidate_metrics": results,
        "data_provenance": "SYNTHETIC_AUGMENTED",
    }

    artifact_payload = {
        "pipeline": best_pipeline,
        "metadata": metadata,
    }
    model_path = MODELS_DIR / ai_config.delay_model_filename
    joblib.dump(artifact_payload, model_path)
    print(f"[OK] Saved best model ({best_model_name}) to {model_path}")

    metrics_path = METRICS_DIR / "delay_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return metadata


if __name__ == "__main__":
    train_delay_model()
