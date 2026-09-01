# System Architecture Document: ChargebackGuard

**An Explainable AI Risk & Fraud Detection Agent**
**Prepared for:** Razorpay AI Buildathon — Track 02: AI Risk Manager
**Version:** 1.0
**Status:** Draft

---

## 1. Design Philosophy

This architecture is scoped for a **2-week buildathon MVP**, not a production banking system. The full SRS (v1.0) specifies enterprise-grade requirements (multi-role auth, encryption at rest, live review UI); this document deliberately implements a **practical subset** that proves the core idea — hybrid rule+LLM scoring with explainability, cost awareness, and an audit trail — without infrastructure that won't get finished or demoed.

**Guiding rule:** every component below must be justifiable by "what does the 5-minute demo need to show." If a piece of infrastructure doesn't directly serve FR-1 through FR-13 or AC-1 through AC-9 from the SRS, it's deferred to "Future Work" (Section 12).

---

## 2. Recommended Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Frontend | **React (Vite) + Tailwind CSS** | Fast to build, minimal boilerplate, good for a dashboard + queue UI in limited time |
| Backend | **Python + FastAPI** | Fast to write, native fit for the ML/LLM-calling code, automatic OpenAPI docs (useful for demo/judges) |
| Database | **SQLite (MVP) → PostgreSQL (if time allows)** | SQLite needs zero setup and is plenty for a batch dataset of a few thousand rows; Postgres is a drop-in upgrade if you want to demo from a hosted instance |
| Rule engine | **Plain Python (pandas + explicit rule functions)** | No need for a rules-engine framework (e.g., Drools) at this scale — hand-written rules are easier to explain to judges and easier to debug |
| LLM reasoning layer | **Anthropic API (Claude)** | Used only for ambiguous-case reasoning and reason-chain generation, called via simple `messages` API, not an agent framework |
| Auth (MVP) | **Simple single-role login (email + password, hashed) using FastAPI + JWT** | Full 4-role AuthN/AuthZ matrix from the SRS is over-engineering for a demo with 1–2 people using it; JWT session is enough to show "authenticated access" without wasted effort |
| Hosting | **Render / Railway (backend) + Vercel (frontend)**, or a single VM if simpler | Free/cheap tiers, fast to deploy, minimal DevOps |
| Monitoring (MVP) | **Structured logging to file/console + a single metrics endpoint** | No need for a full observability stack (Datadog/Grafana) for a batch-processing demo |

**What we are deliberately NOT using for the MVP, and why:**
- No Kafka/message queue — batch processing doesn't need streaming infrastructure.
- No Kubernetes — a single deployed service handles the batch sizes in scope (PERF-1: 1,000 transactions).
- No separate microservices — a single FastAPI app with clear internal modules is easier to build, debug, and explain than a distributed system for this scale.
- No dedicated vector DB — there's no semantic search requirement in the MVP scope.

---

## 3. System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React)                         │
│  ┌───────────────┐  ┌────────────────┐  ┌─────────────────────┐ │
│  │ Upload/Batch   │  │ Review Queue    │  │ Metrics Dashboard    │ │
│  │ View           │  │ View            │  │ View                 │ │
│  └───────┬────────┘  └────────┬────────┘  └──────────┬──────────┘ │
└──────────┼────────────────────┼──────────────────────┼────────────┘
           │                    │                       │
           ▼                    ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                      BACKEND (FastAPI)                            │
│                                                                     │
│  ┌────────────┐   ┌───────────────┐   ┌────────────────────────┐  │
│  │ Ingestion & │──▶│ Rule Engine    │──▶│ LLM Reasoning Layer     │  │
│  │ Validation  │   │ (deterministic)│   │ (ambiguous cases only)  │  │
│  └────────────┘   └───────┬────────┘   └───────────┬────────────┘  │
│                            │                        │               │
│                            ▼                        ▼               │
│                    ┌───────────────────────────────────┐            │
│                    │   Scoring & Routing Service          │            │
│                    │  (assigns final score + routing)     │            │
│                    └───────────────┬───────────────────┘            │
│                                    ▼                                 │
│                    ┌───────────────────────────────────┐            │
│                    │   Cost Calculator                    │            │
│                    └───────────────┬───────────────────┘            │
│                                    ▼                                 │
│                    ┌───────────────────────────────────┐            │
│                    │   Review/Override Service            │◀── Analyst │
│                    └───────────────┬───────────────────┘            │
│                                    ▼                                 │
│                    ┌───────────────────────────────────┐            │
│                    │   Audit Log Service (append-only)    │            │
│                    └───────────────┬───────────────────┘            │
│                                    ▼                                 │
│                    ┌───────────────────────────────────┐            │
│                    │   Metrics Service                    │            │
│                    │  (precision/recall/F1, cost summary) │            │
│                    └───────────────────────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
                 ┌─────────────────────┐
                 │  Database (SQLite/   │
                 │  Postgres)            │
                 │  - transactions        │
                 │  - scores              │
                 │  - reason_chains       │
                 │  - audit_log           │
                 │  - config               │
                 └─────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Maps to SRS |
