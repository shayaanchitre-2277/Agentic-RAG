"""
Gmail read-only connectivity spike for Phase 0 (M0.3).

This script performs an isolated test of Gmail API read-only connectivity.
It verifies:
1. Presence of credentials/gmail_oauth_client.json
2. OAuth 2.0 InstalledAppFlow / token refresh using credentials/token.json
3. Narrow read-only scope: https://www.googleapis.com/auth/gmail.readonly
4. Retrieval of safe metadata (id, date, from, subject) for up to 5 messages.
5. Strict redaction: does NOT download or log full email bodies.

Usage:
  python scripts/spikes/gmail_spike.py
"""

import os
import sys
from pathlib import Path

# Scopes: Request exclusively read-only access
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# Path configurations (Project root relative)
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CREDENTIALS_DIR = REPO_ROOT / "credentials"
CLIENT_SECRETS_FILE = CREDENTIALS_DIR / "gmail_oauth_client.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"


def check_prerequisites():
    """Verify prerequisites and return guidance if missing."""
    if not CLIENT_SECRETS_FILE.exists():
        print(f"ERROR: OAuth client secrets file not found at: {CLIENT_SECRETS_FILE}")
        print("\nPlease follow these manual setup steps:")
        print("1. Go to Google Cloud Console -> APIs & Services -> Credentials.")
        print("2. Create an OAuth 2.0 Client ID (Application type: Desktop app).")
        print("3. Download JSON and save it as: credentials/gmail_oauth_client.json")
        print("4. Ensure 'Gmail API' is enabled in your Google Cloud Project.")
        print("5. Configure OAuth Consent Screen in 'Testing' mode and add your test user email.")
        sys.exit(1)


def get_credentials():
    """Obtain valid user credentials from storage or run OAuth flow."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            print(f"Warning: Failed to load existing token.json: {e}")
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired access token using refresh_token...")
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, "w", encoding="utf-8") as token_out:
                    token_out.write(creds.to_json())
                print("Token refreshed successfully.")
            except Exception as e:
                print(f"Token refresh failed: {e}. Initiating interactive login...")
                creds = None

        if not creds:
            print("Initiating local OAuth 2.0 flow...")
            print("A browser window will open for authentication.")
            print(f"Scope requested: {SCOPES}")
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(CLIENT_SECRETS_FILE), SCOPES
                )
                creds = flow.run_local_server(port=0)
                # Persist credentials for subsequent runs
                CREDENTIALS_DIR.mkdir(parents=True, exist_ok=True)
                with open(TOKEN_FILE, "w", encoding="utf-8") as token_out:
                    token_out.write(creds.to_json())
                print(f"Credentials saved to: {TOKEN_FILE}")
            except Exception as e:
                print(f"ERROR during OAuth flow: {e}")
                sys.exit(1)

    return creds


def test_gmail_connectivity(creds):
    """Call Gmail API messages.list and get metadata for a few messages."""
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    try:
        service = build("gmail", "v1", credentials=creds)

        # Print granted scopes
        granted_scopes = getattr(creds, "scopes", None) or SCOPES
        print("SUCCESS: Gmail API client initialized.")
        print(f"Granted Scopes: {granted_scopes}")

        # List up to 5 messages
        print("\nQuerying recent messages (metadata only)...")
        results = service.users().messages().list(userId="me", maxResults=5).execute()
        messages = results.get("messages", [])

        if not messages:
            print("No messages found in the mailbox.")
            return

        print(f"Found {len(messages)} messages. Inspecting safe headers:\n")
        print(f"{'Message ID':<18} | {'Date':<30} | {'From':<30} | {'Subject'}")
        print("-" * 110)

        for msg_summary in messages:
            msg_id = msg_summary["id"]
            # Fetch only minimal metadata headers to strictly avoid downloading body
            msg = service.users().messages().get(
                userId="me",
                id=msg_id,
                format="metadata",
                metadataHeaders=["Subject", "From", "Date"]
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            subject = headers.get("Subject", "(No Subject)")
            sender = headers.get("From", "(Unknown Sender)")
            date = headers.get("Date", "(Unknown Date)")

            # Redact email addresses slightly for terminal privacy if desired, or truncate long strings
            clean_from = sender[:28] + ".." if len(sender) > 30 else sender
            clean_subject = subject[:45] + ".." if len(subject) > 47 else subject
            clean_date = date[:28]

            print(f"{msg_id:<18} | {clean_date:<30} | {clean_from:<30} | {clean_subject}")

        print("\nGmail read-only connectivity test completed successfully.")

    except HttpError as error:
        print(f"Gmail API HTTP error: {error}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error querying Gmail API: {e}")
        sys.exit(1)


def main():
    check_prerequisites()
    creds = get_credentials()
    test_gmail_connectivity(creds)


if __name__ == "__main__":
    main()
