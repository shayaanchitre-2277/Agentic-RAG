"""
Gemini API connectivity spike for Phase 0 (M0.3).

This script performs an isolated test of Gemini API connectivity.
It verifies:
1. Presence of GEMINI_API_KEY in .env (without printing or exposing the key)
2. Initialization of the official google-genai SDK
3. A minimal single-request generation call using gemini-3.8-flash
4. Accurate measurement of round-trip latency and safe response inspection
"""

import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env located at repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = REPO_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY is missing from .env")
    sys.exit(1)

def test_gemini_connectivity():
    try:
        from google import genai
        import google.genai as genai_module
    except ImportError:
        print("ERROR: 'google-genai' SDK is not installed in the environment.")
        sys.exit(1)

    sdk_version = getattr(genai_module, "__version__", "unknown")
    print(f"SDK: google-genai version {sdk_version}")

    # Use currently recommended production model
    model_name = "gemini-3.8-flash"
    prompt = "Respond with exactly the single word: OK"

    print(f"Testing connectivity with model: {model_name}...")
    start_time = time.perf_counter()

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000

        text = response.text.strip() if response.text else ""
        print("SUCCESS: Received response from Gemini API!")
        print(f"Model: {model_name}")
        print(f"Latency: {latency_ms:.2f} ms")
        print(f"Response: {text}")
        print("\nGemini connectivity spike completed successfully.")

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"FAILED after {latency_ms:.2f} ms")
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_gemini_connectivity()
