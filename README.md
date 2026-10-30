# ElectroGrid ⚡

### Intelligent Electrical Field-Service Management & Automated Workforce Scheduling Platform

**ElectroGrid** is an enterprise-grade field-service management and workforce scheduling platform designed for modern electrical distribution circles and enterprise utilities. It seamlessly orchestrates the field-service lifecycle across three core stakeholder portals: **Customer Portal**, **Technician Mobile Field Workspace**, and **Grid Operations Supervision**.

---

## 🌟 Key Capabilities

### 1. End-to-End Operational Lifecycle
```
CUSTOMER SERVICE REQUEST ➡️ COMPLAINT TRIAGE & CATEGORIZATION ➡️ 
CENTRALIZED HARD-CONSTRAINT VALIDATION ➡️ MULTI-CRITERIA SCORING & DISPATCH ➡️ 
FIELD JOB EXECUTION (EN ROUTE / ARRIVED / ON-SITE) ➡️ COMPLETION REPORT SIGN-OFF ➡️ 
RAZORPAY TEST MODE SETTLEMENT ➡️ AUDIT TRAIL & QUALITY FEEDBACK
```

### 2. Multi-Criteria Automated Scheduling Engine
- **Strict Hard-Constraint Filtering**: Validates certified electrician skills (e.g. High Voltage, 3-Phase, Solar PV), mandatory PPE/diagnostic safety gear, and daily shift hours.
- **Documented Heuristic Scoring Model**:
  - Technical Skill Compatibility: **25%**
  - Shift & Availability Match: **20%**
  - Proximity & Transit Distance: **20%**
  - Workload Balance: **15%**
  - Service Deadline Feasibility: **10%**
  - Specialized Equipment Match: **10%**
- **Autonomous Dispatch & 5-Minute Timeout**: Automatically dispatches highest-scoring candidate and monitors field acknowledgment.

### 3. Dynamic Disruption Recovery (D01–D07)
- Reproducible simulation for technician delay (+90m), vehicle breakdowns, emergency power outages, and critical equipment failures.
- Greedy baseline + bounded local-search optimization for instantaneous rebalancing without disrupting ongoing field work.

### 4. Interactive Mysuru Distribution Circle Map
- Real-time fleet tracking across 20 distribution feeders using Leaflet & OpenStreetMap.
- Interactive mock telemetry with turn-by-turn waypoint routing, live speed HUD, and heading indicator.

### 5. Integrated Razorpay Checkout (Test Mode)
- Transparent electrical invoicing: Diagnostic & Inspection Fee (₹399), Parts & Consumables (₹550), and 18% GST (₹171) = **₹1,120 Total**.
- Official Razorpay SDK Standard Checkout modal with HMAC-SHA256 signature verification.
- Instant Offline Sandbox simulation fallback for test evaluation without API credentials.
- Printable GST tax invoice receipt generation upon settlement.

---

## 👥 Demo Profiles & Credentials

Every account enforces credential validation. All demo profiles use the default password:

> **Default Password:** `dispatchgrid123`

| Role | Name | Email | Password | Primary Interface |
| :--- | :--- | :--- | :--- | :--- |
| **Supervisor** | Meera Kulkarni | `supervisor@dispatchgrid.io` | `dispatchgrid123` | `/supervisor/overview` |
| **Lead Technician** | Pradeep Hegde (MYS-TECH-100) | `technician@dispatchgrid.io` | `dispatchgrid123` | `/technician/dashboard` |
| **18th Electrician** | Guruprasad Rao (MYS-TECH-117) | `guruprasad.r@dispatchgrid.io` | `dispatchgrid123` | `/technician/dashboard` |
| **Individual Customer** | Ananya Rao | `customer@dispatchgrid.io` | `dispatchgrid123` | `/customer/dashboard` |
| **Commercial Enterprise** | Suresh N. (Mysore Silk) | `facilities@mysoresilk.in` | `dispatchgrid123` | `/customer/dashboard` |

---

## 🛠️ Technology Stack

- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, React Router v6, Lucide React, Recharts, Leaflet.
- **Backend API**: Python 3.12+, FastAPI, SQLAlchemy, Pydantic v2, Uvicorn, httpx.
- **Database**: PostgreSQL (Supabase pooler mode).
- **Payment Gateway**: Razorpay REST Orders API + HMAC-SHA256 Webhooks (Test Mode).
- **Deployment Platform**: Vercel (Frontend SPA) + Cloud hosting (FastAPI Monolith).

---

## 🚀 Local Development Setup

### 1. Frontend
```bash
# Install dependencies
npm install

# Start Vite development server on port 3000
npm run dev

# Run production build check
npm run build
```

### 2. Backend (FastAPI)
```bash
cd integration/bdsc_backend/BDSC/backend

# Create virtual environment & install requirements
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt

# Start backend server on port 8000
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

---

## 🌐 Deployment to Vercel

ElectroGrid is pre-configured for one-click deployment on Vercel:

1. Import repository `https://github.com/basavaraja-byte/elctrogrid` on Vercel.
2. Select Framework Preset: **Vite**.
3. Build Command: `npm run build`.
4. Output Directory: `dist`.
5. Configure Environment Variables in Vercel Project Settings:
   - `VITE_API_BASE_URL`: URL of your deployed FastAPI backend (or `http://localhost:8000` for local proxy).
   - `VITE_USE_MOCK_DATA`: Set `true` for standalone preview mode with full interactive demo data; `false` to connect to production backend.
   - `VITE_RAZORPAY_KEY_ID`: Your Razorpay Test Key ID (`rzp_test_...`).
