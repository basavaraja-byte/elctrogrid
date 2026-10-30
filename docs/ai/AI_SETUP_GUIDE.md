# DispatchGrid — AI Setup & Environment Guide

This guide provides exact step-by-step instructions for setting up the Python environment, installing dependencies, training the models, and running the application on Windows.

---

## 1. Prerequisites

- **OS:** Windows 10/11
- **Python:** Python 3.11+ (Python 3.15 used in current environment)
- **Node.js:** v18+ (for React Vite frontend)
- **PowerShell:** Standard Windows PowerShell terminal

---

## 2. Setting Up Python Virtual Environment

Open Windows PowerShell and navigate to the integration workspace:

```powershell
# 1. Navigate to backend workspace
cd c:\project\project\MITM\code\integration\bdsc_backend\BDSC\backend

# 2. Activate existing virtual environment
..\..\.venv\Scripts\Activate.ps1
```

If setting up a new virtual environment from scratch:
```powershell
# Create venv
python -m venv .venv

# Activate venv
.\.venv\Scripts\Activate.ps1

# Install core backend, scheduler, and AI packages
pip install fastapi uvicorn sqlalchemy alembic pydantic pydantic-settings python-dotenv pytest httpx psycopg-binary
pip install numpy pandas scikit-learn scipy joblib
```

---

## 3. Training the AI Models

To train all 4 models sequentially and generate fresh artifacts and metrics:

```powershell
$env:OMP_NUM_THREADS = "1"
python -m app.ai.training.train_all
```

Expected output:
- Model 1: Saved to `app/ai/artifacts/models/duration_model.joblib`
- Model 2: Saved to `app/ai/artifacts/models/delay_model.joblib`
- Model 3: Saved to `app/ai/artifacts/models/demand_model.joblib`
- Model 4: Saved to `app/ai/artifacts/models/disruption_model.joblib`
- Evaluation JSON reports saved to `app/ai/artifacts/metrics/*.json`

---

## 4. Running the Complete System

### Terminal 1: Unified FastAPI Backend (Port 8000)
```powershell
cd c:\project\project\MITM\code\integration\bdsc_backend\BDSC\backend
$env:OMP_NUM_THREADS = "1"
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
- Interactive Swagger UI: **http://localhost:8000/docs**
- AI Health Status: **http://localhost:8000/api/v1/ai/model-status**

### Terminal 2: React Vite Frontend (Port 3000)
```powershell
cd c:\project\project\MITM\code
npm run dev
```
- Frontend Web App: **http://localhost:3000**

---

## 5. Running the Test Suite

Execute the entire backend, scheduler, and AI test suite:

```powershell
# Run AI tests (16 tests)
cd c:\project\project\MITM\code\integration\bdsc_backend\BDSC\backend
$env:OMP_NUM_THREADS = "1"
pytest tests/test_ai_layer.py -v

# Run all backend + AI tests (44 tests)
pytest tests/ -v

# Run scheduler tests (72 tests)
cd c:\project\project\MITM\code\integration\scheduler\dispatch_grid
pytest app/tests/ -v
```
All **116 tests** will pass cleanly.

