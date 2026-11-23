#!/usr/bin/env python3
"""Checks what a batch needs before it starts and says what to fix (exit 1 if something blocks it).

  python scripts/health_check.py            # prints a table
  python scripts/health_check.py --notify   # also sends a notification when something is wrong

Checks: YouTube token (refreshes it, so a revoked or expired one shows up now and not in the middle of an upload), ElevenLabs credits, Gemini key, banked scripts, prices age, free disk.
"""
import argparse
import shutil
import sys
from pathlib import Path
from typing import Callable, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

OK, WARN, FAIL = "ok", "warn", "FAIL"
Check = Tuple[str, str, str]  # status, name, detail


def youtube() -> Check:
    try:
        from services.youtube import YouTubeService
        YouTubeService().get_authenticated_client()
        return OK, "YouTube token", "valid (refreshed)"
    except Exception as exc:  # noqa: BLE001
        text = str(exc)
        hint = " -> renew with scripts/authenticate_yt.py (guide/publishing.md)" if "invalid_grant" in text or "refresh" in text.lower() else ""
        return FAIL, "YouTube token", text[:120] + hint


def elevenlabs() -> Check:
    from config.settings import settings
    if not settings.ELEVENLABS_API_KEY:
        return FAIL, "ElevenLabs", "ELEVENLABS_API_KEY is missing"
    try:
        import requests
        r = requests.get("https://api.elevenlabs.io/v1/user/subscription", headers={"xi-api-key": settings.ELEVENLABS_API_KEY}, timeout=15)
        if r.status_code != 200:
            return WARN, "ElevenLabs", f"subscription not readable (HTTP {r.status_code}); the key may lack the user_read permission"
        d = r.json()
        left = d["character_limit"] - d["character_count"]
        need = 4 * 1100  # about 1100 characters of narration per video
        return (OK if left >= need else FAIL), "ElevenLabs credits", f"{left:,} characters left (a batch of 4 needs about {need:,})"
    except Exception as exc:  # noqa: BLE001
        return WARN, "ElevenLabs", f"could not check: {exc}"


def gemini() -> Check:
    from config.settings import settings
    return (OK, "Gemini key", "set") if settings.GEMINI_API_KEY else (FAIL, "Gemini key", "GEMINI_API_KEY is missing")


def bank() -> Check:
    from services.story_bank import ready_by_format
    stock = ready_by_format()
    total = sum(stock.values())
    return (OK if total >= 8 else WARN), "Banked scripts", f"{total} ready ({', '.join(f'{k} {v}' for k, v in sorted(stock.items()) if v) or 'none'}): the fallback for a failed slot"


def prices() -> Check:
    from services.prices import age_days, load_prices
    try:
        p = load_prices()
    except Exception as exc:  # noqa: BLE001
        return WARN, "Prices", f"none ({exc}): no 'Every X' video"
    age = age_days(p)
    return (OK if age <= 3 else WARN), "Prices", f"{p['date']} ({age} day(s) old; 'Every X' videos need at most 3)"


def disk() -> Check:
    free = shutil.disk_usage(BASE_DIR).free / 1e9
    return (OK if free >= 10 else FAIL if free < 3 else WARN), "Free disk", f"{free:.1f} GB (a batch writes about 2 GB; `limpieza` frees more)"


CHECKS: List[Callable[[], Check]] = [youtube, elevenlabs, gemini, bank, prices, disk]


def run() -> List[Check]:
    results = []
    for fn in CHECKS:
        try:
            results.append(fn())
        except Exception as exc:  # noqa: BLE001
            results.append((WARN, fn.__name__, f"check crashed: {exc}"))
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--notify", action="store_true", help="send a notification when a check fails")
    args = ap.parse_args()
    results = run()
    for status, name, detail in results:
        print(f"{status:<5} {name:<18} {detail}")
    bad = [r for r in results if r[0] == FAIL]
    if bad and args.notify:
        from services.notify import notify
        notify("Silicon Verdict: health check", "; ".join(f"{n}: {d}" for _, n, d in bad)[:200])
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
