# UI/UX Document: ChargebackGuard

**An Explainable AI Risk & Fraud Detection Agent**
**Prepared for:** Razorpay AI Buildathon — Track 02: AI Risk Manager
**Version:** 1.0
**Status:** Draft

---

## 1. Design Principles

1. **Explain, don't just score.** Every risk number on screen must sit next to its reason — no orphaned numbers.
2. **Calm, not alarming.** This is a risk tool used by analysts all day; avoid aggressive reds/flashing states. Signal severity through hierarchy and clarity, not panic.
3. **Trustworthy over flashy.** Judges and analysts alike should feel this is a serious tool. Prioritize clarity, whitespace, and legible data over decorative UI.
4. **One primary action per screen.** Every screen has a clear main task (upload, decide, configure) — secondary info supports it, never competes with it.
5. **Show your work.** Reason chains, audit logs, and cost estimates are core content, not tucked-away details.

---

## 2. User Roles Recap (drives navigation & permissions)

- **Analyst** — reviews and decides on flagged transactions.
- **Risk Manager** — everything Analyst can do, plus configuration and full metrics access.

(Auditor/System roles exist in the SRS but are out of scope for the MVP UI, per the Architecture Document's Future Work section.)

---

## 3. Information Architecture & Navigation

```
Login
 └── App Shell (persistent left sidebar nav)
      ├── Dashboard (Metrics)         [Analyst: view-only | Risk Manager: full]
      ├── Upload Batch                [both]
      ├── Review Queue                [both]
      │    └── Transaction Detail (drawer/modal)
      ├── Audit Log                   [Risk Manager only]
      └── Settings (Config)           [Risk Manager only]
```

**Navigation pattern:** persistent left sidebar (desktop) with 5 items max, collapsing to a bottom tab bar or hamburger drawer on mobile/tablet (see Section 9). No deep nested menus — everything is reachable in one click from the sidebar, keeping the app easy to demo.

---

## 4. User Journey (primary flow)

**Analyst's day, end to end:**

1. **Log in** → lands on **Dashboard** showing today's batch summary at a glance.
2. Sees a **"12 transactions awaiting review"** prompt → clicks through to **Review Queue**.
3. Queue is sorted by risk score, descending. Clicks the top transaction.
4. **Transaction Detail** opens: sees score, reason chain, cost estimate.
5. Reads the reason chain, decides: Confirm Block or Confirm Clear. Types a reason (min 10 characters).
6. Submits → row disappears from queue, confirmation toast appears.
7. Repeats for remaining queue items, or navigates to **Upload Batch** to run a new batch.

**Risk Manager's additional flow:**

1. From **Dashboard**, reviews precision/recall/F1 and rule-vs-LLM split.
2. Navigates to **Settings** to adjust score thresholds or cost assumptions if numbers look off.
3. Checks **Audit Log** to review recent overrides for quality/consistency.

---

## 5. Screens

### 5.1 Login
- Centered card: email, password, "Log in" button.
- Error state: inline red text under the field that failed ("Invalid email or password"), not a generic toast — helps demo clarity.
- No "forgot password" flow needed for MVP — out of scope, note in writeup.

### 5.2 Dashboard (Metrics)
**Purpose:** at-a-glance system health and performance.

**Layout (top to bottom):**
- **Header row:** batch name/date selector, "Upload New Batch" button (top right, primary action).
- **KPI cards row (4 cards):** Precision | Recall | F1 Score | Transactions Reviewed. Each card: large number, small label, small trend indicator if a prior batch exists.
- **Cost summary panel:** two side-by-side stat blocks — "Estimated False-Positive Cost Exposure" and "Estimated False-Negative Cost Exposure" — each with the ₹ amount and transaction count behind it.
- **Rule vs. LLM split:** simple horizontal bar or donut showing % rule-decided vs. % LLM-decided.
- **Recent activity list:** last 5 decisions made, each row clickable → Transaction Detail.

**Role difference:** Analyst sees this screen read-only (no threshold/cost editing shortcuts); Risk Manager sees an additional "Adjust Settings" link inline near the cost panel.

### 5.3 Upload Batch
**Purpose:** ingest a new transaction batch.

**Layout:**
- Drag-and-drop zone (CSV) with a visible "browse files" fallback link — large, centered, clearly the primary element on the page.
- File requirements text below the drop zone (required columns, format) — collapsible "see required format" details.
- On file select: show filename, row count (once parsed), and a "Start Scoring" button.
- Progress state while scoring runs (see Section 7 — Loading States).
- On completion: summary card — "X transactions scored, Y auto-cleared, Z auto-blocked, W sent to review" with a "Go to Review Queue" button.
- On partial failure: a distinct **"N rows had errors"** expandable panel listing row number + reason (maps to ER-1), so bad data is visible, not hidden.

### 5.4 Review Queue
**Purpose:** the analyst's core workspace.

**Layout:**
- Filter/sort bar at top: sort by score (default: high→low), filter by payment method, filter by decided-by (rule/LLM).
- Table (desktop) / stacked cards (mobile) with columns: Transaction ID, Amount, Score (with a small color-coded pill: e.g. amber for review-band, not red — reserve strong red for very high scores only), Payment Method, Decided By (rule/LLM badge), Time Queued.
- Row click → opens **Transaction Detail** as a right-side drawer (keeps queue context visible, avoids full navigation away).
- Pagination: 25 rows per page (aligns with PERF-4's "no more than 100 at once" — we go tighter for usability).
- Empty state: see Section 7.

### 5.5 Transaction Detail (drawer/modal)
**Purpose:** the moment of decision — the most important screen in the product.

**Layout (top to bottom):**
- Header: Transaction ID, amount, timestamp, payment method.
- **Risk score**, shown prominently with its routing band (auto-clear/auto-block/review) as a labeled pill, not just a raw number.
- **Reason chain** — written as a short bulleted list (e.g., "• New device used for this transaction • IP country (SG) differs from billing country (IN) • 4 transactions from this device in the last 10 minutes"), each bullet tied to a real field, per FR-4.
- **Cost estimate panel:** "If this is fraud and we clear it: ~₹X lost. If this is legitimate and we block it: ~₹Y lost." — framed as a decision aid, not a verdict.
- **Raw transaction fields** in a collapsed "View raw data" accordion — available for analysts who want to double check, not shown by default (keeps focus on the reasoning).
- **Decision panel (only for review-queue transactions):** two buttons — "Confirm Block" / "Confirm Clear" — plus a required reason text field (min 10 chars, live character counter, submit disabled until valid).
- **Audit trail mini-section** (for already-decided transactions): shows who decided, when, and their reason — read-only.

### 5.6 Audit Log (Risk Manager only)
**Purpose:** full transparency/searchability of past decisions and config changes.

**Layout:**
- Filter bar: date range, event type (score/override/config_change), actor.
- Table: Timestamp, Event Type, Actor, Transaction ID (if applicable), Summary of change.
- Row click → expands inline to show full detail JSON in a readable, formatted way (not raw JSON dump — labeled key/value pairs).

### 5.7 Settings (Risk Manager only)
**Purpose:** configure thresholds and cost assumptions.

**Layout:**
- Two clearly labeled sections: "Risk Thresholds" and "Cost Assumptions."
- Threshold section: two sliders or numeric inputs (Low Threshold, High Threshold) with a live visual bar showing the three bands (clear/review/block) updating as you adjust — makes the abstract number tangible.
- Cost section: numeric inputs for false-positive cost components and false-negative cost components, each with a short helper label explaining what it represents.
- Validation inline: if Low ≥ High, show inline error immediately, disable Save (maps to VR-5/BR-6).
- "Save Changes" button — confirmation toast on save, and a note that changes apply to future scoring runs only (maps to FR-14).

---

## 6. Core Components (reusable)

| Component | Used in | Notes |
|---|---|---|
| **KPI Card** | Dashboard | Number + label + optional trend arrow |
| **Score Pill** | Queue, Detail | Color-coded by band; color choice per Section 8 |
| **Reason Chain List** | Detail | Bulleted, icon per bullet type (device/geo/velocity/amount) |
| **Cost Panel** | Detail, Dashboard | Two-value comparison layout |
| **Data Table** | Queue, Audit Log | Sortable headers, consistent row height, hover state |
| **Drawer** | Transaction Detail | Slides from right, keeps background context, dismissible via X or click-outside |
| **Toast** | All screens | Bottom-right, auto-dismiss after 4s, used for save/submit confirmations |
| **Empty State** | Queue, Audit Log | Icon + short message + primary action if relevant |
| **Inline Validation Message** | Forms | Red text directly under the offending field, never a top-of-page generic banner alone |
| **Badge (Rule/LLM)** | Queue, Detail | Small pill distinguishing decided-by source |

---

## 7. Loading, Error, and Empty States

### Loading
- **Batch scoring in progress:** determinate progress bar if row count is known ("Scoring 340 of 1,000..."), not an indefinite spinner — this is a data-heavy operation and users benefit from knowing scale/progress.
- **Dashboard metrics loading:** skeleton cards (gray placeholder blocks matching KPI card shape), not a full-page spinner — keeps layout stable.
- **Queue/table loading:** skeleton rows.

### Error
- **Ingestion errors (ER-1):** never block the whole batch — show "N of M rows processed successfully, X rows had errors" with an expandable error list (row + specific reason).
- **LLM layer degraded (ER-2):** a small, non-alarming inline badge on affected transactions: "Reasoning: rule-based fallback used" — visible but not styled as a failure, since the system handled it gracefully by design.
- **Form validation errors:** always inline, at the field level, in plain language ("Reason must be at least 10 characters" not "VR-3 violation").
- **Network/server error:** a dismissible banner at the top of the affected screen with a "Retry" button; never a raw error code shown to the user without a human-readable message alongside it.

### Empty States
- **Review Queue empty:** friendly message — "No transactions need review right now" with an icon (e.g., a checkmark), and a secondary link to Upload a new batch.
- **Audit Log empty (new deployment):** "No activity yet — actions will appear here once you start reviewing transactions."
- **Dashboard with no batch uploaded yet:** replace KPI cards with a single centered prompt: "Upload your first batch to see metrics" + primary Upload button.

---

## 8. Visual Design System

### 8.1 Typography
- **Font:** a clean, modern system/sans-serif stack (e.g., Inter, or system-ui fallback) — no decorative fonts; this is a data-dense tool.
- **Scale:**
  - Page title: 24px / semi-bold
  - Section heading: 18px / semi-bold
  - Body text: 14px / regular
  - Small/meta text (timestamps, labels): 12px / regular, muted color
  - KPI numbers: 32px / bold

### 8.2 Color Palette
Kept deliberately restrained — this is a risk tool, not a marketing site.

| Purpose | Color | Notes |
|---|---|---|
| Primary brand/action | Deep blue (`#1E3A8A`-ish) or Razorpay-adjacent blue | Buttons, active nav, links |
| Background | Off-white / very light gray (`#F9FAFB`) | Reduces eye strain over long analyst sessions |
| Surface (cards/panels) | White | Clear contrast against background |
| Text primary | Near-black (`#111827`) | |
| Text muted | Gray (`#6B7280`) | Timestamps, helper text |
| Success / auto-clear | Muted green | Never neon |
| Caution / review-band | Amber | Reserved for the review-queue band, not overused |
| Danger / auto-block | Muted red | Used sparingly — only the score pill and block-confirmation, not backgrounds |
| Borders/dividers | Light gray (`#E5E7EB`) | |

**Principle:** color signals *category* (clear/review/block), not *urgency for its own sake*. Avoid saturated red backgrounds or blinking elements — an analyst looking at this all day should not feel alarmed by the UI itself.

### 8.3 Spacing
- Base unit: **4px grid** (4, 8, 12, 16, 24, 32, 48).
- Card padding: 16–24px.
- Section vertical spacing: 32px between major sections on a page.
- Table row height: 48px minimum (comfortable click/tap target).

### 8.4 Iconography
- Simple line icons (e.g., Lucide/Feather-style) — one consistent icon set throughout, no mixing styles.
- Icons always paired with a text label in this product (no icon-only buttons except well-understood ones like "X" to close).

---

## 9. Responsive Behavior

This is primarily an **analyst desktop tool** (risk review is a focused, desk-based task), but should degrade gracefully:

| Breakpoint | Behavior |
|---|---|
| Desktop (≥1024px) | Full sidebar nav, data tables, side-drawer for Transaction Detail |
| Tablet (768–1023px) | Sidebar collapses to icon-only rail (expandable on click); tables remain but with fewer default visible columns (hide "Decided By" behind a column toggle) |
| Mobile (<768px) | Sidebar becomes a bottom tab bar (Dashboard / Queue / Upload / More); tables convert to stacked cards (one transaction per card, key fields only: ID, score pill, amount); Transaction Detail opens as a full-screen view instead of a drawer |

**Note in writeup:** given the buildathon's focus, invest primary polish in desktop; ensure mobile at minimum doesn't break (stacked, scrollable, functional) rather than achieving full mobile parity.

---

## 10. Accessibility

- **Color is never the only signal:** score bands and badges always pair color with a text label (e.g., "Review" not just an amber dot).
- **Contrast:** body text and UI elements meet WCAG AA contrast ratios against their backgrounds.
- **Keyboard navigation:** all interactive elements (buttons, table rows, form fields) reachable and operable via Tab/Enter; the Transaction Detail drawer traps focus while open and returns focus to the triggering row on close.
- **Form labels:** every input has a visible, associated `<label>`, not placeholder-text-only labeling.
- **Screen reader support:** semantic HTML (`<table>`, `<button>`, `<nav>`) over div-soup; ARIA labels on icon-only controls (e.g., close button).
- **Focus indicators:** visible focus rings on all interactive elements, not suppressed for aesthetics.

---

## 11. Interaction Details

- **Toasts** auto-dismiss after 4 seconds but are also manually dismissible; never block interaction with the rest of the page.
- **Destructive-adjacent actions** (Confirm Block on a transaction) do not require a second "are you sure" modal — the reason-text requirement (VR-3) already serves as the deliberate friction/confirmation step, per BR-3's "final decision" rule. Adding a second confirmation would be redundant friction.
- **Drawer vs. modal:** Transaction Detail uses a drawer (not a full modal) specifically so analysts retain visual context of the queue behind it — supports fast, sequential review of multiple transactions.
- **Optimistic UI:** after submitting a decision, the row can be immediately removed from the queue view client-side, with a toast confirming; if the server call fails, the row reappears with an error toast (keeps the queue feeling fast during a demo).

---

## 12. Screens Summary (build checklist)

| Screen | Priority for MVP demo |
|---|---|
| Login | Required |
| Dashboard | Required — this is what judges see first for "proof of metrics" |
| Upload Batch | Required — shows the ingestion story |
| Review Queue | Required — core workspace |
| Transaction Detail | Required — this is the differentiator (reason chain + cost) |
| Audit Log | Nice-to-have — build if time allows, mention in writeup if not |
| Settings | Nice-to-have — can hardcode reasonable defaults and skip full UI if time is short, but keep the config *values* changeable via a config file even if no UI is built |

---

*End of document.*
