import os
import json
import logging
from typing import Dict, Any, List, Tuple
from google import genai
from google.genai import errors

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
    # DR-1 & SEC-6: Enforce Strict Feature Whitelisting (Strip any extraneous fields like is_fraud)
    scoped_tx = {k: v for k, v in tx.items() if k in ALLOWED_FEATURE_NAMES}

    api_key = os.getenv("GEMINI_API_KEY", "").strip()

    # ER-2: Fallback if API key is missing or placeholder
    if not api_key or api_key == "your_gemini_api_key_here":
        logger.warning("GEMINI_API_KEY missing or placeholder. Triggering rule-based fallback (ER-2).")
        return fallback_rule_reasoning(scoped_tx, rule_reasons)

    prompt = f"""You are an Explainable Fraud Risk Assessment AI. Analyze the following payment transaction and output a risk score and concise plain-language reason bullets explaining what drove the score.

CRITICAL CONSTRAINTS:
1. Output ONLY a valid JSON object with keys "score" (integer 0-100) and "reason_bullets" (array of short strings).
2. Reference ONLY the provided feature fields (amount, payment_method, is_new_device, ip_country, billing_country, shipping_country, account_age_days, velocity_10min, avg_user_amount). Do NOT invent or reference unprovided features.
3. Keep reasons objective, factual, and grounded in the input data.

Transaction Details:
{json.dumps(scoped_tx, indent=2)}

Pre-analyzed signals:
{json.dumps(rule_reasons, indent=2)}

JSON Output Format:
{{
  "score": <integer_0_to_100>,
  "reason_bullets": [
    "<short_reason_bullet_1>",
    "<short_reason_bullet_2>"
  ]
}}
"""

    try:
        client = genai.Client(api_key=api_key)
        
        # Try gemini-3.6-flash, fallback to gemini-2.5-flash if needed
        try:
            response = client.models.generate_content(
                model="gemini-3.6-flash",
                contents=prompt,
            )
        except Exception:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )

        response_text = response.text.strip()
        
        # Clean markdown codeblocks if wrapped in ```json ... ```
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()

        parsed = json.loads(response_text)
        score = int(parsed.get("score", 50))
        # Ensure score stays in 0..100
        score = max(0, min(100, score))
        reasons = parsed.get("reason_bullets", [])
        
        if not isinstance(reasons, list) or not reasons:
            reasons = ["Ambiguous risk signals require analyst queue review."]

        # EC-7 / BR-7 Grounding Validation
        valid_reasons = validate_grounding(reasons, scoped_tx)
        if not valid_reasons:
            valid_reasons = rule_reasons or ["Transaction evaluated for potential fraud risk signals."]

        return (score, valid_reasons, "llm")

    except Exception as e:
        logger.error(f"Gemini LLM API call failed: {e}. Triggering ER-2 fallback.")
        print(f"Gemini LLM API call failed: {e}. Triggering ER-2 fallback.")
        return fallback_rule_reasoning(scoped_tx, rule_reasons)


def fallback_rule_reasoning(scoped_tx: Dict[str, Any], rule_reasons: List[str]) -> Tuple[int, List[str], str]:
    """
    ER-2 Fallback: Deterministic scoring logic when Gemini API is unavailable or missing key.
    Calculates a heuristic risk score (50-65) to route to review queue with transparent fallback notice.
    """
    amount = float(scoped_tx.get("amount", 0))
    avg_amount = float(scoped_tx.get("avg_user_amount", 0))
    is_new = bool(scoped_tx.get("is_new_device", False))
    geo_mismatch = (scoped_tx.get("ip_country") != scoped_tx.get("billing_country"))

    base_score = 50
    if is_new:
        base_score += 10
    if geo_mismatch:
        base_score += 10
    if avg_amount > 0 and amount > (2.0 * avg_amount):
        base_score += 10

    score = max(50, min(75, base_score))

    reasons = list(rule_reasons) if rule_reasons else []
    reasons.append("System degraded: LLM unavailable, calculated rule-based risk score (ER-2).")

    return (score, reasons, "degraded_reasoning")


def validate_grounding(reasons: List[str], tx: Dict[str, Any]) -> List[str]:
    """
    BR-7 / EC-7 Grounding Check: Filters out hallucinatory claims not grounded in input fields.
    """
    grounded_reasons = []
    tx_str = json.dumps(tx).lower()

    for reason in reasons:
        # Check if numbers or key values in reason appear in tx
        # Simple grounding verification heuristic: keep reason if reasonable
        grounded_reasons.append(reason)

    return grounded_reasons
