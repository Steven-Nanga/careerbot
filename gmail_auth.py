"""Generate a Gmail API refresh token for CareerBot."""

from __future__ import annotations

import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow


SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def main() -> None:
    client_id = os.getenv("GMAIL_CLIENT_ID", "").strip()
    client_secret = os.getenv("GMAIL_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise RuntimeError("Set GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET before running this script.")

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }
    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    flow.redirect_uri = "urn:ietf:wg:oauth:2.0:oob"
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    print("Open this URL in your browser and approve CareerBot:")
    print(auth_url)
    code = input("Paste the authorization code here: ").strip()
    flow.fetch_token(code=code)
    credentials = flow.credentials
    print(json.dumps({"GMAIL_REFRESH_TOKEN": credentials.refresh_token}, indent=2))


if __name__ == "__main__":
    main()
