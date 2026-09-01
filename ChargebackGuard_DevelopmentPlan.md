# Development Plan: ChargebackGuard

**An Explainable AI Risk & Fraud Detection Agent**
**Prepared for:** Razorpay AI Buildathon — Track 02: AI Risk Manager
**Version:** 1.0
**Status:** Draft
**Timeline basis:** ~14-day buildathon window

---

## 1. Purpose

This plan converts the PRD, SRS, Architecture, and UI/UX documents into a sequenced, executable roadmap. Every task below traces back to a requirement ID (FR/VR/EC/etc.) or a screen from those documents, so no work is invented and no required work is missed. The goal: **development can start immediately without guessing scope, order, or "done."**

---

## 2. MVP Scope (restated, single source of truth)

**In scope for the buildathon MVP:**
- Batch upload → validation → rule engine → LLM reasoning (ambiguous cases) → scoring → routing → cost calculation → review queue → decision → audit log → metrics dashboard.
- Two roles: Analyst, Risk Manager (simple JWT auth, single-tenant).
- Screens: Login, Dashboard, Upload Batch, Review Queue, Transaction Detail. Audit Log and Settings are stretch goals (Section 8).
- SQLite database, single FastAPI backend, single React frontend, deployed as two services.

**Explicitly out of scope (per PRD Section 10 and Architecture Section 12):**
- Real-time/streaming scoring, live payment gateway integration, autonomous blocking actions.
- Full 4-role AuthZ matrix (Auditor, System account UI), SSO/MFA, encryption at rest, observability stack, horizontal scaling.
- Full mobile parity (functional degrade only, per UI/UX Section 9).

Any request to add scope beyond this list during development should be checked against the PRD/SRS before being accepted — this list is the tie-breaker.

---

## 3. Phases Overview

| Phase | Focus | Approx. Days |
|---|---|---|
| 0 | Setup & scaffolding | Day 1 |
| 1 | Data layer & synthetic dataset | Days 1–2 |
| 2 | Backend core: ingestion, rule engine | Days 2–4 |
| 3 | Backend: LLM reasoning layer + scoring/routing | Days 4–6 |
| 4 | Backend: cost calculator, review/decision, audit log | Days 6–7 |
| 5 | Backend: metrics + config + auth | Days 7–8 |
| 6 | Frontend: shell, auth, upload, dashboard | Days 8–10 |
| 7 | Frontend: review queue + transaction detail | Days 10–11 |
| 8 | Integration testing & bug fixing | Days 11–12 |
| 9 | Stretch goals (Audit Log UI, Settings UI) | Day 12 (if ahead of schedule) |
| 10 | Deployment | Day 13 |
| 11 | Demo prep: video, writeup, polish | Day 14 |

Dependencies are called out explicitly in each phase below — this is not a strict waterfall, but later phases genuinely cannot start meaningfully until their dependencies are done.

---

## 4. Phase 0 — Setup & Scaffolding (Day 1)

**Tasks:**
1. Initialize repo structure: `/backend` (FastAPI), `/frontend` (React + Vite), `/data` (synthetic dataset scripts), `/docs` (this doc set).
2. Set up Python virtual environment, install FastAPI, SQLAlchemy, pydantic, pytest.
3. Set up React + Vite + Tailwind project.
4. Set up SQLite file and initial empty schema migration (using SQLAlchemy models or Alembic).
5. Set up `.env` handling for API keys (Anthropic key, JWT secret) — confirm `.env` is gitignored.
6. Set up a basic CI check (optional but cheap): lint + test run on push.

**Dependencies:** None — this is the starting point.

**Definition of Done (DoD):**
- `backend` runs locally and responds on `/health`.
- `frontend` runs locally and renders a placeholder page.
- Database file created with an empty schema matching Architecture Section 7 table list.
- `.env.example` committed (no real secrets), real `.env` gitignored.

---

## 5. Phase 1 — Data Layer & Synthetic Dataset (Days 1–2)

