"""Reusable feature engineering and transformation pipelines for DispatchGrid AI."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.impute import SimpleImputer


# ============================================================================
# 1. DURATION PREDICTION FEATURE PIPELINE
# ============================================================================

DURATION_CATEGORICAL_FEATURES = ["job_type", "priority", "service_zone", "customer_type"]
DURATION_NUMERIC_FEATURES = [
    "skill_count",
    "window_span_min",
    "estimated_duration_min",
    "hour_of_day",
    "day_of_week",
]

def create_duration_preprocessor() -> ColumnTransformer:
    """Prepares features for the Job Duration Regressor."""
    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, DURATION_NUMERIC_FEATURES),
            ("cat", categorical_transformer, DURATION_CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return preprocessor


# ============================================================================
# 2. SLA DELAY RISK FEATURE PIPELINE
# ============================================================================

DELAY_CATEGORICAL_FEATURES = ["job_type", "priority", "service_zone"]
DELAY_NUMERIC_FEATURES = [
    "predicted_duration_min",
    "sla_slack_min",
    "estimated_travel_min",
    "duration_to_slack_ratio",
    "buffer_slack_min",
]

def engineer_delay_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived ratio and margin features for delay prediction."""
    df = df.copy()
    if "predicted_duration_min" not in df.columns:
        df["predicted_duration_min"] = df.get("estimated_duration_min", 90.0)

    if "sla_slack_min" not in df.columns:
        if "sla_deadline_min" in df.columns and "window_start_min" in df.columns:
            df["sla_slack_min"] = df["sla_deadline_min"] - df["window_start_min"]
        else:
            df["sla_slack_min"] = 180.0

    if "estimated_travel_min" not in df.columns:
        df["estimated_travel_min"] = 25.0

    # Avoid division by zero
    slack_safe = np.maximum(df["sla_slack_min"].values, 1.0)
    df["duration_to_slack_ratio"] = df["predicted_duration_min"] / slack_safe
    df["buffer_slack_min"] = df["sla_slack_min"] - (df["predicted_duration_min"] + df["estimated_travel_min"])
    return df

def create_delay_preprocessor() -> ColumnTransformer:
    """Prepares features for the SLA Delay Classifier."""
    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, DELAY_NUMERIC_FEATURES),
            ("cat", categorical_transformer, DELAY_CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return preprocessor


# ============================================================================
# 3. DISRUPTION RISK FEATURE PIPELINE
# ============================================================================

DISRUPTION_CATEGORICAL_FEATURES = ["job_priority", "service_zone"]
DISRUPTION_NUMERIC_FEATURES = [
    "technician_workload_hours",
    "tight_buffer_count",
    "estimated_duration_min",
    "overwork_index",
]

def engineer_disruption_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute derived workload strain metrics."""
    df = df.copy()
    if "job_priority" not in df.columns and "priority" in df.columns:
        df["job_priority"] = df["priority"]

    if "technician_workload_hours" not in df.columns:
        df["technician_workload_hours"] = 6.0

    if "tight_buffer_count" not in df.columns:
        df["tight_buffer_count"] = 0

    if "estimated_duration_min" not in df.columns:
        df["estimated_duration_min"] = 90.0

    df["overwork_index"] = np.maximum(0.0, df["technician_workload_hours"] - 8.0)
    return df

def create_disruption_preprocessor() -> ColumnTransformer:
    """Prepares features for the Disruption Risk Classifier."""
    numeric_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
    ])

    categorical_transformer = Pipeline(steps=[
        ("imputer", SimpleImputer(strategy="most_frequent")),
        ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
    ])

    preprocessor = ColumnTransformer(
        transformers=[
            ("num", numeric_transformer, DISRUPTION_NUMERIC_FEATURES),
            ("cat", categorical_transformer, DISRUPTION_CATEGORICAL_FEATURES),
        ],
        remainder="drop",
    )
    return preprocessor

