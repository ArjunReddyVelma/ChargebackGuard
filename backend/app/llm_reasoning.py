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

    client = genai.Client(api_key=api_key)
    
    # Preferred Gemini models list
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
        reasons = parsed.get("reason_bullets", [])
        
        if not isinstance(reasons, list) or not reasons:
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
