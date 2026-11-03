#!/usr/bin/env python3
"""Comprehensive diagnostic tool to verify all Silicon Verdict API credentials.

Performs ultra-lightweight, non-costly probe requests:
- Gemini 2.0 Flash generation
- Pixabay Video API search
- ElevenLabs Voice validation
- YouTube OAuth client_secrets.json schema check
"""
import json
import logging
import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import settings

logging.basicConfig(level=logging.WARNING)

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def test_gemini() -> tuple[bool, str]:
    """Tests Gemini 2.0 Flash with a 5-word generation query."""
    if not settings.GEMINI_API_KEY:
        return False, "GEMINI_API_KEY is missing in .env"
    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents="State exactly five technical words.",
        )
        msg = response.text.strip().replace("\n", " ") if response.text else "Active"
        return True, f"Model {settings.GEMINI_MODEL} responded: '{msg[:40]}'"
    except Exception as exc:
        return False, f"API Error: {str(exc).splitlines()[0]}"


def test_pixabay() -> tuple[bool, str]:
    """Tests Pixabay Video API with a quick search for hardware clips."""
    if not settings.PIXABAY_API_KEY:
        return False, "PIXABAY_API_KEY is missing in .env"
    try:
        import requests
        url = "https://pixabay.com/api/videos/"
        params = {
            "key": settings.PIXABAY_API_KEY,
            "q": "hardware",
            "per_page": 3,
        }
        res = requests.get(url, params=params, timeout=12)
        if res.status_code == 200:
            data = res.json()
            total = data.get("totalHits", len(data.get("hits", [])))
            return True, f"Connection OK ({total} video clips available for 'hardware')"
        return False, f"HTTP {res.status_code}: {res.text[:100]}"
    except Exception as exc:
        return False, f"Connection error: {exc}"


def test_elevenlabs() -> tuple[bool, str]:
    """Tests ElevenLabs API key and validates target Voice ID availability."""
    if not settings.ELEVENLABS_API_KEY:
        return False, "ELEVENLABS_API_KEY is missing in .env"
    try:
        import requests
        voice_id = settings.ELEVENLABS_VOICE_ID
        url = f"https://api.elevenlabs.io/v1/voices/{voice_id}"
        headers = {"xi-api-key": settings.ELEVENLABS_API_KEY}
        res = requests.get(url, headers=headers, timeout=12)
        if res.status_code == 200:
            voice_data = res.json()
            voice_name = voice_data.get("name", "Custom Voice")
            category = voice_data.get("category", "premade")
            return True, f"Voice '{voice_name}' [{category}] verified (ID: {voice_id})"
        elif res.status_code == 404:
            # Fallback check if user API key works generally
            u_res = requests.get("https://api.elevenlabs.io/v1/user", headers=headers, timeout=10)
            if u_res.status_code == 200:
                return False, f"API Key valid, but Voice ID '{voice_id}' not found in account."
            return False, f"Voice ID '{voice_id}' not found (HTTP 404)"
        return False, f"HTTP {res.status_code}: {res.text[:100]}"
    except Exception as exc:
        return False, f"Connection error: {exc}"


def test_youtube_secrets() -> tuple[bool, str]:
    """Validates existence and schema of client_secrets.json."""
    secrets_path = settings.resolve_client_secrets_path()
    if not secrets_path.is_file():
        return False, f"client_secrets.json not found at {secrets_path}"
    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        app_info = data.get("installed") or data.get("web")
        if not app_info:
            return False, "Invalid OAuth format (missing 'installed' or 'web' block)"

        client_id = app_info.get("client_id", "")
        project_id = app_info.get("project_id", "unknown")

        # Check if token.json already exists
        token_path = settings.resolve_token_path()
        token_info = ""
        if token_path.is_file() and token_path.stat().st_size > 10:
            token_info = " | token.json: PRESENT"
        else:
            token_info = " | token.json: PENDING (run authenticate_yt.py)"

        return True, f"Project '{project_id}' | Client ID: ...{client_id[-16:]}{token_info}"
    except Exception as exc:
        return False, f"Invalid JSON in client_secrets: {exc}"


def main():
    print(f"\n{CYAN}{BOLD}{'=' * 75}{RESET}")
    print(f"{CYAN}{BOLD}   SILICON VERDICT: COMPREHENSIVE CREDENTIALS VALIDATION TOOL{RESET}")
    print(f"{CYAN}{BOLD}{'=' * 75}{RESET}\n")

    checks = [
        ("Google Gemini AI", test_gemini),
        ("Pixabay Video API", test_pixabay),
        ("ElevenLabs TTS", test_elevenlabs),
        ("YouTube OAuth Config", test_youtube_secrets),
    ]

    all_passed = True
    results = []

    for name, test_fn in checks:
        passed, details = test_fn()
        status_label = f"{GREEN}[  OK  ]{RESET}" if passed else f"{RED}[FAILED]{RESET}"
        if not passed:
            all_passed = False
        results.append((name, status_label, details, passed))

    # Print Table
    print(f"{'SERVICE / API':<24} | {'STATUS':<17} | DETAILS")
    print("-" * 75)
    for name, status, details, passed in results:
        print(f"{name:<24} | {status} | {details}")
    print("-" * 75)

    if all_passed:
        print(f"\n{GREEN}{BOLD}[✓] ALL CORE CREDENTIALS OPERATIONAL! Ready for video generation.{RESET}")
    else:
        print(f"\n{YELLOW}{BOLD}[!] Some services reported warnings or errors. Check messages above.{RESET}")

    print(f"\n{CYAN}Next Step for YouTube Upload Authorization:{RESET}")
    print(f"  {BOLD}python scripts/authenticate_yt.py{RESET}\n")


if __name__ == "__main__":
    main()