|---|---|---|
| Ingestion & Validation | Parses uploaded CSV/JSON, applies VR-1 to VR-6, quarantines invalid rows | FR-1, ER-1 |
| Rule Engine | Applies deterministic high-confidence rules; tags transaction `rule_decided` or routes onward | FR-3 |
| LLM Reasoning Layer | Called only for ambiguous cases; generates score + reason chain from Claude API | FR-2, FR-4 |
| Scoring & Routing Service | Merges rule/LLM output into final score, applies threshold routing | FR-5, EC-4 |
| Cost Calculator | Computes FP/FN cost estimates per transaction and aggregates | FR-6, FR-7 |
| Review/Override Service | Serves review queue, accepts analyst decisions, enforces VR-3, EC-5 | FR-8, FR-9 |
| Audit Log Service | Append-only writes for scores, overrides, config changes | FR-10, BR-1 |
| Metrics Service | Computes precision/recall/F1, FP/FN rates and cost, rule-vs-LLM split | FR-11, FR-12, FR-13 |

---

## 4. Data Flow

**Batch scoring flow (primary flow):**

1. User uploads a batch file (CSV) via the Upload view.
2. Backend validates each row (VR-1–VR-6); invalid rows quarantined with reasons (ER-1).
3. Valid transactions pass through the Rule Engine.
   - If a rule confidently decides (clear pass / clear block) → tagged `rule_decided`, skip LLM call.
   - If ambiguous → sent to the LLM Reasoning Layer with only that transaction's relevant fields (SEC-6).
4. LLM returns a risk score + reason chain (or times out → fallback per ER-2).
5. Scoring & Routing Service assigns final score and routing outcome (`auto-clear` / `auto-block` / `review-queue`) per configured thresholds.
6. Cost Calculator attaches FP/FN cost estimates to `review-queue`/`auto-block` transactions.
7. All results are persisted to the database and logged to the Audit Log Service.
8. Review-queue transactions appear in the Review Queue view for analyst action.
9. Analyst decisions flow back through the Review/Override Service → Audit Log.
10. Metrics Service aggregates results for the Dashboard view (recomputed on demand or cached per batch).

**Sequence diagram (simplified):**

```
User → Frontend: upload batch.csv
Frontend → Backend: POST /batches
Backend → Ingestion: validate rows
Ingestion → RuleEngine: valid transactions
RuleEngine → LLMLayer: ambiguous subset only
LLMLayer → ScoringService: score + reason chain
RuleEngine → ScoringService: rule-decided transactions
ScoringService → CostCalculator: routed transactions
CostCalculator → DB: persist scored transactions
ScoringService → AuditLog: log scoring events
Frontend → Backend: GET /queue (review-queue view)
Analyst → Frontend: submit decision
Frontend → Backend: POST /transactions/{id}/decision
Backend → AuditLog: log override event
Frontend → Backend: GET /metrics
Backend → Frontend: precision/recall/F1/cost summary
```

---

## 5. API Design (REST, FastAPI)

| Endpoint | Method | Purpose | Maps to |
|---|---|---|---|
| `/auth/login` | POST | Authenticate user, return JWT | AuthN-1 |
| `/batches` | POST | Upload a batch file for scoring | FR-1 |
| `/batches/{batch_id}` | GET | Get batch status/summary | FR-2 |
| `/transactions` | GET | List scored transactions (filterable by routing outcome) | FR-8 |
| `/transactions/{id}` | GET | Get full detail: score, reason chain, cost | FR-4, FR-6 |
| `/transactions/{id}/decision` | POST | Submit analyst decision + reason | FR-9, VR-3 |
| `/audit-log` | GET | Retrieve audit log (Risk Manager/Auditor only) | FR-10, AuthZ-3 |
| `/metrics` | GET | Precision/recall/F1, cost summary, rule-vs-LLM split | FR-11–FR-13 |
| `/config` | GET/PUT | View/update thresholds and cost assumptions (Risk Manager only) | FR-14, FR-15 |

Kept intentionally RESTful and small — no GraphQL, no separate microservice per endpoint. All endpoints live in one FastAPI app with routers split by concern (`batches.py`, `transactions.py`, `metrics.py`, `config.py`, `auth.py`).

---

## 6. Authentication & Authorization (MVP-scoped)

- **AuthN:** Email + password login, hashed with bcrypt, session via short-lived JWT (matches AuthN-1, AuthN-4 from SRS at a practical scale).
- **AuthZ:** A single `role` field on the user record (`analyst`, `risk_manager`) checked via a FastAPI dependency on protected routes — a lightweight version of the full permission matrix in the SRS, covering the two roles that actually appear in the demo. `auditor` and separate `system` service accounts are documented as future work (Section 12) rather than built, since a live demo won't need them.
- Full enterprise items **not built for MVP**: SSO, MFA, session revocation lists, granular per-field permissions. These are called out explicitly in the demo writeup as "designed for, not implemented," which is more credible than silently skipping them.

