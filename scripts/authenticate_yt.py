#!/usr/bin/env python3
"""Local OAuth 2.0 helper script to authenticate with YouTube Data API v3 for 'Silicon Verdict'.

Run this script on your local workstation to generate the persistent `token.json`
credentials file with long-lived offline refresh capability.
"""
import logging
import os
import subprocess
import sys
import webbrowser
from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("auth_yt")

# Strict scopes required for video upload, playlist/metadata inspection, and analytics retention reports
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

BASE_DIR = Path(__file__).resolve().parent.parent
CLIENT_SECRETS_FILE = BASE_DIR / "client_secrets.json"
TOKEN_OUTPUT_FILE = BASE_DIR / "data" / "token.json"
TOKEN_LEGACY_FILE = BASE_DIR / "token.json"


def authenticate_local() -> None:
    """Launches local OAuth 2.0 flow, receives user authorization, and stores token.json."""
    logger.info("Initializing YouTube Data API v3 authentication for 'Silicon Verdict'...")

    if not CLIENT_SECRETS_FILE.is_file():
        alt_path = BASE_DIR / "tokens" / "client_secret.json"
        if alt_path.is_file():
            active_secret_file = alt_path
        else:
            logger.error("Required OAuth client secret file not found: %s", CLIENT_SECRETS_FILE)
            sys.exit(1)
    else:
        active_secret_file = CLIENT_SECRETS_FILE

    logger.info("Reading OAuth 2.0 client secrets from: %s", active_secret_file)

    try:
        flow = InstalledAppFlow.from_client_secrets_file(
            str(active_secret_file),
            scopes=SCOPES,
        )

        flow.redirect_uri = "http://localhost:8080/"
        auth_url, _ = flow.authorization_url(prompt="consent", access_type="offline")

        print("\n" + "=" * 80)
        print(">>> GOOGLE OAUTH 2.0 AUTHORIZATION REQUIRED <<<")
        print("Please visit the following URL in your browser to authorize 'Silicon Verdict':")
        print(f"\n{auth_url}\n")
        print("=" * 80 + "\n")

        # Attempt to open default browser automatically on macOS
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", auth_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                webbrowser.open(auth_url)
        except Exception:
            pass

        logger.info("Awaiting authorization callback on http://localhost:8080 ...")

        credentials = flow.run_local_server(
            port=8080,
            prompt="consent",
            access_type="offline",
            open_browser=False,  # Already triggered above
        )

        if not credentials.refresh_token:
            logger.warning(
                "Notice: No refresh_token was returned. If this token expires in 1 hour, "
                "revoke access at https://myaccount.google.com/permissions and run this script again."
            )
        else:
            logger.info("Refresh token successfully acquired!")

        # Serialize complete credentials to data/token.json and token.json
        TOKEN_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TOKEN_OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(credentials.to_json())

        with open(TOKEN_LEGACY_FILE, "w", encoding="utf-8") as f:
            f.write(credentials.to_json())

        # Also sync to tokens/token.json if tokens directory exists
        tokens_dir = BASE_DIR / "tokens"
        if tokens_dir.is_dir():
            with open(tokens_dir / "token.json", "w", encoding="utf-8") as f:
                f.write(credentials.to_json())

        logger.info("SUCCESS: YouTube credentials saved to: %s and %s", TOKEN_OUTPUT_FILE, TOKEN_LEGACY_FILE)
        print("\n" + "=" * 80)
        print(f"[✓] SUCCESS! token.json generated at: {TOKEN_OUTPUT_FILE}")
        print("Your pipeline is now 100% authorized for unattended YouTube uploads and YouTube Analytics reports.")
        print("=" * 80 + "\n")

    except Exception as exc:
        logger.critical("Authentication flow failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    authenticate_local()
