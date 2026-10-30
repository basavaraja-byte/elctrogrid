# DispatchGrid — AI API Reference Documentation

All AI & Machine Learning endpoints are served by the FastAPI backend on port `8000` under the `/api/v1/ai` prefix.

Interactive Swagger documentation is available at:
**[http://localhost:8000/docs#/AI%20%26%20Machine%20Learning](http://localhost:8000/docs#/AI%20%26%20Machine%20Learning)**

---

## 1. Predict Job Duration

`POST /api/v1/ai/predict-duration`

Predicts expected service duration with empirical 90% confidence intervals based on trade complexity, required certifications, customer facility type, and service zone.

### Request Example
```json
{
  "job_type": "residential_wiring",
  "priority": "Normal",
  "required_skills": ["residential_wiring", "safety_inspection"],
  "service_zone": "Central",
  "window_start_min": 540,
  "window_end_min": 720,
  "estimated_duration_min": 120,
  "customer_type": "individual"
}
```

### Response Example (HTTP 200)
```json
{
  "predicted_duration_min": 124.6,
  "lower_bound_min": 92.4,
  "upper_bound_min": 156.8,
  "confidence_score": 0.88,
  "model_name": "LinearRegression (Baseline)",
  "model_version": "1.0.0",
  "prediction_timestamp": "2026-10-31T00:15:00.000000Z",
  "fallback_used": false,
  "data_source": "SYNTHETIC_AUGMENTED"
}
```

---

## 2. Predict SLA Delay Risk

`POST /api/v1/ai/predict-delay-risk`

Evaluates whether a job is at risk of missing its SLA response deadline, returning a calibrated probability, categorical risk tier (`LOW`, `MEDIUM`, `HIGH`), and explainable contributing factors.

### Request Example
```json
{
  "job_id": "JOB-042",
  "job_type": "distribution_panel_repair",
  "priority": "Critical",
  "predicted_duration_min": 135.0,
  "appointment_window_start_min": 540,
  "appointment_window_end_min": 660,
  "sla_deadline_min": 690,
  "estimated_travel_time_min": 25.0,
  "service_zone": "East"
}
```

### Response Example (HTTP 200)
```json
{
  "job_id": "JOB-042",
  "delay_probability": 0.84,
  "risk_category": "HIGH",
  "contributing_factors": [
    "Severe buffer deficit: Service duration (135m) + travel (25m) leaves only 10 minutes before SLA deadline.",
    "Elevated priority (Critical) imposes accelerated response deadline."
  ],
  "suggested_action": "Job JOB-042 is at HIGH risk of missing its SLA deadline. Action: Reassign to an idle technician in the same zone or escalate priority queue immediately.",
  "model_name": "RandomForestClassifier",
  "model_version": "1.0.0",
  "prediction_timestamp": "2026-10-31T00:15:00.000000Z",
  "fallback_used": false,
  "data_source": "SYNTHETIC_AUGMENTED"
}
```

---

## 3. Forecast Electrical Service Demand

`POST /api/v1/ai/forecast-demand`

Forecasts incoming electrical maintenance volume per Mysuru urban zone over the next 24 hours.

### Request Example
```json
{
  "service_zone": null,
  "target_date": "2026-10-31",
  "day_of_week": 5
}
```

### Response Example (HTTP 200)
```json
{
  "forecast_period": "Next 24h (2026-10-31)",
  "total_expected_jobs": 52.0,
  "peak_zone": "Central",
  "zone_forecasts": [
    { "zone": "Central", "expected_jobs": 16.0, "lower_bound": 12.8, "upper_bound": 20.0, "demand_level": "PEAK" },
    { "zone": "North", "expected_jobs": 11.0, "lower_bound": 8.8, "upper_bound": 13.8, "demand_level": "NORMAL" },
    { "zone": "South", "expected_jobs": 10.0, "lower_bound": 8.0, "upper_bound": 12.5, "demand_level": "NORMAL" },
    { "zone": "East", "expected_jobs": 8.0, "lower_bound": 6.4, "upper_bound": 10.0, "demand_level": "NORMAL" },
    { "zone": "West", "expected_jobs": 7.0, "lower_bound": 5.6, "upper_bound": 8.8, "demand_level": "NORMAL" }
  ],
  "model_name": "Ridge (Baseline)",
  "model_version": "1.0.0",
  "prediction_timestamp": "2026-10-31T00:15:00.000000Z",
  "data_source": "SYNTHETIC_AUGMENTED"
}
```

---

## 4. Predict Disruption Risk

`POST /api/v1/ai/predict-disruption-risk`

Evaluates technician schedule compression and flags potential cascaded delays.

### Request Example
```json
{
  "technician_id": "TECH-004",
  "job_id": "JOB-018",
  "technician_workload_hours": 8.5,
  "tight_buffer_count": 2,
  "service_zone": "Central"
}
```

### Response Example (HTTP 200)
```json
{
  "disruption_probability": 0.68,
  "risk_category": "HIGH",
  "affected_technician_id": "TECH-004",
  "affected_job_id": "JOB-018",
  "contributing_factors": [
    "Technician workload strain: Assigned 8.5 hours today exceeds 8.0h standard shift limit.",
    "Schedule compression: 2 consecutive assignments have less than 15-minute transit buffers."
  ],
  "suggested_preventive_action": "Technician TECH-004 schedule has HIGH disruption risk. Action: Insert a 30-minute buffer window or rebalance next ticket to secondary technician.",
  "model_name": "HistGradientBoostingClassifier",
  "model_version": "1.0.0",
  "prediction_timestamp": "2026-10-31T00:15:00.000000Z",
  "data_source": "SYNTHETIC_AUGMENTED"
}
```

---

## 5. Get Model Status & Health

`GET /api/v1/ai/model-status`

Returns readiness status, algorithms, sample sizes, and live metrics for all 4 trained models.

---

## 6. Get Model Evaluation Reports

`GET /api/v1/ai/evaluation`

Returns comprehensive candidate model benchmark comparisons (MAE, RMSE, R², F1, ROC-AUC, WAPE).