---

## 7. Storage

**Tables (SQLite/Postgres):**

- `transactions` — raw ingested fields (per DR schema in SRS Section 5.1)
- `scores` — transaction_id, score, routing_outcome, decided_by (rule/llm), timestamp
- `reason_chains` — transaction_id, reason_text, referenced_fields (JSON)
- `costs` — transaction_id, fp_cost_estimate, fn_cost_estimate
- `decisions` — transaction_id, actor_id, decision, reason_text, timestamp
- `audit_log` — append-only, event_type, actor_id, details (JSON), timestamp
- `config` — key, value, updated_by, updated_at (current values only; history captured via audit_log config_change events)
- `users` — id, email, password_hash, role

**Why relational, not document/NoSQL:** the data is naturally tabular with clear relationships (transaction → score → decision → audit entry), and the metrics computation (precision/recall) is fundamentally a SQL aggregation problem. A document store would add complexity without benefit at this scale.

**DR-1 enforcement (no label leakage):** the `is_fraud` ground-truth column is stored in a separate `test_labels` table, joined only by the Metrics Service — never exposed to the Rule Engine or LLM Reasoning Layer code paths. This is enforced structurally (different table, different access path), not just by convention.

---

## 8. Security (practical subset)

| Control | MVP Implementation |
|---|---|
| Transport security | HTTPS via hosting provider's built-in TLS (Render/Vercel handle this by default) |
| Password storage | bcrypt hashing, never plaintext |
| Data at rest | Acceptable to leave unencrypted-at-rest for a demo on a managed hosting provider's disk; called out as a gap for production in the writeup |
| PII handling | `device_id` treated as an opaque string in the synthetic dataset (already anonymized) — no real PII enters the system at all, since data is synthetic/public |
| LLM prompt hygiene | Each LLM call includes only the single transaction's relevant fields — no batch-wide or cross-user data in one prompt (SEC-6) |
| Secrets | API keys (Anthropic, DB credentials) stored in environment variables, never committed to the repo |

Full production security posture (encryption at rest, access logging, key rotation, SEC-1–SEC-7 in full) is explicitly deferred — noted as future work, not silently ignored.

---

## 9. Deployment

**Simple two-service deployment:**

- **Frontend:** deployed as a static build to Vercel (or Netlify).
- **Backend:** deployed as a single FastAPI service to Render or Railway, with SQLite file (or managed Postgres add-on) attached.
- **Environment config:** `.env` file for API keys and DB connection string, not committed to version control.
- **CI:** optional for a buildathon — a simple GitHub Actions job running tests on push is a nice-to-have, not essential to the demo.

No containers-of-containers, no Kubernetes, no separate staging/prod split — one deployed environment is sufficient and appropriate for a buildathon submission.

---

## 10. Monitoring (MVP-scoped)

- **Structured logs:** every scoring event, override, and config change logs a structured JSON line (also written to `audit_log` table) — this doubles as your audit trail and your debug log.
- **`/health` endpoint:** simple liveness check for the backend.
- **`/metrics` endpoint:** already required by FR-11–FR-13; also useful as a lightweight "is the system behaving" signal during the demo.
- **No dedicated observability stack** (Prometheus/Grafana/Datadog) — unnecessary for a batch-processing demo with no continuous production traffic.

---

## 11. Scalability (documented, not built)

The MVP is explicitly scoped for **batch sizes up to ~10,000 transactions** (per PERF-1, PERF-3 in the SRS). This architecture handles that scale comfortably on a single service instance. For context and to show forward-thinking design in the writeup, here's how it would evolve — without building any of it now:

| If scale grows to... | Change |
|---|---|
| Real-time transaction stream | Introduce a message queue (Kafka/SQS) between ingestion and scoring; move rule engine to a stream processor |
| Millions of transactions/day | Move from SQLite/single Postgres to a partitioned/sharded database; separate read replicas for the metrics dashboard |
| High LLM call volume | Add request batching/caching for the reasoning layer, and consider a smaller fine-tuned model for the rule-adjacent LLM calls to cut cost/latency |
| Multi-tenant (multiple merchants) | Add tenant_id to every table, enforce row-level security |

This section exists so the design is presented as "built right-sized for now, with a clear path forward" — not because any of it needs to be implemented for the buildathon.

---

## 12. Future Work (explicitly deferred)

To keep the MVP honest and finishable, the following are **designed for in the SRS but intentionally not built** in this architecture, and should be stated as such in the demo/writeup:

- Full 4-role AuthN/AuthZ matrix (Auditor, System service account)
- Real-time/streaming scoring
- Encryption at rest, key rotation, access logging separate from business audit log
- Live multi-user review queue with concurrency handling beyond basic first-write-wins (EC-5)
- Dedicated observability/monitoring stack
- Horizontal scaling / containerized deployment

Stating these clearly is itself a credibility signal — it shows the gap between "what we proved" and "what a production system would need" was a deliberate scoping decision, not an oversight.

---

*End of document.*