**Tasks (traces to SRS Section 5, prior dataset discussion):**
1. Write a synthetic dataset generator script producing transactions with the schema in SRS Section 5.1 (`transaction_id`, `timestamp`, `amount`, `payment_method`, `device_id`, `is_new_device`, `ip_country`, `billing_country`, `shipping_country`, `account_age_days`, `velocity_10min`, `avg_user_amount`).
2. Bake in 5 deliberate fraud patterns (per earlier discussion) with **genuine ambiguity** — validate that a rules-only baseline does NOT achieve near-perfect precision/recall (this is a build gate, see below).
3. Generate a labeled test set (`is_fraud` column) stored **separately** from the scoring-input table, per DR-1 (no label leakage).
4. Optionally blend in a public dataset (PaySim) fields for realism, mapped into the same schema.
5. Produce at least 500 rows for MVP testing, with a documented, intentional fraud rate (e.g., 5–10%, not the ultra-rare real-world 0.1% — too rare makes small-batch demos meaningless).

**Dependencies:** Phase 0 complete (repo structure exists).

**Definition of Done:**
- Dataset generator script runs deterministically (seeded) and outputs a valid CSV.
- **Build gate check:** run a naive rules-only baseline against the labeled set; confirm it does NOT hit >95% precision/recall (if it does, patterns are too separable — regenerate with more overlap). This directly protects AC-5 and the SRS's honesty requirement.
- `is_fraud` column verified absent from the scoring-input file path used by the Rule Engine/LLM layer.

---

## 6. Phase 2 — Backend Core: Ingestion & Rule Engine (Days 2–4)

**Tasks (maps to FR-1, FR-3, VR-1–VR-6, ER-1, EC-1, EC-2, EC-3, EC-6):**
1. Build `/batches` POST endpoint: accepts CSV upload.
2. Implement validation layer applying VR-1 through VR-6; quarantine invalid rows with structured errors (ER-1), don't drop the whole batch.
3. Implement the Rule Engine as explicit Python functions (not a framework) covering the deterministic high/low-confidence cases (device mismatch + velocity, geo mismatch, amount anomaly, established-account clear pattern).
4. Handle edge cases explicitly: null `shipping_country` (EC-1), zero `account_age_days`/no `avg_user_amount` baseline (EC-2), empty valid batch (EC-3), anomalous velocity values (EC-6).
5. Tag every transaction `rule_decided` or `needs_llm_review` (feeds Phase 3).
6. Write unit tests for the rule engine covering each rule and each edge case above.

**Dependencies:** Phase 1 (needs a dataset to test against); Phase 0.

**Definition of Done:**
- Uploading the Phase 1 synthetic batch produces per-row validation results matching expectations.
- Every rule has at least one passing and one failing unit test (ties to SRS AC-3).
- Every edge case (EC-1, EC-2, EC-3, EC-6) has a passing test demonstrating correct handling, not a crash.
- Rule engine correctly leaves a meaningful fraction (not 0%, not 100%) of transactions tagged `needs_llm_review` — if it resolves everything itself, the LLM layer has nothing to prove (revisit Phase 1 data if so).

---

## 7. Phase 3 — LLM Reasoning Layer + Scoring/Routing (Days 4–6)

**Tasks (maps to FR-2, FR-4, FR-5, ER-2, EC-4, EC-7, SEC-6, DR-1):**
1. Implement the LLM call for `needs_llm_review` transactions: send only that transaction's relevant fields (SEC-6) to the Anthropic API, request a structured JSON response containing a score (0–100) and a reason chain.
2. Implement a post-generation validation check: confirm every field referenced in the reason chain actually exists in the transaction's input (EC-7, BR-7) — reject/regenerate or fall back to rule-based explanation if not.
3. Implement fallback logic: if the LLM call times out or errors, fall back to a rule-based score/reason and tag `degraded_reasoning` (ER-2) — must not leave a transaction unscored.
4. Implement the Scoring & Routing Service: merge rule-decided and LLM-decided scores into a single final score, apply configured thresholds to assign `auto-clear` / `auto-block` / `review-queue` (FR-5), with deterministic boundary handling (EC-4).
5. Persist scores and reason chains to the database.
6. Confirm structurally that `is_fraud` never enters the LLM prompt or rule engine input (DR-1) — write an explicit test asserting this.

