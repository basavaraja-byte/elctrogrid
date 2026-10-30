# DispatchGrid — AI Implementation Guide

This guide describes how each component of the AI layer is implemented, how code is structured, and how the models interact with the backend and frontend.

---

## 1. Directory Structure

The AI layer is organized cleanly inside `integration/bdsc_backend/BDSC/backend/app/ai/`:

```
app/ai/
├── __init__.py                # Package exports (ai_router, ai_service, ExplanationService)
├── config.py                  # Thresholds, fallback defaults, artifact directory paths
├── schemas.py                 # Pydantic request and response schemas
├── data_prep/                 # Data loading and feature transformation
│   ├── __init__.py
│   ├── dataset_loader.py      # Loads benchmark CSVs and SQLite operational records
│   ├── feature_engineering.py # Scikit-learn ColumnTransformers and Pipelines
│   └── synthetic_generator.py # Physical electrical domain dataset generator (SYNTHETIC_AUGMENTED)
├── training/                  # Reproducible training scripts
│   ├── __init__.py
│   ├── train_duration.py      # Trains duration regressors (LR, RF, HistGBDT)
│   ├── train_delay.py         # Trains SLA delay classifiers (Logistic, RF, HistGBDT)
│   ├── train_demand.py        # Trains zone demand forecaster (Ridge, RF, HistGBDT)
│   ├── train_disruption.py    # Trains disruption risk classifier (HistGBDT)
│   └── train_all.py           # Master training script
├── services/                  # Runtime business logic
│   ├── __init__.py
│   ├── explanation_service.py # Generates human-readable localized explanations
│   └── prediction_service.py  # Thread-safe cached inference engine with fallback
├── api/                       # REST endpoints
│   ├── __init__.py
│   └── routes.py              # FastAPI APIRouter mounted at /api/v1/ai
└── artifacts/                 # Serialized models and metrics
    ├── models/                # *.joblib model pipelines
    └── metrics/               # *.json evaluation reports
```

---

## 2. Model 1 Implementation: Job Duration Prediction

- **File:** `app/ai/training/train_duration.py`
- **Features Used:**
  - `job_type`: Categorical (e.g. residential_wiring, commercial_wiring, safety_inspection)
  - `priority`: Categorical (Low, Normal, High, Critical)
  - `service_zone`: Categorical (Central, North, South, East, West)
  - `customer_type`: Categorical (individual, commercial)
  - `skill_count`: Numeric count of required certified skills
  - `window_span_min`: Numeric width of the appointment window
  - `estimated_duration_min`: Customer-submitted initial guess
  - `hour_of_day`, `day_of_week`: Chronological features
- **Pipeline:**
  ```python
  preprocessor = ColumnTransformer(transformers=[
      ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), numeric_features),
      ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")), ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical_features),
  ])
  pipeline = Pipeline([("preprocessor", preprocessor), ("regressor", LinearRegression())])
  ```
- **Prediction Interval:**
  The residual standard deviation $\sigma_{\text{res}}$ on test data is computed. Bounds are returned as:
  $$\text{Lower} = \max(15, \hat{y} - 1.645 \cdot \sigma_{\text{res}}), \quad \text{Upper} = \hat{y} + 1.645 \cdot \sigma_{\text{res}}$$

---

## 3. Model 2 Implementation: SLA Delay Risk Prediction

- **File:** `app/ai/training/train_delay.py`
- **Features Used:**
  - `predicted_duration_min`: From Model 1 or customer estimate
  - `sla_slack_min`: Time from window start to SLA deadline
  - `estimated_travel_min`: Transit travel estimate
  - `duration_to_slack_ratio`: $\frac{\text{duration}}{\text{slack}}$ (key indicator of deadline pressure)
  - `buffer_slack_min`: $\text{slack} - (\text{duration} + \text{travel})$ (negative means unavoidable delay)
- **Classification & Calibration:**
  Random Forest Classifier outputs $P(\text{Delayed})$.
  - $P < 0.30$: **LOW Risk** (Green) -> Standard automated dispatch
  - $0.30 \le P < 0.70$: **MEDIUM Risk** (Amber) -> Monitor transit progress
  - $P \ge 0.70$: **HIGH Risk** (Red) -> Prioritize dispatch or assign nearest idle technician

---

## 4. Model 3 Implementation: Demand Forecasting

- **File:** `app/ai/training/train_demand.py`
- **Chronological Split:** Prevents data leakage by training on the first 80% of days and evaluating on the subsequent 20% of days.
- **Outputs:** Expected job volume per zone (Central, North, South, East, West) along with expected peak demand zone.

---

## 5. Model 4 Implementation: Disruption Risk Prediction

- **File:** `app/ai/training/train_disruption.py`
- **Features:** Technician scheduled hours, tight buffer count (<15 min), and overwork index.
- **Output:** Categorical disruption probability and preventive recommendation (e.g. inserting buffer before next ticket).

