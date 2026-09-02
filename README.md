# ChargebackGuard 🛡️
**An Explainable AI Risk & Fraud Detection Agent**

*Prepared for Razorpay AI Buildathon — Track 02: AI Risk Manager*

ChargebackGuard is a transparent, defense-only payment fraud and chargeback risk detection agent. It replaces traditional black-box risk scores with plain-language, factually grounded reason chains, quantifies the financial cost of classification errors (False Positives vs False Negatives), routes ambiguous borderline transactions to a human review queue, and maintains an append-only audit trail of analyst override decisions.

---

## 🏗️ 1. Project Overview & Architecture

ChargebackGuard implements a **Hybrid Rule + LLM Architecture**:

1. **Deterministic Rule Engine (Fast Path):** High-confidence transactions matching verified historical patterns (e.g. established account history, matching domestic IP/billing, normal transaction amount) are automatically cleared (`RULE_TRUSTED_USER_CLEAR`, Score 5, `auto-clear`) without making external LLM calls.
2. **Google Gemini LLM Reasoning Layer (Deep Inspection):** Transactions exhibiting ambiguous risk signals (e.g., unrecognized new device, geographic location shifts, velocity spikes, or amount deviations) are routed to Google Gemini (`gemini-3.5-flash` / `gemini-3.6-flash` via the official `google-genai` SDK).
3. **Multi-Signal Corroboration & Risk Calibration:** Gemini evaluates signal tradeoffs using multi-signal corroboration rules—requiring at least two independent corroborating risk factors before scoring above the review-queue threshold (>70). Single isolated signals (like a routine device upgrade on an established account) are recognized as normal consumer behavior and scored <30 (`auto-clear`).
4. **Human-in-the-Loop Review Queue:** Borderline risk scores (configurable 30–70 score band) route to human risk analysts for decision override.
5. **Financial Error Cost Exposure:** Computes False Positive cost (customer friction + lost revenue margin) vs False Negative cost (chargeback penalty fee + transaction value).

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│  ┌───────────────┐  ┌────────────────┐  ┌─────────────────────┐ │
│  │ Upload Batch  │  │ Review Queue   │  │ Metrics Dashboard   │ │
│  │ View          │  │ & Drawer       │  │ & Settings Views    │ │
│  └───────┬────────┘  └────────┬───────┘  └──────────┬──────────┘ │
└──────────┼────────────────────┼──────────────────────┼────────────┘
           │                    │                       │
           ▼                    ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                            │
│                                                                     │
│  ┌────────────┐   ┌───────────────┐   ┌────────────────────────┐  │
│  │ Ingestion & │──▶│ Rule Engine    │──▶│ Google Gemini LLM      │  │
│  │ Validation  │   │ (deterministic)│   │ Reasoning Layer        │  │
│  └────────────┘   └───────┬────────┘   └───────────┬────────────┘  │
│                            │                        │               │
│                            ▼                        ▼               │
│                    ┌───────────────────────────────────┐            │
│                    │   Scoring & Routing Service       │            │
│                    │  (assigns final score + routing)  │            │
│                    └───────────────┬───────────────────┘            │
│                                    ▼                                 │
│                    ┌───────────────────────────────────┐            │
│                    │   Cost Calculator                 │            │
│                    └───────────────┬───────────────────┘            │
│                                    ▼                                 │
│                    ┌───────────────────────────────────┐            │
│                    │   Review/Override Service         │◀── Analyst │
│                    └───────────────┬───────────────────┘            │
│                                    ▼                                 │
│                    ┌───────────────────────────────────┐            │
│                    │   Audit Log Service (append-only) │            │
│                    └───────────────┬───────────────────┘            │
│                                    ▼                                 │
│                    ┌───────────────────────────────────┐            │
│                    │   Metrics Service                 │            │
│                    │  (precision/recall/F1, cost)      │            │
│                    └───────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  Database (SQLite)  │
                 │  - transactions     │
                 │  - scores           │
                 │  - reason_chains    │
                 │  - audit_log        │
                 │  - test_labels      │
                 └─────────────────────┘
