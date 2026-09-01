# Product Requirements Document: ChargebackGuard

**An Explainable AI Risk & Fraud Detection Agent**
**Prepared for:** Razorpay AI Buildathon — Track 02: AI Risk Manager
**Version:** 1.0
**Status:** Draft

---

## 1. Problem Statement

Fraud and chargeback detection systems in payments today are largely black boxes. They output a risk score (e.g., "0.87 fraud probability") with no explanation of *why* a transaction was flagged. This creates three concrete problems:

1. **Risk teams can't act with confidence.** A score alone doesn't tell an analyst whether to block, review, or approve — they need to know *what specifically* is suspicious.
2. **False positives carry a hidden cost.** Every legitimate transaction wrongly blocked is a real customer and real revenue lost, but most systems don't measure or surface this cost — they optimize for catching fraud, not for the total cost of being wrong.
3. **Black-box decisions are hard to audit or improve.** Without a reasoning trail, teams can't tell whether the model is right for the right reasons, and human reviewers have no way to give structured feedback that improves the system over time.

**ChargebackGuard** addresses this by producing not just a risk score, but a transparent reasoning chain, an estimated cost of being wrong, and a human-in-the-loop feedback mechanism — for defensive fraud/chargeback detection only.

---

## 2. Target Users

| User | Need |
|---|---|
| **Risk & fraud analysts** (primary) | A ranked queue of flagged transactions with clear, actionable reasons — not just scores — so they can make fast, confident decisions. |
| **Merchant risk/finance teams** | Visibility into why transactions are blocked and the financial impact of both fraud caught and false positives incurred. |
| **Buildathon evaluators** (for this submission) | A system that demonstrates real precision/recall rigor, explainability, and responsible human-in-the-loop design — not an autonomous black box. |

---

## 3. Goals

1. Detect fraudulent transactions with measurable precision and recall on a held-out test set.
2. Explain every flagged (and borderline) decision in plain language, tracing which signals drove the score.
3. Quantify the cost of errors — both missed fraud and false positives — so risk decisions can be weighed against real business cost, not accuracy alone.
4. Support human override with structured feedback logging, so the system is auditable and improvable, never fully autonomous.

### Non-Goals
- This is **not** a payment-blocking system in production — it is a decision-support and scoring system.
- This is **not** a generative/offensive tool of any kind — detection and explanation only.

---

## 4. Core Features

### 4.1 Risk Scoring Engine
- Hybrid architecture: fast deterministic rules for clear-cut cases (very high/very low risk) + LLM-assisted reasoning for ambiguous cases.
- Every transaction receives a risk score (0–100).

### 4.2 Reason Chain Generator
- For every scored transaction, output a short, plain-language explanation of which signals contributed and how (e.g., "new device + shipping/billing country mismatch + 4 transactions in 10 minutes").
- Reason chains must be traceable to specific input features — no unsupported claims.

### 4.3 Cost Calculator
- For every flagged transaction, estimate the cost of a false positive (lost legitimate revenue + friction) vs. the cost of a false negative (chargeback fee + transaction amount).
- Aggregate into a portfolio-level "cost of errors" metric.

### 4.4 Human-in-the-Loop Review Queue
- Borderline-risk transactions route to a review queue.
- Human overrides are logged with the original score, the human's decision, and the stated reason — forming a feedback dataset.

### 4.5 Metrics Dashboard
- Precision, recall, F1 on the labeled test set.
- False-positive rate with estimated cost.
- Breakdown of decisions by rule-layer vs. LLM-layer origin.

---

## 5. MVP Scope

To keep the MVP focused, the following are **in scope** for the first build:

- Batch scoring of a static synthetic/public dataset (not real-time streaming).
- Rule layer + LLM reasoning layer for ambiguous cases.
- Reason chain generation for every transaction.
- Cost calculator with configurable cost assumptions.
- A simple review queue simulation (no live human reviewers — simulated overrides for demo purposes).
- A single dashboard view showing metrics and example flagged transactions.

**Explicitly out of scope for MVP** (see Section 10).

---

## 6. User Stories

1. **As a risk analyst**, I want to see a risk score and a plain-language reason for every flagged transaction, so I can decide whether to block, review, or approve it without digging through raw data.
2. **As a risk analyst**, I want borderline cases routed to a review queue instead of auto-blocked, so I don't lose legitimate customers to an overconfident model.
3. **As a risk analyst**, when I override a model decision, I want my override and reason logged, so the system has a record for future improvement.
4. **As a finance/risk manager**, I want to see the estimated cost of false positives and false negatives, so I can judge whether the model's risk threshold is set appropriately for the business.
5. **As a risk manager**, I want a breakdown of how many decisions came from simple rules vs. LLM reasoning, so I understand where the system's complexity is actually adding value.
6. **As an evaluator**, I want to see precision/recall and an honest list of failure cases, so I can trust the reported numbers aren't cherry-picked.

