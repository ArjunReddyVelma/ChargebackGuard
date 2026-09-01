import os
from google import genai
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

def test_models():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    client = genai.Client(api_key=api_key)
    
    models = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash"]
    for m in models:
        try:
            res = client.models.generate_content(
                model=m,
                contents="Test prompt",
            )
            print(f"✅ Success {m}: {res.text[:30]}")
        except Exception as e:
            print(f"❌ Error {m}: {e}")

if __name__ == "__main__":
    test_models()
