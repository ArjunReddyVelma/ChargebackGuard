# Software Requirements Specification: ChargebackGuard

**An Explainable AI Risk & Fraud Detection Agent**
**Prepared for:** Razorpay AI Buildathon — Track 02: AI Risk Manager
**Version:** 1.0
**Status:** Draft

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional and non-functional requirements for ChargebackGuard, an explainable, defense-only fraud/chargeback risk detection system. It is written to be directly testable — every requirement has an ID and an associated acceptance check.

### 1.2 Scope
ChargebackGuard scores transactions for fraud risk, generates human-readable reason chains, estimates the financial cost of decisions, routes borderline cases to human review, and logs all overrides for auditability. It operates on batch data for this version. It does not block payments, move funds, or act autonomously on any account.

### 1.3 Requirement ID Convention
- `FR-x` = Functional Requirement
- `BR-x` = Business Rule
- `DR-x` = Data Requirement
- `VR-x` = Validation Rule
- `AuthN-x` = Authentication Requirement
- `AuthZ-x` = Authorization Requirement
- `ER-x` = Error Handling Requirement
- `EC-x` = Edge Case
- `SEC-x` = Security Requirement
- `PERF-x` = Performance Requirement
- `AC-x` = Acceptance Criterion

---

## 2. User Roles and Permissions

| Role | Description |
|---|---|
| **Analyst** | Reviews flagged/borderline transactions, can approve or override the system's decision with a required reason. Cannot change system configuration (thresholds, cost values). |
| **Risk Manager** | Has all Analyst permissions, plus can configure risk thresholds, cost assumptions, and view aggregate metrics/dashboards. Cannot modify audit logs. |
| **Auditor (read-only)** | Can view all transactions, scores, reason chains, overrides, and logs. Cannot approve, override, or configure anything. |
| **System/Service Account** | The batch-scoring pipeline itself. Writes scores and reason chains. Cannot be assigned to a human; used only for automated ingestion and scoring jobs. |

### 2.1 Permission Matrix

| Action | Analyst | Risk Manager | Auditor | System |
|---|:---:|:---:|:---:|:---:|
| View transaction + score + reason chain | ✅ | ✅ | ✅ | ✅ |
| Approve / override a flagged transaction | ✅ | ✅ | ❌ | ❌ |
| Configure risk thresholds / cost values | ❌ | ✅ | ❌ | ❌ |
| View aggregate metrics dashboard | ✅ (view only) | ✅ (full) | ✅ (view only) | ❌ |
| View/export audit log | ❌ | ✅ | ✅ | ❌ |
| Modify/delete audit log entries | ❌ | ❌ | ❌ | ❌ |
| Run/trigger batch scoring job | ❌ | ✅ | ❌ | ✅ |

**BR-1:** No role, including Risk Manager, may modify or delete an existing audit log entry. Audit logs are append-only.

---

## 3. Functional Requirements

### 3.1 Ingestion & Scoring

**FR-1:** The system shall accept a batch of transactions as structured input (CSV/JSON) containing, at minimum: transaction ID, timestamp, amount, payment method, device ID, IP country, billing country, shipping country, account age in days, transaction velocity (count in last 10 minutes), and average historical transaction amount for the user.
*Acceptance: A batch file missing any required field is rejected with a specific per-field error (see ER-1).*

**FR-2:** The system shall compute a risk score from 0–100 for every transaction in the batch.
*Acceptance: 100% of valid transactions in a batch receive a non-null integer score in range [0,100].*

**FR-3:** The system shall route each transaction through a rule layer first; only transactions that do not meet a high-confidence rule (clear pass or clear block) shall be routed to the LLM reasoning layer.
*Acceptance: Given a test batch, the system's log shows each transaction tagged as `rule_decided` or `llm_decided`, and the two counts sum to the batch size.*

**FR-4:** The system shall generate a reason chain for every scored transaction, referencing only fields present in that transaction's input data.
*Acceptance: For a sample of 20 scored transactions, every claim in the reason chain text is traceable to an actual field value in that transaction's record.*

**FR-5:** The system shall assign each transaction a routing outcome: `auto-clear`, `auto-block`, or `review-queue`, based on configurable score thresholds.
*Acceptance: A transaction scored below the low threshold routes to auto-clear; above the high threshold routes to auto-block; between the two routes to review-queue.*

### 3.2 Cost Calculation

