# DispatchGrid — AI Model Evaluation Report

This report presents the objective evaluation metrics, candidate model comparisons, and statistical findings across all four DispatchGrid Machine Learning models.

---

## 1. Summary of Candidate Evaluations

### Model 1: Job Duration Prediction (Regression)
- **Target:** `actual_duration_min`
- **Training Set:** 1,200 records | **Test Set:** 300 records (80/20 split)

| Candidate Model | MAE (Mean Abs. Error) | RMSE (Root Mean Sq. Error) | R² Score | Selection Status |
| :--- | :--- | :--- | :--- | :--- |
| **Linear Regression (Baseline)** | **16.47 min** | **22.83 min** | **0.8264** | **SELECTED (Best generalization & explainability)** |
| **Random Forest Regressor** | 17.76 min | 24.03 min | 0.8077 | Candidate |
| **HistGradientBoosting Regressor**| 17.79 min | 23.94 min | 0.8092 | Candidate |

> **Finding:** Linear Regression achieved the lowest MAE (16.47 min) and highest R² (0.83). Because physical electrical service trade categories exhibit clean linear relationships with trade complexity and customer types, the baseline generalized better on unseen data without overfitting.

---

### Model 2: SLA Delay Risk Prediction (Binary Classification)
- **Target:** `sla_delayed` (0 = On-time, 1 = Missed deadline)
- **Evaluation Metrics:** Precision, Recall, F1-Score, ROC-AUC, PR-AUC

| Candidate Model | Precision | Recall | F1-Score | ROC-AUC | Selection Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression (Baseline)** | 0.8710 | 0.7714 | 0.8182 | 0.9884 | Candidate |
| **Random Forest Classifier** | **0.8750** | **0.8000** | **0.8358** | **0.9857** | **SELECTED (Highest F1 & balanced recall)** |
| **HistGradientBoosting Classifier**| 0.8750 | 0.8000 | 0.8358 | 0.9887 | Candidate |

> **Finding:** Random Forest Classifier achieved an outstanding **F1-Score of 0.8358** with an **80.0% recall rate**, meaning 4 out of 5 potential SLA breaches are detected before technician dispatch occurs.

---

### Model 3: Electrical Service Demand Forecasting (Time-Series Regression)
- **Target:** `daily_job_count` per urban service zone
- **Split:** Strictly chronological (first 144 days training, last 36 days test)

| Candidate Model | MAE (Jobs) | RMSE | WAPE (%) | Selection Status |
| :--- | :--- | :--- | :--- | :--- |
| **Ridge Regression (Baseline)** | **1.92 jobs** | **2.48** | **16.99%** | **SELECTED (Lowest error on unseen days)** |
| **Random Forest Regressor** | 1.95 jobs | 2.54 | 17.20% | Candidate |
| **HistGradientBoosting Regressor**| 2.10 jobs | 2.75 | 18.59% | Candidate |

> **Finding:** Ridge Regression achieved a Weighted Absolute Percentage Error (WAPE) of **17.0%**, accurately tracking seasonal variations and weekend shifts with an average error of under 2 service tickets per zone.

---

### Model 4: Schedule Disruption Risk Prediction (Classification)
- **Target:** `disruption_occurred` (Technician delay or cascade overrun)

| Candidate Model | Precision | Recall | F1-Score | ROC-AUC | Selection Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Logistic Regression (Baseline)** | 0.6923 | 0.1364 | 0.2278 | 0.7583 | Candidate |
| **Random Forest Classifier** | 0.6667 | 0.2424 | 0.3556 | 0.8015 | Candidate |
| **HistGradientBoosting Classifier**| **0.5366** | **0.3333** | **0.4112** | **0.7521** | **SELECTED (Best balance for imbalanced risk)** |

> **Finding:** Disruption risk exhibits inherent operational class imbalance (~20% positive rate). HistGradientBoosting provided the best recall (33.3%) and F1-score (0.41), identifying tight schedules that require supervisor attention.

---

## 2. Reproducibility & Automated Retraining

All model artifacts (`*.joblib`) and evaluation reports (`*.json`) are regenerated with deterministic random seeds (`random_seed=42`) via:
```powershell
python -m app.ai.training.train_all
```