**Dependencies:** Phase 2 (needs rule-tagged transactions as input).

**Definition of Done:**
- Every transaction in a test batch ends with a non-null score and a reason chain that passes the field-grounding check.
- Deliberately inducing an LLM failure (e.g., invalid API key temporarily) demonstrates graceful fallback per ER-2, verified by test (ties to SRS AC-7).
- Boundary-score transaction test confirms deterministic routing per EC-4.
- Automated test confirms `is_fraud` is absent from any LLM prompt payload (DR-1 enforcement, not just convention).

---

## 8. Phase 4 — Cost Calculator, Review/Decision, Audit Log (Days 6–7)

**Tasks (maps to FR-6, FR-7, FR-8, FR-9, FR-10, VR-3, EC-5, BR-1, BR-3):**
1. Implement Cost Calculator: compute FP/FN cost estimates per transaction using configurable cost values (initially hardcoded sensible defaults if Settings UI isn't built yet).
2. Implement `/transactions` GET (list, filterable) and `/transactions/{id}` GET (detail) endpoints.
3. Implement `/transactions/{id}/decision` POST: validate reason length (VR-3), handle concurrent-decision race condition (EC-5 — first write wins, second gets `ALREADY_DECIDED`), mark decision final (BR-3).
4. Implement Audit Log Service as append-only writes — no update/delete code path exists at all for this table (BR-1), not just permission-blocked.
5. Wire scoring events, override events, and (later) config-change events into the audit log.

**Dependencies:** Phase 3 (transactions must be scored before they can be reviewed/decided).

**Definition of Done:**
- Submitting a valid decision updates transaction status and creates an audit log entry with all required fields (transaction ID, original score, routing outcome, decision, reason, actor, timestamp).
- Submitting a decision with a too-short reason is rejected with the correct error code.
- Simulated concurrent decision test confirms second submission is rejected, not silently overwritten (EC-5).
- Attempting to programmatically update/delete an audit log row is impossible (no endpoint or ORM method exists for it) — verified by code review/test.

---

## 9. Phase 5 — Metrics, Config, Auth (Days 7–8)

**Tasks (maps to FR-11–FR-15, AuthN-1–4, AuthZ-1–4, VR-5, BR-5, BR-6):**
1. Implement `/metrics` endpoint: precision, recall, F1 (computed against the separately-stored `is_fraud` labels — never the scoring inputs), FP/FN rate + cost, rule-vs-LLM split.
2. Implement `/auth/login` with bcrypt password check and JWT issuance.
3. Implement role-based dependency checks on protected routes (Analyst vs. Risk Manager) per the permission matrix (Architecture Section 6).
4. Implement `/config` GET/PUT for thresholds and cost values, with validation (VR-5, BR-5, BR-6) and audit logging of changes (FR-15).
5. Seed at least one Analyst and one Risk Manager test user.

**Dependencies:** Phase 4 (metrics need decided transactions; config affects scoring in Phase 3, so config defaults should already exist from Phase 3 — this phase adds the editable interface).

**Definition of Done:**
- `/metrics` output on the Phase 1 test batch is manually spot-checked against 20 transactions and matches (ties to SRS AC-5).
- Login works for both seeded users; wrong password rejected with a clear error, no password logged (AuthN-3).
- An Analyst attempting to hit `/config` PUT is rejected with 403 (AuthZ-1/AuthZ-2), verified by test.
- Invalid threshold config (low ≥ high) is rejected before being saved (VR-5/BR-6), verified by test.

---

## 10. Phase 6 — Frontend: Shell, Auth, Upload, Dashboard (Days 8–10)

**Tasks (maps to UI/UX Sections 5.1, 5.2, 5.3, 6, 7):**
1. Build App Shell: sidebar nav (role-aware — hide Settings/Audit Log for Analyst), responsive collapse behavior per UI/UX Section 9.
2. Build Login screen, wire to `/auth/login`, store JWT, handle invalid-login inline error.
3. Build Upload Batch screen: drag-and-drop, file parse preview, "Start Scoring" call to `/batches`, progress state, completion summary, per-row error panel (ER-1 UI).
4. Build Dashboard screen: KPI cards, cost summary panel, rule-vs-LLM split visual, recent activity list — wired to `/metrics`.
5. Implement shared components first (per UI/UX Section 6): KPI Card, Toast, Empty State, Skeleton loaders — build these before the screens that use them to avoid rework.

**Dependencies:** Phase 5 (needs working `/auth`, `/batches`, `/metrics` endpoints).

**Definition of Done:**
- A user can log in, get redirected to Dashboard, and see real metrics from an uploaded batch.
- Upload flow handles both a clean file and a file with deliberately bad rows, showing both success and error states correctly.
- Skeleton/loading states visible during data fetch, not blank screens or layout jump.
- Role-based nav confirmed: Analyst does not see Settings/Audit Log links at all.

---

## 11. Phase 7 — Frontend: Review Queue + Transaction Detail (Days 10–11)

**Tasks (maps to UI/UX Sections 5.4, 5.5, 6):**
1. Build Review Queue table (desktop) with sort/filter, Score Pill and Rule/LLM Badge components, pagination.
2. Build Transaction Detail drawer: score + routing pill, reason chain list, cost panel, raw data accordion, decision panel with validated reason input, audit trail mini-section for already-decided transactions.
3. Wire decision submission to `/transactions/{id}/decision`, implement optimistic row removal from queue with rollback-on-error (UI/UX Section 11).
4. Build mobile card-stack fallback for the queue table (UI/UX Section 9).

**Dependencies:** Phase 6 (shell, auth, shared components must exist); Phase 4/5 backend endpoints.

**Definition of Done:**
- An analyst can open the queue, click a transaction, read the reason chain (verified it references real fields, not generic text), submit a decision, and see the row disappear with a confirmation toast.
- Attempting to submit a decision with a short reason shows inline validation and blocks submission.
- A second, simulated concurrent decision attempt on the same transaction shows the `ALREADY_DECIDED` error correctly in the UI.
- Empty queue state renders correctly when no transactions are pending review.

---

## 12. Phase 8 — Integration Testing & Bug Fixing (Days 11–12)

**Tasks:**
1. Full end-to-end run: upload a fresh batch → verify scores, reason chains, routing → work through the review queue → check dashboard metrics update → check audit log entries exist.
2. Run through every Acceptance Criterion in SRS Section 13 (AC-1 through AC-9) as a manual test pass, checking off each explicitly.
3. Fix any discovered bugs; re-run the affected phase's automated tests.
4. Cross-check UI against UI/UX doc for consistency (colors, spacing, empty/error states) — a lightweight design QA pass.
5. Performance sanity check: time a 1,000-row batch upload/scoring run against PERF-1 (60s) and PERF-2 (5s avg LLM reasoning) targets.

**Dependencies:** Phases 2–7 substantially complete.

**Definition of Done:**
- All SRS AC-1–AC-9 checked and passing, with any known gaps explicitly documented (not silently ignored) for the writeup.
- No known crash-causing bugs remain in the primary flow (upload → review → decide → dashboard).
- Performance targets met or a documented reason given if not (e.g., "LLM latency depends on API load, average measured at Xs").

---

## 13. Phase 9 — Stretch Goals (Day 12, only if ahead of schedule)

**Tasks (only attempt if Phase 8 is fully done early):**
1. Audit Log screen (UI/UX Section 5.6).
2. Settings screen (UI/UX Section 5.7) — if skipped, config remains editable via a JSON/`.env` file, and this is explicitly noted in the demo writeup as "designed, backend-ready, UI deferred."

**Dependencies:** Phase 8 complete with time to spare.

**Definition of Done:** Same DoD criteria as defined in the UI/UX doc for these screens (Section 5.6/5.7), or explicit written note in the final submission that these are backend-complete/UI-deferred.

---

## 14. Phase 10 — Deployment (Day 13)

**Tasks (maps to Architecture Section 9):**
1. Deploy backend to Render/Railway with environment variables set (Anthropic API key, JWT secret, DB connection).
2. Deploy frontend to Vercel/Netlify, pointed at the deployed backend URL.
3. Run the seed script for demo users and load a demo batch dataset into the deployed environment.
4. Smoke-test the deployed environment end-to-end (not just localhost) — this catches CORS/env-var issues before demo day.

**Dependencies:** Phase 8 complete (stable code); ideally Phase 9 outcomes known.

**Definition of Done:**
- Deployed frontend URL loads, login works, and a full upload → review → decide → dashboard loop works against the deployed backend.
- `/health` endpoint reachable on the deployed backend.
- No secrets committed to the repo (final check).

---

## 15. Phase 11 — Demo Prep (Day 14)

**Tasks:**
1. Record the 5-minute pitch video per the structure discussed earlier: problem → live demo (2–3 transactions scored, reasoned, decided) → metrics (precision/recall, FP cost) → human-override/audit trail proof → architecture diagram + what's next.
2. Finalize the GitHub repo README: setup instructions, architecture diagram (from the Architecture doc), and an explicit "Known Limitations" section (ties to SRS AC-9's honesty requirement).
3. Do a final pass linking this doc set (PRD, SRS, Architecture, UI/UX, this plan) into the repo's `/docs` folder for judges who want to dig deeper.

**Dependencies:** Phase 10 (deployed system needed for a real demo recording).

**Definition of Done:**
- Video recorded, under or at 5 minutes, shows a real (not staged/faked) run against the deployed system.
- README complete and a fresh reader (not you) could set up and run the project from it alone.
- Known Limitations section lists at least: what's stretch-goal-deferred (Section 13), what's architecture-deferred (Architecture Section 12), and one honest model/data limitation (e.g., synthetic data doesn't capture real-world fraud drift).

---

## 16. Priority Tiers (if time runs short, cut in this order)

Should the 14-day window compress, cut from the bottom up — never cut from the top without cutting everything below it first:

1. **Never cut:** Rule Engine + LLM Reasoning + Scoring/Routing + Reason Chain generation (Phases 2–3) — this is the core of the submission.
2. **Never cut:** Cost Calculator + basic Metrics (precision/recall/F1) (Phase 4 partial, Phase 5 partial) — this is what proves rigor per the track's stated bar.
3. **Cut only if forced:** Review Queue + Transaction Detail UI (Phase 7) — could be replaced by a well-formatted notebook/CLI output for the demo if the UI isn't ready, though this weakens the "real system" impression significantly.
4. **Cut freely:** Audit Log UI, Settings UI (Phase 9) — backend logic can exist without UI; mention as future work.
5. **Cut freely:** Full responsive/mobile polish (UI/UX Section 9) — desktop-only demo is acceptable.
6. **Cut only as a last resort:** Deployment (Phase 10) — a well-recorded localhost demo is a fallback, but a live deployed link is significantly more credible to judges.

---

## 17. Milestone Summary

| Milestone | Target Day | Signals |
|---|---|---|
| M1: Dataset + Rule Engine working | Day 4 | Can run a batch through validation + rules and get sensible, testable output |
| M2: Full scoring pipeline working (rules + LLM + routing + cost) | Day 6 | End-to-end score → reason → cost, no UI yet, testable via API/scripts |
| M3: Review + audit loop working | Day 7 | Can simulate a full decision cycle with audit trail, via API |
| M4: Metrics + auth working | Day 8 | Can log in, pull real precision/recall from a batch, roles enforced |
| M5: Core UI complete | Day 11 | Full flow usable end-to-end in the browser |
| M6: Tested & deployed | Day 13 | Stable, deployed, smoke-tested |
| M7: Demo-ready | Day 14 | Video + README + docs finalized and submitted |

---

*End of document.*
