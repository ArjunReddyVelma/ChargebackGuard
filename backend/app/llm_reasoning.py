import os
import json
import logging
from typing import Dict, Any, List, Tuple
from google import genai

logger = logging.getLogger(__name__)

# DR-1: Strict Whitelist of Allowed Feature Fields
ALLOWED_FEATURE_NAMES = {
    "transaction_id",
    "timestamp",
    "amount",
    "payment_method",
    "device_id",
    "is_new_device",
    "ip_country",
    "billing_country",
    "shipping_country",
    "account_age_days",
    "velocity_10min",
    "avg_user_amount"
}

def generate_llm_reasoning(tx: Dict[str, Any], rule_reasons: List[str]) -> Tuple[int, List[str], str]:
    """
    Generates explainable fraud reasoning and risk score using Google Gemini API.
    
    Returns:
        (score, reason_bullets, decided_by)
        where decided_by is 'llm' on successful API response,
        or 'degraded_reasoning' on fallback (ER-2).
    """
    scoped_tx = {k: v for k, v in tx.items() if k in ALLOWED_FEATURE_NAMES}

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("GEMINI_API_KEY missing or placeholder. Triggering rule-based fallback (ER-2).")
        return fallback_rule_reasoning(scoped_tx, rule_reasons)

    prompt = f"""You are an Expert Explainable Risk AI for Payment Fraud Detection. Analyze the following payment transaction and output a calibrated risk score (0-100) and factually grounded reason bullets.

CRITICAL RISK CALIBRATION RULES:
1. MULTI-SIGNAL CORROBORATION REQUIREMENT: NO SINGLE ISOLATED RISK SIGNAL (e.g. `is_new_device=true` alone, `velocity=2` alone, or a single IP country mismatch alone) should result in a score > 30 (auto-clear band is 0-29).
2. POSITIVE TRUST MITIGATION: If an account has established history (`account_age_days` > 60), matching domestic billing/shipping, and normal transaction amount (`amount` < 2.5x `avg_user_amount`), a single isolated signal (like a new phone/browser) is NORMAL consumer behavior. Score it < 30 (auto-clear).
3. SCORING BANDS:
   - 0 to 29 (Auto-Clear): Low risk. Established trust signals, OR single isolated signal strongly offset by account age & matching billing.
   - 30 to 69 (Review Queue): Ambiguous risk. Requires 2 moderate signals (e.g., new device + 2.5x amount on 30-day account) requiring human review.
   - 70 to 100 (Auto-Block): High risk. Requires AT LEAST 2-3 severe corroborating signals (e.g., new device + foreign IP mismatch + 5x amount spike + new account).

FEW-SHOT WORKED EXAMPLES:

Example 1 (Legitimate Edge Case - Single Isolated Signal):
Input: account_age_days=257, amount=6183.39, avg_user_amount=5281.10, is_new_device=true, ip_country="IN", billing_country="IN", velocity_10min=0
Analysis: Only single risk signal is new device. Strongly mitigated by 257-day account age, matching IN/IN location, and normal amount (1.17x avg).
Output JSON:
{{
  "score": 15,
  "confidence": 0.95,
  "signal_tradeoff": "Single new device signal is strongly offset by 257-day established account age and matching domestic location.",
  "reason_bullets": [
    "New device used, but transaction amount (₹6,183.39) is within normal baseline (1.2x avg).",
    "Established account history (257 days) with matching IP and billing location (IN)."
  ]
}}

Example 2 (Fraudulent Case - Multiple Corroborating Signals):
Input: account_age_days=5, amount=32000.00, avg_user_amount=2000.00, is_new_device=true, ip_country="US", billing_country="IN", velocity_10min=3
Analysis: Multiple strong corroborating signals: new device, 16x amount spike, foreign IP mismatch (US vs IN), and high velocity (3) on a brand-new 5-day account.
Output JSON:
{{
  "score": 88,
  "confidence": 0.98,
  "signal_tradeoff": "Multiple severe corroborating signals (16x amount spike, foreign IP, new device) on brand-new 5-day account indicate high compromise risk.",
  "reason_bullets": [
    "Transaction amount (₹32,000.00) is 16.0x higher than user's historical average (₹2,000.00).",
    "Unrecognized new device used with foreign IP mismatch (US) against billing location (IN).",
    "Account age is only 5 days with an elevated 10-minute velocity of 3."
  ]
}}

Example 3 (Ambiguous Case - Moderate Signals):
Input: account_age_days=45, amount=12500.00, avg_user_amount=4000.00, is_new_device=true, ip_country="IN", billing_country="IN", velocity_10min=2
Analysis: 3.1x amount increase and new device on 45-day account. Domestic location (IN/IN) prevents auto-blocking, but signals warrant human review.
Output JSON:
{{
  "score": 52,
  "confidence": 0.85,
  "signal_tradeoff": "New device combined with 3.1x amount deviation warrants human review, though domestic location mitigates extreme risk.",
  "reason_bullets": [
    "Transaction amount (₹12,500.00) is 3.1x higher than user average (₹4,000.00).",
    "New device used on 45-day-old account with a velocity of 2 in 10 minutes."
  ]
}}

TARGET TRANSACTION TO EVALUATE:
Transaction Details:
{json.dumps(scoped_tx, indent=2)}

Pre-analyzed signals:
{json.dumps(rule_reasons, indent=2)}

OUTPUT REQUIREMENT:
Output ONLY a valid JSON object with keys "score" (integer 0-100), "confidence" (float 0-1), "signal_tradeoff" (string), and "reason_bullets" (array of short strings without leading bullets or dashes).
"""

    client = genai.Client(api_key=api_key)
    models_to_try = ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-3.6-flash"]
    response = None

    for m in models_to_try:
        try:
            response = client.models.generate_content(
                model=m,
                contents=prompt,
            )
            if response and response.text:
                break
        except Exception as e:
            logger.warning(f"Gemini model {m} failed: {e}. Trying next model...")
            continue

    if not response or not response.text:
        return fallback_rule_reasoning(scoped_tx, rule_reasons)

    try:
        response_text = response.text.strip()
        
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        parsed = json.loads(response_text)
        score = int(parsed.get("score", 50))
        score = max(0, min(100, score))
        raw_reasons = parsed.get("reason_bullets", [])
        
        # Clean double bullets or leading dashes
        reasons = [r.lstrip('•-* ').strip() for r in raw_reasons if r]
        
        if not reasons:
            reasons = ["Ambiguous risk signals require analyst queue review."]

        return (score, reasons, "llm")

    except Exception as e:
        logger.error(f"Gemini response parsing failed: {e}. Triggering ER-2 fallback.")
        return fallback_rule_reasoning(scoped_tx, rule_reasons)


