import os
import json
from google import genai
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

def test_gemini_models():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    client = genai.Client(api_key=api_key)
    
    prompt = """You are an Explainable Fraud Risk Assessment AI. Analyze the following payment transaction and output a risk score and concise plain-language reason bullets explaining what drove the score.

CRITICAL CONSTRAINTS:
1. Output ONLY a valid JSON object with keys "score" (integer 0-100) and "reason_bullets" (array of short strings).
2. Reference ONLY the provided feature fields (amount, payment_method, is_new_device, ip_country, billing_country, shipping_country, account_age_days, velocity_10min, avg_user_amount). Do NOT invent or reference unprovided features.
3. Keep reasons objective, factual, and grounded in the input data.

Transaction Details:
{
  "transaction_id": "TXN_00002",
  "timestamp": "2026-08-01T10:04:00+00:00",
  "amount": 25400.5,
  "payment_method": "card",
  "device_id": "DEV_AMBIG_7",
  "is_new_device": true,
  "ip_country": "SG",
  "billing_country": "IN",
  "shipping_country": "IN",
  "account_age_days": 12,
  "velocity_10min": 2,
  "avg_user_amount": 1200.0
}

Pre-analyzed signals:
[
  "Unrecognized new device used.",
  "IP country (SG) differs from billing country (IN).",
  "Velocity of 2 transactions in trailing 10 minutes.",
  "Transaction amount (₹25400.50) is 21.2x higher than user's historical average (₹1200.00)."
]

JSON Output Format:
{
  "score": <integer_0_to_100>,
  "reason_bullets": [
    "<short_reason_bullet_1>",
    "<short_reason_bullet_2>"
  ]
}
"""

    models_to_test = ["gemini-3.6-flash", "gemini-2.5-flash"]
    for m in models_to_test:
        try:
            print(f"Testing model '{m}'...")
            res = client.models.generate_content(
                model=m,
                contents=prompt
            )
            print(f"✅ SUCCESS WITH {m}!")
            print(f"Raw Object: {res}")
            print(f"Text Output:\n{res.text}")
            return m, res
        except Exception as e:
            print(f"❌ Model '{m}' failed: {e}")

if __name__ == "__main__":
    test_gemini_models()
