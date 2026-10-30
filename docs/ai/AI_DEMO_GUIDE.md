# DispatchGrid — Hackathon AI Demonstration Guide

Follow these exact steps to demonstrate the AI Layer during hackathon presentations and technical evaluations.

---

## 🎬 5-Minute Demonstration Script

### Step 1: Open the Supervisor Dashboard
1. Open your browser and navigate to **[http://localhost:3000](http://localhost:3000)**.
2. In the top navigation bar, use the **Role Switcher** to switch to **Supervisor** (`supervisor@dispatchgrid.io`).
3. Notice the new **AI Predictive Intelligence & Risk Evaluation** banner at the top of the dashboard:
   - **Live Models Active**: Shows that 4/4 trained models are loaded in memory.
   - **Model 1: Duration Regressor**: Linear Regression (MAE: 16.5m, R²: 0.83).
   - **Model 2: SLA Delay Classifier**: Random Forest (F1: 0.84, ROC-AUC: 0.99).
   - **Model 3: Demand Forecaster**: Ridge Time-Series (WAPE: 17.0%).
   - **Model 4: Disruption Classifier**: HistGradientBoosting (ROC-AUC: 0.75).
   - Click the **Refresh Predictions** button to see real-time synchronization with the FastAPI backend.

### Step 2: Demonstrate Real-Time SLA Delay Risk Analysis
1. In the **SLA Delay Risk Priority Queue** panel, observe tickets flagged as **HIGH Risk** or **MEDIUM Risk**.
2. Point out the **AI Diagnosis**:
   > *"Predicted service duration is 135m (confidence range 115m - 160m). Transit travel of ~25m leaves insufficient slack before SLA deadline."*
3. Show the **Action Recommendation**:
   > *"Prioritize immediate dispatch or reassign to an idle technician in the same zone."*
4. Explain to the judges:
   > *"Traditional dispatchers only discover a delay after a customer complains. Our ML model predicts the delay before the technician is even dispatched, allowing proactive intervention."*

### Step 3: Demonstrate Multi-Zone Demand Forecasting (Mysuru)
1. Point to the **Next 24h Demand Forecast** panel.
2. Show the expected ticket distribution across Mysuru zones:
   - **Central Mysuru**: Identified as **PEAK DEMAND** (16.0 - 20.0 tickets).
   - **North & South**: Normal operational volume (10.0 - 14.0 tickets).
   - **East & West**: Lower baseline load (6.0 - 10.0 tickets).
3. Explain:
   > *"This allows operations managers to pre-position technicians in Central Mysuru rather than having them idle in outer zones."*

### Step 4: Demonstrate Baseline vs AI Comparison
Open PowerShell and run the benchmark comparison script:
```powershell
cd c:\project\project\MITM\code\integration\bdsc_backend\BDSC\backend
$env:OMP_NUM_THREADS = "1"
python -m app.ai.evaluation.compare_baseline_vs_ai
```
Show the live console output table to the judges:
- **Schedule Objective Cost:** **0.21** (AI-Enhanced) vs **0.24** (Static Baseline) -> Lower cost and superior balance.
- **SLA Delay Risks Proactively Identified:** **29 High Risks** caught in Run B vs **0 monitored** in Run A.
- **Hard Constraints Maintained:** **100% strict adherence** in both runs.

### Step 5: Demonstrate Interactive Swagger API Testing
1. Navigate to **[http://localhost:8000/docs#/AI%20%26%20Machine%20Learning](http://localhost:8000/docs#/AI%20%26%20Machine%20Learning)**.
2. Click on `POST /api/v1/ai/predict-duration` -> Click **Try it out** -> Click **Execute**.
3. Show the JSON response containing the predicted duration and 90% confidence interval.
4. Click on `GET /api/v1/ai/model-status` -> Click **Execute** to show the live health and metrics of all 4 models.

