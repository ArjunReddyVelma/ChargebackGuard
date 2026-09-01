# ChargebackGuard 🛡️
**An Explainable AI Risk & Fraud Detection Agent**

*Prepared for Razorpay AI Buildathon — Track 02: AI Risk Manager*

ChargebackGuard is a transparent, defense-only fraud detection system that replaces black-box risk scores with plain-language reason chains, quantifies the financial cost of errors (False Positives vs False Negatives), routes borderline transactions to a human review queue, and maintains an immutable audit trail of analyst overrides.

---

## 🚀 Key Features

1. **Hybrid Scoring Engine:** Fast deterministic rule layer for high-confidence cases + Claude 3.5 LLM reasoning layer for ambiguous transactions.
2. **Traceable Reason Chains:** Every scored transaction outputs plain-language explanations referencing real input features (no generic or fabricated claims).
3. **Financial Error Cost Exposure:** Computes False Positive cost (customer friction + lost revenue margin) vs False Negative cost (chargeback penalty fee + transaction value).
4. **Human-in-the-Loop Review Queue:** Borderline risk scores (configurable 30–70 score band) route to analysts for decision override.
5. **Immutable Audit Trail:** All human overrides and threshold configuration updates are logged in an append-only audit log.
6. **Ground Truth Rigor (DR-1 & Build Gate):** Ground truth `is_fraud` labels are strictly isolated from scoring inputs. Synthetic data generator includes a build gate check verifying a rules-only baseline achieves <95% precision/recall to guarantee realistic ambiguity.

---

## 🛠️ Architecture & Stack

- **Backend:** Python 3.11+ / FastAPI / SQLAlchemy / Pydantic v2 / PyJWT / Pytest
- **Database:** SQLite (`chargeback_guard.db`)
- **LLM Layer:** Anthropic Claude API (`claude-3-5-sonnet-20241022`) with rule-based fallback (`degraded_reasoning`, ER-2)
- **Frontend:** React 18 / Vite / Tailwind CSS / Lucide Icons
- **Version Control:** Git / GitHub (`https://github.com/ArjunReddyVelma/ChargebackGuard.git`)

---

## 📥 Quick Start Instructions

### Prerequisites
- Python 3.11+
- Node.js (v18+) & npm

### 1. Repository Setup & Clone
```bash
git clone https://github.com/ArjunReddyVelma/ChargebackGuard.git
cd ChargebackGuard
```

### 2. Backend Setup
```bash
# Navigate to backend and activate virtual environment
cd backend
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env and insert your ANTHROPIC_API_KEY if testing LLM calls

# Run FastAPI backend server on port 8000
uvicorn main:app --reload --port 8000
```

### 3. Data Generation & Seeding
In a separate terminal:
```bash
# Generate synthetic dataset with build gate check
python data/generate_dataset.py

# Seed test ground truth labels into database
python data/seed_labels.py
```

### 4. Frontend Setup
In another terminal:
```bash
cd frontend
npm install
npm run dev
```
The frontend dev server runs at `http://localhost:5173`.

---

## 🔑 Demo Login Accounts

| Role | Email | Password | Allowed Access |
|---|---|---|---|
| **Analyst** | `analyst@chargebackguard.io` | `analyst123` | Upload Batch, Dashboard (view), Review Queue, Submit Overrides |
| **Risk Manager** | `manager@chargebackguard.io` | `manager123` | All Analyst features + Audit Log View + Threshold & Cost Config Settings |

---

## 🧪 Running Automated Tests

Run the full backend test suite (`pytest`):
```bash
PYTHONPATH=.:backend ./backend/venv/bin/pytest backend/tests
```

All 26 test cases cover:
- Ingestion validation (VR-1 to VR-6) & row quarantining (ER-1)
- Rule engine decision rules & edge cases (EC-1 null shipping, EC-2 new account, EC-6 extreme velocity anomaly)
- LLM reasoning, grounding checks (BR-7, EC-7), prompt safety (SEC-6), and graceful fallback (ER-2)
- Scoring threshold boundaries (EC-4) & DR-1 label isolation assertion
- Cost calculator formulas (FR-6, BR-5)
- Analyst overrides, 10-char reason check (VR-3), race condition `ALREADY_DECIDED` (EC-5), and immutable audit logging (BR-1)
- Precision, recall, F1, and cost metrics calculation (FR-11–13)
- Role authorization (AuthZ-1, AuthZ-2: Analyst denied 403 on `/config`)

---

## 📢 Known Limitations & Disclosures (AC-9)

1. **Batch Mode for MVP:** Scoring operates on uploaded CSV batches rather than real-time WebSocket/Kafka streaming.
2. **Synthetic Data Realism:** While the synthetic dataset exhibits genuine overlap (verified by the build gate check), synthetic rules do not fully replicate real-world adversarial fraud drift.
3. **Simulated Production Auth:** Simple JWT auth with 2 primary roles (Analyst, Risk Manager) is implemented for demo purposes; production enterprise SSO/MFA is deferred.