```

---

## 📊 2. Key Verification Results (Identical 100-Transaction Test Set)

All performance metrics below were computed on the **identical 100-transaction test dataset** (`data/synthetic_transactions.csv`) containing 12 actual ground-truth fraud transactions (`is_fraud=True`) and 88 legitimate transactions (`is_fraud=False`).

### Side-by-Side Performance Comparison

| Metric | Production Rule Funnel (Pre-LLM) | **Recalibrated Gemini Hybrid System** | Net Improvement / Delta |
|---|---|---|---|
| **True Positives (TP)** | 12 (out of 12) | **12 (out of 12)** | **100% Fraud Detection Maintained** |
| **False Positives (FP)** | 39 | **8** | **-31 False Positives (79.5% Reduction!)** |
| **False Negatives (FN)** | 0 | **0** | **Zero Missed Fraud (0% FNR)** |
| **True Negatives (TN)** | 49 | **80** | **+31 Legitimate Transactions Cleared** |
| **Precision** | 23.53% | **60.00%** | **+36.47 percentage points** |
| **Recall** | 100.00% | **100.00%** | **100.00%** |
| **F1 Score** | **0.3810** | **0.7500** | **+0.3690 (+36.9 percentage points!)** |
| **False Positive Rate (FPR)** | 44.32% | **9.09%** | **-35.23 percentage points** |
| **FP Cost Exposure** | ₹54,867.63 | **₹23,410.15** | **57.3% Financial Cost Reduction!** |


### Comparison Against Strict Phase 1 Heuristic

- **Phase 1 Naive 3-Rule Heuristic (`generate_dataset.py`):** Precision = 63.64%, Recall = **58.33%** (TP=7, FP=4, FN=5, TN=84), **F1 = 0.6087**.
- **Recalibrated Gemini Hybrid System:** Precision = **60.00%**, Recall = **100.00%** (TP=12, FP=8, FN=0, TN=80), **F1 = 0.7500**.
- **Insight:** The Hybrid System catches **5 additional true positive fraud cases** (12 vs 7) that static rules miss entirely, while boosting F1 score from 0.6087 to 0.7500 (+14.13 percentage points).

> *Note on Model Selection:* Google Gemini API (`gemini-3.5-flash` / `gemini-3.6-flash` via the official `google-genai` SDK) was selected as the LLM provider due to free-tier access availability for the buildathon.

---

## 🛠️ 3. Tech Stack

- **Backend:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic v2, PyJWT, Pytest
- **Database:** SQLite (`chargeback_guard.db`)
- **LLM SDK:** `google-genai` (Google GenAI SDK v2.21.0, utilizing `gemini-3.5-flash` / `gemini-3.6-flash`)
- **Frontend:** React 18, Vite, Tailwind CSS, Lucide Icons
- **Version Control:** Git & GitHub (`https://github.com/ArjunReddyVelma/ChargebackGuard.git`)

---

## 💻 4. Local Setup & Execution Instructions

