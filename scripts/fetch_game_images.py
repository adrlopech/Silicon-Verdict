#!/usr/bin/env python3
"""Downloads official Steam store screenshots into assets/games/ and writes a manifest.

Source: Steam Store public API (store.steampowered.com/api/appdetails).
Each image is recorded in assets/games/manifest.json with game, developer/publisher,
source URL and tags, so videos can credit the source and avoid repeating images.

Usage:
  python scripts/fetch_game_images.py                # all games, 5 images each
  python scripts/fetch_game_images.py --per-game 8
  python scripts/fetch_game_images.py --appid 1091500
"""
import argparse
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
GAMES_DIR = BASE_DIR / "assets" / "games"
MANIFEST = GAMES_DIR / "manifest.json"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("fetch_game_images")

# appid -> (slug, curiosity tags used by the topic engine)
GAMES = {
    1091500: ("cyberpunk_2077", ["rendering", "raytracing", "lod"]),
    379720: ("doom_2016", ["optimization", "idtech", "rendering"]),
    220: ("half_life_2", ["physics", "source_engine"]),
    489830: ("skyrim_se", ["physics", "framerate", "bugs"]),
    620: ("portal_2", ["physics", "level_design"]),
    292030: ("the_witcher_3", ["open_world", "streaming", "lod"]),
    1245620: ("elden_ring", ["framerate", "stutter", "open_world"]),
    1174180: ("red_dead_redemption_2", ["rendering", "simulation", "streaming"]),
    730: ("counter_strike_2", ["netcode", "tickrate", "physics"]),
    546560: ("half_life_alyx", ["vr", "physics", "optimization"]),
    1190460: ("death_stranding", ["procedural", "rendering"]),
    870780: ("control", ["raytracing", "destruction", "physics"]),
    1716740: ("starfield", ["procedural", "loading"]),
    1086940: ("baldurs_gate_3", ["dice", "simulation"]),
    271590: ("gta_v", ["streaming", "optimization"]),
}


# Current games (released or announced for 2025-2026): data/games_catalog.json, built from Steam's own search + appdetails (real appids, release dates).
# Add a game there ({"<appid>": {"slug": ..., "name": ..., "year": ...}}) and run this script, then build_game_facts.py and caption_game_media.py.
_CATALOG = BASE_DIR / "data" / "games_catalog.json"
if _CATALOG.is_file():
    for _appid, _g in json.loads(_CATALOG.read_text(encoding="utf-8")).items():
        GAMES.setdefault(int(_appid), (_g["slug"], [str(_g.get("year", "")), "current"]))


def load_manifest() -> dict:
    if MANIFEST.is_file():
        try:
            return json.loads(MANIFEST.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"images": []}


def fetch_game(session: requests.Session, appid: int, slug: str, tags: list, per_game: int, manifest: dict) -> int:
    r = session.get(
        "https://store.steampowered.com/api/appdetails",
        params={"appids": appid, "l": "english"},
        timeout=20,
    )
    r.raise_for_status()
    entry = r.json().get(str(appid), {})
    if not entry.get("success"):
        log.warning("appid %s: no data", appid)
        return 0
    data = entry["data"]
    import sys
    sys.path.insert(0, str(BASE_DIR))
    from services.game_registry import used_media_keys
    from services.game_images import entry_key
    used = used_media_keys()
    shots = [sh for sh in data.get("screenshots", []) if entry_key({"image_url": re.sub(r"\?t=\d+$", "", sh["path_full"])}) not in used]  # never re-download used media
    # Spread picks across the gallery for variety
    step = max(1, len(shots) // per_game)
    picked = shots[::step][:per_game]

    out_dir = GAMES_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)
    known = {i["file"] for i in manifest["images"]}
    count = 0
    for shot in picked:
        url = shot["path_full"]
        fname = f"{slug}_{shot['id']:02d}.jpg"
        rel = f"{slug}/{fname}"
        if rel in known and (GAMES_DIR / rel).is_file():
            continue
        img = session.get(url, timeout=30)
        if img.status_code != 200 or len(img.content) < 10_000:
            log.warning("skip %s (status %s)", url, img.status_code)
            continue
        (GAMES_DIR / rel).write_bytes(img.content)
        manifest["images"].append({
            "file": rel,
            "game": data["name"],
            "appid": appid,
            "tags": tags,
            "developers": data.get("developers", []),
            "publishers": data.get("publishers", []),
            "source": "steam_store",
            "source_url": f"https://store.steampowered.com/app/{appid}/",
            "image_url": re.sub(r"\?t=\d+$", "", url),
            "bytes": len(img.content),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        })
        count += 1
        time.sleep(0.3)
    log.info("%s: %d new images", data["name"], count)
    return count


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-game", type=int, default=12)
    ap.add_argument("--appid", type=int)
    args = ap.parse_args()

    GAMES_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    session = requests.Session()
    session.headers["User-Agent"] = "SiliconVerdict-asset-fetcher/1.0"

    total = 0
    for appid, (slug, tags) in GAMES.items():
        if args.appid and appid != args.appid:
            continue
        try:
            total += fetch_game(session, appid, slug, tags, args.per_game, manifest)
        except Exception as exc:
            log.error("appid %s failed: %s", appid, exc)
        MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Done: %d new images, %d total in manifest", total, len(manifest["images"]))


if __name__ == "__main__":
    main()
