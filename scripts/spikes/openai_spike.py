"""
OpenAI API connectivity spike for Phase 0 (M0.3).

This script performs an isolated test of OpenAI API connectivity.
It verifies:
1. Presence of OPENAI_API_KEY in .env (without printing or exposing the key)
2. Initialization of the official openai SDK
3. A minimal single-request completion call using gpt-4o-mini
4. Accurate measurement of round-trip latency and safe response inspection
5. Clear error handling for auth failures, quota limits, and model access issues
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

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    print("ERROR: OPENAI_API_KEY is missing from .env")
    sys.exit(1)

def test_openai_connectivity():
    try:
        import openai
        from openai import OpenAI, AuthenticationError, RateLimitError, NotFoundError, APIError
    except ImportError:
        print("ERROR: 'openai' SDK is not installed in the environment.")
        sys.exit(1)

    sdk_version = getattr(openai, "__version__", "unknown")
    print(f"SDK: openai version {sdk_version}")

    # Use cost-effective, standard production model for judge/eval roles
    model_name = "gpt-4o-mini"
    prompt = "Respond with exactly the single word: OK"

    print(f"Testing connectivity with model: {model_name}...")
    start_time = time.perf_counter()

    try:
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=10,
            temperature=0.0,
        )
        latency_ms = (time.perf_counter() - start_time) * 1000

        text = response.choices[0].message.content.strip() if response.choices else ""
        print("SUCCESS: Received response from OpenAI API!")
        print(f"Model: {response.model} (requested: {model_name})")
        print(f"Latency: {latency_ms:.2f} ms")
        print(f"Response: {text}")
        print("\nOpenAI connectivity spike completed successfully.")

    except AuthenticationError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"AUTHENTICATION ERROR after {latency_ms:.2f} ms: Invalid API key or unauthorized.")
        print(f"Details: {e.message}")
        sys.exit(1)
    except RateLimitError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"RATE LIMIT / QUOTA ERROR after {latency_ms:.2f} ms: Insufficient quota or rate limit exceeded.")
        print(f"Details: {e.message}")
        sys.exit(1)
    except NotFoundError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"NOT FOUND ERROR after {latency_ms:.2f} ms: Model '{model_name}' not accessible to this account.")
        print(f"Details: {e.message}")
        sys.exit(1)
    except APIError as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"API ERROR after {latency_ms:.2f} ms: {e.message}")
        sys.exit(1)
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        print(f"UNEXPECTED ERROR after {latency_ms:.2f} ms: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_openai_connectivity()
