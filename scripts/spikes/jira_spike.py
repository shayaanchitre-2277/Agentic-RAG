"""
Jira Cloud REST API v3 connectivity spike for Phase 0 (M0.3).

This script performs an isolated, read-only test of Jira Cloud connectivity
using an Atlassian Classic API Token via HTTP Basic Authentication directly
against JIRA_BASE_URL (https://shayaanchitre.atlassian.net).

Endpoints verified:
  1. Current user profile: GET /rest/api/3/myself
     - Verifies HTTP 200, prints accountId and displayName.
  2. Project retrieval:    GET /rest/api/3/project
     - Verifies HTTP 200, prints accessible project keys and names.
  3. Issue search:         GET /rest/api/3/search/jql
     - Parameters: jql="project is not EMPTY ORDER BY updated DESC"
                   (bounded query required by Atlassian Cloud v3)
                   maxResults=5, fields="key,summary,status,issuelinks,updated"
     - Verifies HTTP 200, prints issue keys, summaries, statuses, and issue links.

Security & Hygiene:
  - NEVER logs, prints, or exposes the API token or Authorization headers.
  - Strictly read-only GET requests with a 15-second timeout.
"""

import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

# Use httpx2 or httpx depending on environment availability
try:
    import httpx
except ImportError:
    try:
        import httpx2 as httpx
    except ImportError:
        import requests
        httpx = None

# Load environment variables from .env located at repo root
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ENV_PATH = REPO_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH)

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_USER_EMAIL = os.getenv("JIRA_USER_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

def validate_environment():
    missing = []
    if not JIRA_BASE_URL:
        missing.append("JIRA_BASE_URL")
    if not JIRA_USER_EMAIL:
        missing.append("JIRA_USER_EMAIL")
    if not JIRA_API_TOKEN:
        missing.append("JIRA_API_TOKEN")

    if missing:
        print(f"ERROR: Missing required Jira configuration in .env: {', '.join(missing)}")
        sys.exit(1)

def extract_base_origin(raw_url: str) -> str:
    """Extract standard origin (scheme + netloc), e.g. https://domain.atlassian.net"""
    parsed = urlparse(raw_url.strip())
    if not parsed.scheme or not parsed.netloc:
        return raw_url.strip().rstrip("/")
    return f"{parsed.scheme}://{parsed.netloc}"

def run_jira_spike():
    validate_environment()

    base_url = extract_base_origin(JIRA_BASE_URL)
    user_email = JIRA_USER_EMAIL.strip()
    api_token = JIRA_API_TOKEN.strip()

    print("=" * 75)
    print("Jira Cloud REST API v3 Connectivity Spike (Classic API Token)")
    print("=" * 75)
    print(f"Target Host: {base_url}")
    print(f"User Email:  {user_email}")
    print("Auth Method: HTTP Basic (User Email + Classic API Token - Redacted)")
    print("-" * 75)

    headers = {
        "Accept": "application/json"
    }

    timeout_seconds = 15.0

    # Initialize client with BasicAuth
    if httpx is not None:
        client = httpx.Client(
            auth=httpx.BasicAuth(user_email, api_token),
            headers=headers,
            timeout=timeout_seconds
        )
    else:
        import requests
        client = requests.Session()
        client.auth = (user_email, api_token)
        client.headers.update(headers)

    # 1. Current user profile: GET /rest/api/3/myself
    myself_url = f"{base_url}/rest/api/3/myself"
    print("\n1. Verifying current user profile (GET /rest/api/3/myself)...")
    start = time.perf_counter()
    try:
        resp = client.get(myself_url)
        latency_ms = (time.perf_counter() - start) * 1000

        print(f"   HTTP Status: {resp.status_code} ({latency_ms:.2f} ms)")
        if resp.status_code == 200:
            user_data = resp.json()
            account_id = user_data.get("accountId", "Unknown")
            display_name = user_data.get("displayName", "Unknown")
            active = user_data.get("active", False)
            print(f"   SUCCESS: Authenticated as '{display_name}'")
            print(f"   Account ID: {account_id}")
            print(f"   Active:     {active}")
        else:
            print(f"   FAILED: HTTP {resp.status_code} - {resp.text[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"   NETWORK / CLIENT ERROR: {e}")
        sys.exit(1)

    # 2. Project retrieval: GET /rest/api/3/project
    project_url = f"{base_url}/rest/api/3/project"
    print("\n2. Retrieving accessible projects (GET /rest/api/3/project)...")
    start = time.perf_counter()
    try:
        resp = client.get(project_url)
        latency_ms = (time.perf_counter() - start) * 1000

        print(f"   HTTP Status: {resp.status_code} ({latency_ms:.2f} ms)")
        if resp.status_code == 200:
            projects = resp.json()
            print(f"   SUCCESS: Retrieved {len(projects)} accessible project(s):")
            for p in projects:
                p_key = p.get("key", "N/A")
                p_name = p.get("name", "N/A")
                p_id = p.get("id", "N/A")
                print(f"     - [{p_key}] {p_name} (ID: {p_id})")
        else:
            print(f"   FAILED: HTTP {resp.status_code} - {resp.text[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"   NETWORK / CLIENT ERROR: {e}")
        sys.exit(1)

    # 3. Issue search: GET /rest/api/3/search/jql
    # Note: Jira Cloud v3 enforces bounded queries (e.g. project is not EMPTY)
    search_url = f"{base_url}/rest/api/3/search/jql"
    search_params = {
        "jql": "project is not EMPTY ORDER BY updated DESC",
        "maxResults": 5,
        "fields": "key,summary,status,issuelinks,updated"
    }
    print("\n3. Testing issue search (GET /rest/api/3/search/jql)...")
    print(f"   Query: jql=\"{search_params['jql']}\", maxResults=5")
    start = time.perf_counter()
    try:
        resp = client.get(search_url, params=search_params)
        latency_ms = (time.perf_counter() - start) * 1000

        print(f"   HTTP Status: {resp.status_code} ({latency_ms:.2f} ms)")
        if resp.status_code == 200:
            data = resp.json()
            issues = data.get("issues", [])
            print(f"   SUCCESS: Retrieved {len(issues)} issue(s):")
            for issue in issues:
                key = issue.get("key", "N/A")
                fields = issue.get("fields", {})
                summary = fields.get("summary", "(No Summary)")
                status_name = fields.get("status", {}).get("name", "Unknown")
                issue_links = fields.get("issuelinks", [])
                has_links = len(issue_links) > 0
                print(f"     - Key: {key:<10} | Status: {status_name:<12} | Links: {has_links} ({len(issue_links)}) | Summary: {summary[:40]}")
        else:
            print(f"   FAILED: HTTP {resp.status_code} - {resp.text[:200]}")
            sys.exit(1)
    except Exception as e:
        print(f"   NETWORK / CLIENT ERROR: {e}")
        sys.exit(1)

    print("\n" + "=" * 75)
    print("ALL THREE CHECKS RETURNED HTTP 200: Jira Connectivity Spike Verified!")
    print("=" * 75)

if __name__ == "__main__":
    run_jira_spike()
