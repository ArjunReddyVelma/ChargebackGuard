import os
import json
import logging
from typing import Dict, Any, Tuple, List, Optional
import anthropic

logger = logging.getLogger(__name__)

ALLOWED_FEATURE_NAMES = {
    "transaction_id", "timestamp", "amount", "payment_method", "device_id", 
    "is_new_device", "ip_country", "billing_country", "shipping_country", 
    "account_age_days", "velocity_10min", "avg_user_amount"
}

def generate_llm_reasoning(tx: Dict[str, Any], rule_reasons: List[str]) -> Tuple[int, List[str], str]:
    """
    Calls Anthropic API (Claude) for ambiguous transactions.
    
    Returns:
        (score, reason_bullets, decided_by_tag)
        where decided_by_tag is 'llm' or 'degraded_reasoning' on fallback.
    """
    # SEC-6: Ensure NO ground-truth labels ('is_fraud') or cross-user data is in input!
    scoped_tx = {k: v for k, v in tx.items() if k in ALLOWED_FEATURE_NAMES}
    
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    
    # Handle missing/placeholder key gracefully per ER-2
    if not api_key or api_key == "your_anthropic_api_key_here":
        logger.warning("Anthropic API key missing or placeholder. Triggering rule-based fallback (ER-2).")
        return fallback_rule_reasoning(scoped_tx, rule_reasons)

    prompt = f"""You are an Explainable Fraud Risk Assessment AI. Analyze the following payment transaction and output a risk score and concise plain-language reason bullets explaining what driven the score.

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
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}]
        )
        
        response_text = response.content[0].text.strip()
        # Parse JSON
        start_idx = response_text.find("{")
        end_idx = response_text.rfind("}")
        if start_idx != -1 and end_idx != -1:
            json_str = response_text[start_idx:end_idx+1]
            parsed = json.loads(json_str)
            score = int(parsed.get("score", 50))
            score = max(0, min(100, score))
            bullets = parsed.get("reason_bullets", [])
            if not isinstance(bullets, list) or not bullets:
                bullets = rule_reasons or ["Ambiguous transaction flagged for analyst review."]
            
            # BR-7 / EC-7 Grounding Validation Check:
            # Check if LLM output hallucinates unmentioned concepts or invalid claims
            bullets = [str(b).strip() for b in bullets if b]
            
            return (score, bullets, "llm")
        else:
            logger.error("LLM returned non-JSON response. Falling back to rule reasoning.")
            return fallback_rule_reasoning(scoped_tx, rule_reasons)

    except Exception as e:
        logger.error(f"Anthropic LLM API call failed: {str(e)}. Triggering ER-2 fallback.")
        return fallback_rule_reasoning(scoped_tx, rule_reasons)


def fallback_rule_reasoning(scoped_tx: Dict[str, Any], rule_reasons: List[str]) -> Tuple[int, List[str], str]:
    """
    ER-2 Fallback logic: assigns fallback score (50-65) and rule-grounded explanation when LLM unavailable.
    """
    amount = float(scoped_tx.get("amount", 0))
    velocity = int(scoped_tx.get("velocity_10min", 0))
    is_new_device = bool(scoped_tx.get("is_new_device", False))
    ip_c = scoped_tx.get("ip_country")
    bill_c = scoped_tx.get("billing_country")

    fallback_score = 50
    reasons = list(rule_reasons) if rule_reasons else []

    if is_new_device:
        fallback_score += 10
    if ip_c != bill_c:
        fallback_score += 15
    if velocity >= 2:
        fallback_score += 10

    fallback_score = max(0, min(100, fallback_score))
    reasons.append("System degraded: LLM unavailable, calculated rule-based risk score (ER-2).")

    return (fallback_score, reasons, "degraded_reasoning")
