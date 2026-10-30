# DispatchGrid — AI Layer Architecture

Welcome to the AI Architecture Guide for **DispatchGrid**! This document explains how Artificial Intelligence and Machine Learning work inside DispatchGrid, written in clear, simple terms for beginners.

---

## 1. What Does "AI and Machine Learning" Mean in DispatchGrid?

In traditional software, developers write fixed rules like:
```python
# Fixed heuristic rule (No ML)
if job_type == "residential_wiring":
    duration = 120  # Always 120 minutes
```
In real electrical service operations in Mysuru:
- A residential wiring job in an older house with oxidized conduit takes much longer than in a new apartment.
- Traffic on Outer Ring Road fluctuates throughout the day.
- Highly experienced technicians complete complex jobs faster.

**Machine Learning (ML)** allows our system to look at historical data and learn statistical patterns. Instead of hardcoding fixed guesses:
$$\text{Duration} = f(\text{trade}, \text{priority}, \text{zone}, \text{skills}, \text{time of day})$$
The ML model outputs a point estimate along with an uncertainty interval $[ \text{Lower}, \text{Upper} ]$.

---

## 2. The Golden Rule of DispatchGrid AI

> **"AI predicts. The scheduler optimises. The backend validates and persists. The supervisor monitors and approves."**

```
  +-------------------------------------------------------------------------+
  |                        DISPATCHGRID HYBRID PIPELINE                     |
  |                                                                         |
  |   1. Customer Request                                                   |
  |          |                                                              |
  |          v                                                              |
  |   2. FastAPI Backend Validation (Pydantic + DB Constraints)             |
  |          |                                                              |
  |          v                                                              |
  |   3. AI Layer (Scikit-Learn Regression & Classification)                |
  |      • Predicts expected job duration with 90% confidence bounds        |
  |      • Classifies SLA deadline breach risk (LOW, MEDIUM, HIGH)          |
  |      • Forecasts 24-hour demand by urban circle                         |
  |      • Identifies technician workload strain & disruption risk          |
  |          |                                                              |
  |          v                                                              |
  |   4. Optimization Engine (Module B Greedy + Module C Local Search)      |
  |      • HARD CONSTRAINTS ENFORCED (Skills, Shift Hours, Windows)         |
  |      • Uses AI duration estimate to build realistic daily schedules     |
  |      • NEVER bypassed by ML predictions                                 |
  |          |                                                              |
  |          v                                                              |
  |   5. Technician 5-Minute Dispatch Offer & Acceptance                    |
  |          |                                                              |
  |          v                                                              |
  |   6. Operations & Recovery Management (D01-D07)                         |
  |      • Disruption occurs -> Recovery engine calculates proposal         |
  |      • Proposal saved as DRAFT                                          |
  |      • Supervisor reviews Before/After comparison & Approves/Rejects    |
  |      • Audit log permanently recorded in database                       |
  +-------------------------------------------------------------------------+
```

---

## 3. The Four Core AI Models

| # | Model Name | Role & Objective | Algorithm Selected | Key Metrics |
|---|---|---|---|---|
| **1** | **Job Duration Predictor** | Estimates service duration before scheduling | Linear Regression (Baseline) | **MAE: 16.47 min**, **R²: 0.83** |
| **2** | **SLA Delay Risk Classifier** | Detects jobs likely to miss response deadlines | Random Forest Classifier | **F1: 0.8358**, **ROC-AUC: 0.9857** |
| **3** | **Demand Forecaster** | Predicts incoming tickets per zone for next 24h | Ridge Regression (Time-Series) | **WAPE: 17.0%**, **MAE: 1.9 jobs** |
| **4** | **Disruption Risk Classifier**| Detects technician schedule overwork & strain | HistGradientBoosting Classifier | **ROC-AUC: 0.7521**, **F1: 0.4112** |

---

## 4. Why AI Enhances Optimization Without Breaking Feasibility

When a dispatch system uses overly optimistic flat durations (e.g., assuming every job takes 45 minutes), it schedules too many jobs per technician. When field technicians encounter real-world complexities, the entire schedule cascades into lateness.

By providing **realistic predicted durations** and **proactive SLA delay alerts**:
1. The scheduler allocates sufficient real-world capacity.
2. The supervisor is notified of high-risk jobs **before** dispatch occurs.
3. The technician receives realistic travel and work assignments.
4. Hard constraints (CHESCOM licenses, shift bounds, appointment windows) are strictly preserved.

