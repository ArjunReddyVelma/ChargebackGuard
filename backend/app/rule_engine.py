from typing import Dict, Any, Tuple, Optional, List

def evaluate_transaction_rules(tx: Dict[str, Any]) -> Tuple[str, Optional[int], Optional[str], Optional[str], List[str]]:
    """
    Evaluates deterministic high-confidence rules for a transaction.
    
    Returns:
        (decision_status, score, routing_outcome, rule_name, reason_bullets)
        where decision_status is 'rule_decided' or 'needs_llm_review'.
    """
    amount = float(tx.get("amount", 0))
    velocity = int(tx.get("velocity_10min", 0))
    is_new_device = bool(tx.get("is_new_device", False))
    ip_country = (tx.get("ip_country") or "").upper()
    billing_country = (tx.get("billing_country") or "").upper()
    shipping_country = (tx.get("shipping_country") or "")
    if shipping_country:
        shipping_country = shipping_country.upper()
    else:
        shipping_country = None  # EC-1: Null for digital goods
    
    account_age_days = int(tx.get("account_age_days", 0))
    avg_user_amount = float(tx.get("avg_user_amount", 0))

    reasons = []

    # EC-6: Data quality anomaly check (e.g., velocity > 500)
    if velocity > 500:
        reasons.append(f"Data quality anomaly detected: unrealistically high 10-minute velocity ({velocity}).")
        return ("rule_decided", 85, "review-queue", "ANOMALY_HIGH_VELOCITY", reasons)

    # 1. Check High-Confidence Fraud Block Rules
    # Geo Mismatch + New Device + High Velocity
    geo_mismatch = (ip_country != billing_country)
    if shipping_country:
        geo_mismatch = geo_mismatch or (shipping_country != billing_country)

    if velocity >= 5:
        reasons.append(f"Extreme transaction velocity: {velocity} transactions in trailing 10 minutes.")
        if is_new_device:
            reasons.append("Transaction originated from an unrecognized new device.")
        if geo_mismatch:
            reasons.append(f"Geographic mismatch detected (IP: {ip_country}, Billing: {billing_country}).")
        return ("rule_decided", 92, "auto-block", "RULE_HIGH_VELOCITY_BLOCK", reasons)

    if is_new_device and geo_mismatch and velocity >= 3 and account_age_days <= 14:
        reasons.append(f"New device on recent account ({account_age_days} days old).")
        reasons.append(f"IP country ({ip_country}) does not match billing country ({billing_country}).")
        reasons.append(f"Elevated velocity: {velocity} transactions in 10 minutes.")
        return ("rule_decided", 88, "auto-block", "RULE_NEW_DEV_GEO_VELOCITY_BLOCK", reasons)

    # 2. Check High-Confidence Clear Pass Rules
    # Established user, normal amount, no new device, no geo mismatch, low velocity
    is_normal_amount = True
    if avg_user_amount > 0 and account_age_days > 0:  # EC-2: explicit check, no divide by zero!
        ratio = amount / avg_user_amount
        if ratio > 3.0 or ratio < 0.1:
            is_normal_amount = False
    
    if (not is_new_device) and (ip_country == billing_country) and velocity <= 1 and account_age_days > 30 and is_normal_amount:
        reasons.append("Transaction matches trusted historical user pattern.")
        reasons.append(f"Verified device and matching billing location ({billing_country}).")
        reasons.append(f"Low transaction velocity ({velocity}) on established account ({account_age_days} days).")
        return ("rule_decided", 5, "auto-clear", "RULE_TRUSTED_USER_CLEAR", reasons)

    # 3. Ambiguous Case -> Route to LLM Reasoning Layer
    # Reasons collected so far to assist LLM context
    if is_new_device:
        reasons.append("Unrecognized new device used.")
    if geo_mismatch:
        reasons.append(f"IP country ({ip_country}) differs from billing country ({billing_country}).")
    if velocity >= 2:
        reasons.append(f"Velocity of {velocity} transactions in trailing 10 minutes.")
    if account_age_days == 0:
        reasons.append("Brand new account (0 days old).")  # EC-2 explicit note
    elif avg_user_amount > 0:
        ratio = amount / avg_user_amount
        if ratio > 2.0:
            reasons.append(f"Transaction amount (₹{amount:.2f}) is {ratio:.1f}x higher than user's historical average (₹{avg_user_amount:.2f}).")

    return ("needs_llm_review", None, None, None, reasons)