**FR-6:** For every transaction routed to `review-queue` or `auto-block`, the system shall compute an estimated false-positive cost (assuming the transaction is legitimate) and an estimated false-negative cost (assuming the transaction is fraudulent), using configurable per-unit cost assumptions.
*Acceptance: Both cost figures are present and non-null for every review-queue/auto-block transaction.*

**FR-7:** The system shall aggregate cost estimates across a batch into a portfolio-level summary: total estimated false-positive cost exposure and total estimated false-negative cost exposure.
*Acceptance: The dashboard sum equals the sum of individual transaction cost fields, verified by a reconciliation check.*

### 3.3 Review & Override

**FR-8:** Transactions routed to `review-queue` shall be visible to Analyst and Risk Manager roles in a queue view, sorted by descending risk score by default.
*Acceptance: Queue view lists only `review-queue` transactions; default sort order is verified by descending score.*

**FR-9:** An Analyst or Risk Manager shall be able to record a decision (`confirm-block`, `confirm-clear`) on a review-queue transaction. A reason (free text, minimum 10 characters) is required.
*Acceptance: Submitting a decision without a reason of at least 10 characters is rejected (see VR-3); a valid submission updates the transaction's final status.*

**FR-10:** Every override/decision shall be logged with: transaction ID, original system score, original routing outcome, human decision, reason text, user ID, and timestamp.
*Acceptance: Querying the audit log for any decided transaction returns all seven fields populated.*

### 3.4 Metrics & Reporting

**FR-11:** The system shall compute and display precision, recall, and F1 score against a labeled test set.
*Acceptance: Values are computed via standard formulas and match an independent manual recalculation on a sample.*

**FR-12:** The system shall report a false-positive rate and its associated estimated cost, and a false-negative rate and its associated estimated cost, separately.
*Acceptance: Both rate/cost pairs are displayed and numerically consistent with the underlying confusion matrix.*

**FR-13:** The system shall report the proportion of decisions made by the rule layer vs. the LLM layer.
*Acceptance: The two proportions sum to 100% of the scored batch.*

### 3.5 Configuration

**FR-14:** A Risk Manager shall be able to configure: the low/high score thresholds (FR-5) and the cost-per-unit assumptions (FR-6).
*Acceptance: A configuration change is applied to subsequent scoring runs and does not silently alter past results.*

**FR-15:** All configuration changes shall be logged with the previous value, new value, user ID, and timestamp.
*Acceptance: Configuration change log entries are retrievable and complete for every change made.*

---

## 4. Business Rules

**BR-2:** A transaction may only be in exactly one routing state at a time: `auto-clear`, `auto-block`, or `review-queue`.

**BR-3:** Once a review-queue transaction receives a human decision, its status becomes final (`confirm-block` or `confirm-clear`) and cannot be routed back to `review-queue` automatically. A new review requires an explicit re-submission, itself logged as a new event.