---

## 7. Success Metrics

| Metric | Target for MVP |
|---|---|
| Precision on labeled test set | Reported honestly; no fixed target — must be measured and disclosed, including trade-offs vs. recall |
| Recall on labeled test set | Same as above |
| False-positive cost visibility | 100% of flagged transactions have a cost estimate attached |
| Reason chain coverage | 100% of scored transactions have a traceable, non-generic explanation |
| Review queue routing | Borderline cases (defined by a configurable score band) are routed to review, not auto-decided |
| Audit trail completeness | Every override is logged with original score, human decision, and reason |

Note: precision/recall are **reported, not gamed**. A key evaluation criterion for this project is honesty of the metrics on a genuinely ambiguous dataset, not an inflated number from an easy dataset.

---

## 8. Assumptions

- A synthetic or public dataset (e.g., PaySim, IEEE-CIS) can be adapted or augmented to include the device/geo/velocity-style features needed for meaningful reason chains.
- The LLM reasoning layer is used for scoring/classification/explanation, not for autonomous fund movement or account actions.
- "Human override" is simulated for the MVP demo, since there is no live analyst team in this project's timeline.
- Cost assumptions (e.g., ₹ value of a lost legitimate customer, chargeback fee amount) are configurable estimates, clearly labeled as assumptions, not verified business data.
- The system operates on batch data for MVP; real-time scoring is a future extension.

---

## 9. Risks

| Risk | Mitigation |
|---|---|
| Synthetic data is too easily separable, making precision/recall look artificially strong | Deliberately design overlapping/ambiguous cases between fraud and legitimate classes; validate that a rules-only baseline underperforms the full system |
| LLM reasoning layer adds latency/cost without adding real accuracy | Measure and report rules-only vs. rules+LLM performance separately to prove the LLM layer earns its place |
| Reason chains sound plausible but aren't actually grounded in the input features (LLM hallucination) | Constrain the LLM prompt to only reference provided feature values; spot-check a sample of reason chains against raw data |
| Over-scoping the MVP (real-time, live review UI, production security) delays a working demo | Explicitly restrict MVP to batch scoring + simulated review (see Section 10) |
| Class imbalance (fraud is rare) skews precision/recall reporting | Use appropriate metrics (e.g., precision/recall/F1, not raw accuracy) and disclose the class balance of the test set |
| Cost estimates are seen as arbitrary/unconvincing | Clearly label all cost inputs as configurable assumptions, not claimed real business figures |

---

## 10. Out of Scope (MVP)

The following are intentionally excluded to keep the MVP focused:

- Real-time/streaming transaction scoring
- Live production integration with any payment gateway
- A fully built human reviewer UI/tooling (a simulated review log is sufficient)
- Automated blocking or fund-holding actions (system is decision-support only)
- Multi-model ensembling or extensive hyperparameter tuning
- User authentication, role-based access control, or multi-tenant support
- Mobile app or non-web interface
- Any offensive fraud-generation capability (this system is strictly defensive)

---

## 11. Acceptance Criteria

The MVP is considered complete when:

1. **Scoring:** Given a batch of transactions, the system outputs a risk score (0–100) for every transaction.
2. **Explainability:** Every scored transaction has an accompanying reason chain that references specific, real input features (no generic or unsupported explanations).
3. **Metrics:** The system reports precision, recall, and F1 on a held-out labeled test set, along with a breakdown of rule-layer vs. LLM-layer decisions.
4. **Cost calculation:** Every flagged transaction has an associated estimated cost (false-positive or false-negative), and an aggregate portfolio-level cost summary is displayed.
5. **Review routing:** Transactions within a defined borderline score band are routed to a review queue rather than auto-decided.
6. **Audit trail:** All simulated human overrides are logged with the original score, override decision, and stated reason, retrievable for review.
7. **Honesty check:** The writeup/demo explicitly discloses at least one category of failure case or limitation the system does not handle well.
8. **Demo:** A 5-minute walkthrough shows at least 2–3 real scored transactions end-to-end (score → reason chain → cost estimate → routing decision).

---

*End of document.*
