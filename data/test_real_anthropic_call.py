import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

def test_live_anthropic_api_call():
    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    print(f"Loaded ANTHROPIC_API_KEY: {api_key[:15]}..." if api_key else "No ANTHROPIC_API_KEY found.")

    if not api_key or api_key == "your_anthropic_api_key_here":
        print("❌ ANTHROPIC_API_KEY is currently set to placeholder in backend/.env.")
        print("   To test live Claude API calls, please replace the placeholder in backend/.env with your real key.")
        return False

    client = anthropic.Anthropic(api_key=api_key)
    
    sample_scoped_tx = {
        "transaction_id": "TXN_00002",
        "timestamp": "2026-08-01T10:04:00+00:00",
        "amount": 25400.5,
        "payment_method": "card",
        "device_id": "DEV_AMBIG_7",
        "is_new_device": True,
        "ip_country": "SG",
        "billing_country": "IN",
        "shipping_country": "IN",
        "account_age_days": 12,
        "velocity_10min": 2,
        "avg_user_amount": 1200.0
    }

    prompt = f"""You are an Explainable Fraud Risk Assessment AI. Analyze the following payment transaction and output a risk score and concise plain-language reason bullets explaining what drove the score.

CRITICAL CONSTRAINTS:
1. Output ONLY a valid JSON object with keys "score" (integer 0-100) and "reason_bullets" (array of short strings).
2. Reference ONLY the provided feature fields (amount, payment_method, is_new_device, ip_country, billing_country, shipping_country, account_age_days, velocity_10min, avg_user_amount). Do NOT invent or reference unprovided features.
3. Keep reasons objective, factual, and grounded in the input data.

Transaction Details:
{json.dumps(sample_scoped_tx, indent=2)}

Pre-analyzed signals:
[
  "Unrecognized new device used.",
  "IP country (SG) differs from billing country (IN).",
  "Velocity of 2 transactions in trailing 10 minutes.",
  "Transaction amount (₹25400.50) is 21.2x higher than user's historical average (₹1200.00)."
]

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
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}]
        )
        print("\n✅ LIVE ANTHROPIC API RESPONSE OBJECT:")
        print(response)
        print("\nResponse Raw Text Content:")
        print(response.content[0].text)
        return True
    except Exception as e:
        print(f"❌ Anthropic API call error: {e}")
        return False

if __name__ == "__main__":
    test_live_anthropic_api_call()