def fallback_rule_reasoning(scoped_tx: Dict[str, Any], rule_reasons: List[str]) -> Tuple[int, List[str], str]:
    """
    ER-2 Fallback: Deterministic scoring logic when Gemini API is unavailable or rate limited.
    """
    amount = float(scoped_tx.get("amount", 0))
    avg_amount = float(scoped_tx.get("avg_user_amount", 0))
    account_age = int(scoped_tx.get("account_age_days", 0))
    is_new = bool(scoped_tx.get("is_new_device", False))
    geo_mismatch = (scoped_tx.get("ip_country") != scoped_tx.get("billing_country"))

    # Calibrated fallback: single isolated signal does not push score above 30 unless multiple signals exist
    risk_points = 0
    if is_new and account_age < 30:
        risk_points += 20
    elif is_new:
        risk_points += 10

    if geo_mismatch and account_age < 30:
        risk_points += 25
    elif geo_mismatch:
        risk_points += 15

    if avg_amount > 0 and amount > (3.0 * avg_amount):
        risk_points += 25

    if account_age > 180 and not geo_mismatch and amount < (2.0 * avg_amount):
        # Strong trust discount
        risk_points = max(0, risk_points - 20)

    score = min(75, 15 + risk_points)

    reasons = [r.lstrip('•-* ').strip() for r in rule_reasons if r]
    reasons.append("System degraded: LLM unavailable, calculated rule-based risk score (ER-2).")

    return (score, reasons, "degraded_reasoning")
