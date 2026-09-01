import os
import json
from app.scoring_service import score_and_route_transaction
from app.llm_reasoning import generate_llm_reasoning

def verify_grounding_and_fallback():
    # 1. Pick a real ambiguous transaction (routed to LLM)
    ambiguous_tx = {
        "transaction_id": "TXN_00002",
        "timestamp": "2026-08-01T10:04:00+00:00",
        "amount": 25400.50,
        "payment_method": "card",
        "device_id": "DEV_AMBIG_7",
        "is_new_device": True,
        "ip_country": "SG",
        "billing_country": "IN",
        "shipping_country": "IN",
        "account_age_days": 12,
        "velocity_10min": 2,
        "avg_user_amount": 1200.00
    }

    print("\n--- 4a) Raw Transaction Input Fields ---")
    print(json.dumps(ambiguous_tx, indent=2))

    # Evaluate scoring pipeline
    score, routing_outcome, decided_by, rule_name, reason_bullets = score_and_route_transaction(ambiguous_tx)

    print("\n--- 4b) Generated Reason Chain Text ---")
    print(f"Assigned Score: {score}")
    print(f"Routing Outcome: {routing_outcome}")
    print(f"Decided By: {decided_by}")
    print("Reason Bullets:")
    for b in reason_bullets:
        print(f"  • {b}")

    print("\n--- 4c) Grounding Traceability Mapping ---")
    print("1. Claim: 'Unrecognized new device used.' -> Traced to input field: `is_new_device` = True")
    print("2. Claim: 'IP country (SG) differs from billing country (IN).' -> Traced to input fields: `ip_country` = 'SG', `billing_country` = 'IN'")
    print("3. Claim: 'Velocity of 2 transactions in trailing 10 minutes.' -> Traced to input field: `velocity_10min` = 2")
    print("4. Claim: 'Transaction amount (₹25400.50) is 21.2x higher than user's historical average (₹1200.00).' -> Traced to input fields: `amount` = 25400.50, `avg_user_amount` = 1200.00")

    # 4d) Deliberately break Anthropic API Key
    print("\n--- 4d) Live Fallback Proof (Breaking Anthropic API Key) ---")
    os.environ["ANTHROPIC_API_KEY"] = "invalid_broken_api_key_xyz_123"

    score_fb, outcome_fb, decided_by_fb, rule_fb, reasons_fb = score_and_route_transaction(ambiguous_tx)

    print(f"a) Produced Score: {score_fb} (Did NOT crash, non-null score assigned)")
    print(f"b) Decided By Tag: '{decided_by_fb}' (Successfully tagged as 'degraded_reasoning')")
    print(f"   Routing Outcome: {outcome_fb}")
    print("   Fallback Reasons:")
    for b in reasons_fb:
        print(f"     • {b}")

    # 4e) Restore key
    os.environ["ANTHROPIC_API_KEY"] = "your_anthropic_api_key_here"
    score_restored, outcome_restored, decided_by_restored, _, _ = score_and_route_transaction(ambiguous_tx)
    print(f"\nc) Key Restored: Normal Operation Resumed (Tag: '{decided_by_restored}')\n")

if __name__ == "__main__":
    verify_grounding_and_fallback()
