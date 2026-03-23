"""
One-time Google Calendar OAuth2 authorization script.

Run this ONCE before starting the server:
    cd /Users/triptsachdeva/dobbeaiassignment/backend
    python services/auth_calendar.py

It will open your browser → you sign in → grant access.
Saves google_token.json. The main app uses that token forever (auto-refreshes).
"""
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), "google_credentials.json")
TOKEN_PATH = os.path.join(os.path.dirname(__file__), "google_token.json")
SCOPES = ["https://www.googleapis.com/auth/calendar"]


def main():
    print("=" * 55)
    print("  Dobbe AI — Google Calendar One-Time Authorization")
    print("=" * 55)

    if not os.path.exists(CREDENTIALS_PATH):
        print(f"\nERROR: Not found: {CREDENTIALS_PATH}")
        return

    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
    print("\nOpening browser for Google sign-in...")
    creds = flow.run_local_server(port=8080, open_browser=True)

    with open(TOKEN_PATH, "w") as f:
        f.write(creds.to_json())

    print(f"\nSaved token to: {TOKEN_PATH}")
    print("Done! Google Calendar is authorized.\n")


if __name__ == "__main__":
    main()