**BR-4:** The system shall never take an autonomous action beyond scoring, explaining, routing, and logging. It shall not initiate a refund, hold funds, suspend an account, or contact a customer. (This is a defense-only, decision-support system per the track's constraints.)

**BR-5:** Cost assumptions (false-positive cost, false-negative cost components) must always be positive numeric values greater than zero; a zero or negative cost input is invalid configuration.

**BR-6:** The low score threshold must always be strictly less than the high score threshold (FR-5/FR-14). Configuration that violates this is rejected.

**BR-7:** Reason chains must never reference a feature value that is null/missing in the source data — if a field is missing, it is excluded from the reasoning, not fabricated.

---

## 5. Data Requirements

### 5.1 Transaction Record Schema

| Field | Type | Required | Notes |
|---|---|---|---|
| `transaction_id` | string (unique) | Yes | Primary key |
| `timestamp` | ISO 8601 datetime | Yes | Must be a valid, parseable datetime |
| `amount` | decimal, > 0 | Yes | Currency assumed INR unless specified |
| `payment_method` | enum (UPI, card, netbanking, wallet) | Yes | |
| `device_id` | string | Yes | Hashed/anonymized identifier |
| `is_new_device` | boolean | Yes | Derived or provided |
| `ip_country` | ISO 3166-1 alpha-2 | Yes | |
| `billing_country` | ISO 3166-1 alpha-2 | Yes | |
| `shipping_country` | ISO 3166-1 alpha-2 | No | Nullable for non-physical goods |
| `account_age_days` | integer, ≥ 0 | Yes | |
| `velocity_10min` | integer, ≥ 0 | Yes | Count of transactions by same user/device in trailing 10 min |
| `avg_user_amount` | decimal, ≥ 0 | Yes | Historical average transaction amount for the user |
| `is_fraud` (label) | boolean | Only in labeled test set | Ground truth, used for metrics only, never fed to the scoring model at inference |

**DR-1:** Ground-truth labels (`is_fraud`) shall never be passed into the scoring/reasoning pipeline as an input feature — only used post-hoc for metrics computation. Leakage of the label into scoring is a critical defect.

**DR-2:** All monetary fields are stored as decimals with two-decimal precision (paise-level for INR).

**DR-3:** All timestamps are stored in UTC; display layer may convert to local time.

### 5.2 Audit Log Schema

| Field | Type | Required |
|---|---|---|
| `log_id` | string (unique) | Yes |
| `transaction_id` | string | Yes |
| `event_type` | enum (score, override, config_change) | Yes |
| `actor_id` | string | Yes |
| `actor_role` | enum (Analyst, Risk Manager, System) | Yes |
| `timestamp` | ISO 8601 datetime | Yes |
| `details` | JSON blob | Yes | Structure varies by event_type, but must be non-empty |

---

## 6. Validation Rules

**VR-1:** `amount` must be a positive decimal; values ≤ 0 are rejected at ingestion with error code `INVALID_AMOUNT`.

**VR-2:** `ip_country`, `billing_country`, and `shipping_country` (when present) must be valid ISO 3166-1 alpha-2 codes; invalid codes are rejected with error code `INVALID_COUNTRY_CODE`.

**VR-3:** Override reason text must be at least 10 characters after trimming whitespace; shorter input is rejected with error code `REASON_TOO_SHORT`.

**VR-4:** `timestamp` must not be in the future relative to ingestion time; future-dated transactions are rejected with error code `INVALID_TIMESTAMP`.

**VR-5:** Configuration threshold values must satisfy `0 ≤ low_threshold < high_threshold ≤ 100`; violations are rejected with error code `INVALID_THRESHOLD_CONFIG`.

**VR-6:** `transaction_id` must be unique within a batch; duplicates are rejected with error code `DUPLICATE_TRANSACTION_ID`, and only the first occurrence is processed.

---

## 7. Authentication (AuthN)

**AuthN-1:** All users (Analyst, Risk Manager, Auditor) must authenticate before accessing any view or endpoint. No anonymous access is permitted.

**AuthN-2:** The System/Service account used for batch scoring jobs authenticates via a distinct service credential, never a human user's credentials.

**AuthN-3:** Failed authentication attempts shall be logged (actor identifier attempted, timestamp, outcome) without logging the submitted password/credential value itself.

**AuthN-4:** Sessions expire after a configurable period of inactivity (default: 30 minutes); expired sessions require re-authentication before any further action.

---

## 8. Authorization (AuthZ)

**AuthZ-1:** Every API endpoint and UI action shall enforce the permission matrix in Section 2.1. A request from a role lacking permission for that action is rejected with HTTP 403 / error code `FORBIDDEN`, not silently ignored.

**AuthZ-2:** An Analyst attempting to change configuration (thresholds, cost values) is rejected per AuthZ-1 (see permission matrix).

**AuthZ-3:** No role may directly edit or delete audit log entries via any interface (see BR-1); any such attempt is rejected with error code `AUDIT_LOG_IMMUTABLE`.

**AuthZ-4:** The Auditor role has read-only access; any attempted write action (override, configuration change) is rejected regardless of endpoint used.

---

## 9. Error Handling

**ER-1:** Ingestion errors (missing required field, invalid batch structure) shall be reported per-row with the specific field and reason, without discarding the entire batch — valid rows are processed and invalid rows are quarantined and reported separately.

**ER-2:** If the LLM reasoning layer is unavailable or times out for a given transaction, the system shall fall back to a rule-only score and reason, flag the transaction as `degraded_reasoning`, and log the fallback event. The transaction shall not be left unscored.

**ER-3:** If cost configuration values are missing at scoring time, cost fields for affected transactions shall be marked `cost_unavailable` rather than defaulting to zero (which would misleadingly imply no cost).

**ER-4:** All rejected records/actions return a structured error containing: error code, human-readable message, and the specific field/value that caused the rejection.

**ER-5:** System-level failures (e.g., database unavailable) shall not corrupt partially-written audit log entries; writes are atomic — either fully recorded or not recorded at all.

---

## 10. Edge Cases

**EC-1:** A transaction with `shipping_country` null (digital goods) shall not have geo-mismatch rules involving shipping country applied; the reason chain must omit shipping-related reasoning rather than treating null as a mismatch.

**EC-2:** A brand-new user (`account_age_days = 0`) with no `avg_user_amount` history shall not trigger an "amount deviates from user average" rule (there is no baseline); this must be handled explicitly, not divide-by-zero or default to a false signal.

**EC-3:** A batch containing zero valid transactions (all rejected at ingestion) shall not crash the scoring pipeline; the system returns an empty result set with the full list of ingestion errors.

**EC-4:** A transaction scored exactly at a threshold boundary (e.g., score == high_threshold) shall be deterministically assigned to one defined side of the boundary (rule: threshold value itself belongs to the review-queue band, not auto-block), and this rule is documented and consistent.

**EC-5:** Two Analysts attempting to submit a decision on the same review-queue transaction concurrently: the system shall accept the first successful submission and reject the second with error code `ALREADY_DECIDED`, not silently overwrite.

**EC-6:** A transaction with velocity_10min far exceeding realistic bounds (e.g., data entry error, such as 10,000) shall be flagged as a data-quality anomaly rather than silently scored as maximal risk without review.

**EC-7:** If the LLM reasoning layer produces a reason chain referencing a feature not present in the transaction (hallucination), the system shall detect this via a post-generation validation check and fall back to a rule-based explanation, logging the discrepancy (see also BR-7).

---

## 11. Security Requirements

**SEC-1:** All PII-adjacent fields (device ID, IP address if collected) shall be stored hashed or tokenized, never in raw reversible form beyond what's operationally required.

**SEC-2:** All data in transit (API calls, dashboard access) shall use TLS 1.2 or higher.

**SEC-3:** All data at rest (transaction records, audit logs) shall be encrypted.

**SEC-4:** Access to raw transaction data and audit logs shall be logged (who accessed what, when), separate from the audit log of business decisions.

**SEC-5:** The system shall not expose any endpoint that allows bulk export of transaction or audit data without Risk Manager or Auditor role verification (AuthZ-1).

**SEC-6:** LLM prompts sent to the reasoning layer shall not include any field beyond what's necessary for that transaction's scoring (no cross-transaction data leakage between customers in a single prompt).

**SEC-7:** The system is strictly defensive; no component of the system shall be capable of generating content that facilitates fraud, evades detection, or targets specific individuals outside the scoring/explanation context.

---

## 12. Performance Requirements

**PERF-1:** Batch scoring of 1,000 transactions (rule layer only, no LLM fallback needed) shall complete within 60 seconds.

**PERF-2:** For transactions routed to the LLM reasoning layer, per-transaction reasoning generation shall complete within 5 seconds on average; a per-transaction timeout of 15 seconds triggers the fallback in ER-2.

**PERF-3:** The metrics dashboard shall load and render precision/recall/F1 and cost summaries for a batch of up to 10,000 scored transactions within 5 seconds.

**PERF-4:** The review queue view shall support pagination and shall not attempt to load more than 100 transactions into a single view at once.

---

## 13. Acceptance Criteria (System-Level)

The system is considered to meet this SRS when:

1. **AC-1:** All Functional Requirements (Section 3) pass their stated acceptance checks against a test batch of at least 500 synthetic transactions with a known, documented fraud rate.
2. **AC-2:** The permission matrix (Section 2.1) is verified by attempting every action from every role and confirming allowed actions succeed and disallowed actions are rejected per AuthZ-1.
3. **AC-3:** Every validation rule (Section 6) is verified with at least one passing and one failing test case.
4. **AC-4:** Every edge case (Section 11) has a corresponding test case demonstrating the specified handling, not a crash or silent incorrect behavior.
5. **AC-5:** Precision, recall, and F1 are reported for the labeled test set, and a manual spot-check of 20 transactions confirms the reported metrics are consistent with actual outcomes (no metric fabrication).
6. **AC-6:** The audit log is demonstrated to be append-only: an attempted edit/delete via any interface is rejected per AuthZ-3.
7. **AC-7:** At least one deliberately induced failure (e.g., LLM layer taken offline) is demonstrated to trigger graceful fallback (ER-2) rather than a scoring failure.
8. **AC-8:** Performance requirements (Section 12) are verified with timed test runs against the stated batch sizes.
9. **AC-9:** The system's writeup/demo discloses at least one documented limitation or known failure mode, consistent with the project's commitment to honest reporting (per the PRD).

---

*End of document.*