### Prerequisites
- **Python:** Version 3.11+ installed
- **Node.js:** Version 18+ and `npm` installed
- **Google Gemini API Key:** Free key from [Google AI Studio](https://aistudio.google.com/)

### 1. Clone Repository & Setup Virtual Environment
```bash
git clone https://github.com/ArjunReddyVelma/ChargebackGuard.git
cd ChargebackGuard

# Create Python virtual environment inside /backend/venv
python3.11 -m venv backend/venv
source backend/venv/bin/activate

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` in the `backend/` directory:
```bash
cp backend/.env.example backend/.env
```
Edit `backend/.env` and paste your Gemini API key:
```env
DATABASE_URL=sqlite:///./chargeback_guard.db
SECRET_KEY=chargebackguard_dev_secret_key_change_me_1234567890
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
GEMINI_API_KEY=your_actual_gemini_api_key_here
CORS_ORIGINS=http://localhost:5173
```

### 3. Generate Synthetic Dataset & Seed Database
```bash
# Generate 600 synthetic transactions & separate DR-1 labels
PYTHONPATH=.:backend ./backend/venv/bin/python data/generate_dataset.py

# Seed test labels and demo user accounts into SQLite
PYTHONPATH=.:backend ./backend/venv/bin/python data/seed_labels.py
```

### 4. Start FastAPI Backend Server
```bash
# From the project root directory:
PYTHONPATH=.:backend ./backend/venv/bin/uvicorn backend.main:app --reload --port 8000
```
Backend API interactive docs: `http://localhost:8000/docs`

### 5. Install & Start React Frontend
In a new terminal window:
```bash
cd frontend
npm install

# Create frontend .env file
echo "VITE_API_URL=http://localhost:8000" > .env

# Start Vite dev server
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## 🔑 5. Demo Login Credentials

The database is pre-seeded with two demo user accounts:

| Role | Email | Password | Features Accessible |
|---|---|---|---|
| **Analyst** | `analyst@chargebackguard.io` | `analyst123` | Upload Batch, Dashboard (view), Review Queue, Submit Analyst Overrides |
| **Risk Manager** | `manager@chargebackguard.io` | `manager123` | All Analyst features + Audit Log Explorer (`/audit-log`) + Settings Config (`/config`) |

---

## 🧪 6. Running Automated Tests

To execute the complete 26-case automated pytest suite:
```bash
PYTHONPATH=.:backend ./backend/venv/bin/pytest backend/tests
```

**Test Suite Coverage (26 / 26 Passed):**
- `test_validation.py`: Schema validation (VR-1 to VR-6) & row error quarantining (ER-1)
- `test_rule_engine.py`: High-confidence rules & edge cases (EC-1 null shipping, EC-2 brand-new account, EC-6 velocity anomaly)
- `test_llm_reasoning.py`: Gemini LLM reasoning, grounding checks (BR-7, EC-7), prompt safety (SEC-6), and ER-2 fallback (`degraded_reasoning`)
- `test_scoring_service.py`: Score boundaries (EC-4) and DR-1 label isolation assertion
- `test_cost_calculator.py`: Financial FP/FN error cost exposure formulas (FR-6)
- `test_decisions_audit.py`: Analyst override submission, 10-char reason enforcement (VR-3), race condition prevention (`ALREADY_DECIDED`, EC-5), and append-only audit logging (BR-1)
- `test_metrics.py`: Post-hoc precision, recall, F1, cost summary, and decision split calculation
- `test_auth_config.py`: JWT role-based AuthZ enforcement (Analyst denied 403 on `/config`)
- `test_e2e_integration.py`: Complete end-to-end flow execution

---

## ⚠️ 7. Known Limitations & Future Work

1. **Small Test Sample Caveat:** The verification dataset contains 100 transactions with 12 actual fraud instances (`is_fraud=True`, 12.0% prevalence). Because there are 12 positive cases, each individual transaction shifts recall by ±8.33 percentage points. Larger-scale evaluation on 1,000–10,000 transactions is recommended for enterprise production deployment.
2. **Synthetic Data Validation:** Validated on synthetic datasets designed to replicate realistic payment signals. Validation against real-world benchmarks like PaySim (6.3M transactions, 0.13% fraud rate) is a natural next step, though PaySim lacks device ID and IP location fields used by our reason chains and would require schema adaptation.
3. **Local Deployment for Buildathon:** Running locally on port 8000 (backend) and port 5173 (frontend). Full production hosting configurations (Render/Railway backend + Vercel frontend) are detailed in the Architecture document but were skipped for live hosting due to buildathon time constraints.
4. **Enterprise AuthZ Matrix & Encryption:** Full 4-role AuthZ matrix (Auditor, System accounts), database encryption at rest, and session revocation lists were designed in the SRS but intentionally deferred as documented MVP scoping decisions.
5. **Implemented UI Extensions (Phase 9):**
   - **Audit Log View (`AuditLogView.jsx`):** Fully built and functional for Risk Managers. Displays formatted, expandable JSON audit events for scores, overrides, and threshold updates.
   - **Settings View (`SettingsView.jsx`):** Fully built and functional for Risk Managers. Allows live tuning of score threshold bands (low/high) and financial cost parameters (friction rate, chargeback fee) with immediate preview.

---

## 📁 8. Project Structure

```text
ChargebackGuard/
├── backend/                  # FastAPI Backend Application
│   ├── app/                  # Application Modules
│   │   ├── routers/          # REST API Route Handlers (batches, transactions, auth, metrics, config, audit)
│   │   ├── models.py         # SQLAlchemy ORM Models (Transaction, Score, ReasonChain, Cost, Decision, AuditLog, User, TestLabel)
│   │   ├── schemas.py        # Pydantic Schemas (VR-1 to VR-6 validation)
│   │   ├── rule_engine.py    # Deterministic Rule Engine
│   │   ├── llm_reasoning.py # Google Gemini API Reasoning Layer & ER-2 Fallback
│   │   ├── scoring_service.py# Hybrid Scoring & DR-1 Isolation Assertion
│   │   ├── cost_calculator.py# Financial Error Cost Exposure Calculator
│   │   ├── metrics_service.py# Precision, Recall, F1 & Cost Exposure Metrics Engine
│   │   ├── audit_log.py      # Append-Only Audit Logger
│   │   └── auth.py           # JWT Authentication & Role Dependencies
│   ├── tests/                # Automated Pytest Suite (26 Passing Tests)
│   ├── requirements.txt      # Backend Python Dependencies
│   ├── .env.example          # Environment Variables Template
│   └── main.py               # FastAPI App Entrypoint & Database Seeder
├── frontend/                 # React 18 + Vite + Tailwind Frontend Application
│   ├── src/
│   │   ├── components/       # Reusable Components (KPICard, ScorePill, Badge, Drawer, Toast, Skeleton)
│   │   ├── views/            # Main Views (Login, AppShell, Dashboard, Upload, ReviewQueue, AuditLog, Settings)
│   │   ├── services/api.js   # API Integration Client
│   │   └── App.jsx           # App Shell Routing & View State Management
│   ├── package.json          # Node.js Dependencies
│   └── vite.config.js        # Vite Build Configuration
├── data/                     # Data Generation & Evaluation Scripts
│   ├── generate_dataset.py   # Synthetic Dataset Generator & Build Gate Check
│   ├── seed_labels.py        # Test Label Database Seeder
│   ├── synthetic_transactions.csv # Input Transactions (DR-1: NO is_fraud field!)
│   ├── synthetic_labels.csv  # Isolated Ground Truth Labels
│   ├── run_live_gemini_evaluation.py # Live Gemini Evaluation Runner
│   └── run_identical_100row_comparison.py # Identical Dataset Baseline Comparison
├── ChargebackGuard_PRD.md    # Product Requirements Document
├── ChargebackGuard_SRS.md    # Software Requirements Specification
├── ChargebackGuard_Architecture.md # System Architecture Document
├── ChargebackGuard_UIUX.md   # UI/UX Specification Document
└── ChargebackGuard_DevelopmentPlan.md # Phase-by-Phase Development Plan
```

---

## 🔗 9. Link to Full Documentation

For detailed architectural diagrams, business rules, API schemas, and UI designs, refer to the full specification documents in the repository:

- [Product Requirements Document (PRD)](file:///Users/reddy/Desktop/ChargebackGuard/ChargebackGuard_PRD.md)
- [Software Requirements Specification (SRS)](file:///Users/reddy/Desktop/ChargebackGuard/ChargebackGuard_SRS.md)
- [System Architecture Document](file:///Users/reddy/Desktop/ChargebackGuard/ChargebackGuard_Architecture.md)
- [UI/UX Specification Document](file:///Users/reddy/Desktop/ChargebackGuard/ChargebackGuard_UIUX.md)
- [Development Plan](file:///Users/reddy/Desktop/ChargebackGuard/ChargebackGuard_DevelopmentPlan.md)
