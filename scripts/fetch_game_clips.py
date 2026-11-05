#!/usr/bin/env python3
"""Cuts short clips out of the official Steam trailers (store.steampowered.com appdetails -> movies) into assets/games/<slug>/clips/.

Each clip is a 2-5 s shot between scene cuts, 1280 wide, no audio. Clips already used in a video (game_media_used ledger) are never recreated.
New clips have no caption: run scripts/caption_game_media.py afterwards.

  python scripts/fetch_game_clips.py                 # every game, up to 8 clips per trailer, 2 trailers
  python scripts/fetch_game_clips.py --appid 489830 --clips-per-trailer 10
"""
import argparse
import logging
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
from scripts.fetch_game_images import GAMES  # noqa: E402
from services.game_images import GAMES_DIR, load_manifest, save_manifest  # noqa: E402
from services.game_registry import used_media_keys  # noqa: E402
from services.voice import get_ffmpeg_bin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("fetch_game_clips")
FF = get_ffmpeg_bin()


def download_trailer(url: str, dest: Path, max_seconds: int = 180) -> bool:
    cmd = [FF, "-y", "-v", "error", "-i", url, "-t", str(max_seconds), "-vf", "scale=1280:-2", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", str(dest)]
    return subprocess.run(cmd, capture_output=True, timeout=900).returncode == 0 and dest.is_file()


def scene_cuts(video: Path) -> list:
    proc = subprocess.run([FF, "-i", str(video), "-vf", "select='gt(scene,0.30)',showinfo", "-an", "-f", "null", "-"], capture_output=True, text=True, timeout=600)
    return sorted(float(m) for m in re.findall(r"pts_time:([\d.]+)", proc.stderr))


def duration(video: Path) -> float:
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", subprocess.run([FF, "-i", str(video)], capture_output=True, text=True).stderr)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def plan_clips(cuts: list, total: float, how_many: int) -> list:
    """(start, length) shots of 2-5 s between cuts, skipping the intro logos and the end card, spread over the trailer."""
    bounds = [0.0] + cuts + [total]
    shots = []
    for a, b in zip(bounds, bounds[1:]):
        start, end = max(a, 4.0) + 0.15, min(b, total - 4.0) - 0.1
        if end - start >= 2.0:
            shots.append((round(start, 2), round(min(end - start, 5.0), 2)))
    if len(shots) <= how_many:
        return shots
    step = len(shots) / how_many
    return [shots[int(i * step)] for i in range(how_many)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--appid", type=int)
    ap.add_argument("--clips-per-trailer", type=int, default=8)
    ap.add_argument("--trailers", type=int, default=2)
    args = ap.parse_args()

    manifest, used = load_manifest(), used_media_keys()
    have = {v.get("key") for v in manifest["videos"]}
    session = requests.Session()
    session.headers["User-Agent"] = "SiliconVerdict-asset-fetcher/1.0"
    total_new = 0
    for appid, (slug, tags) in GAMES.items():
        if args.appid and appid != args.appid:
            continue
        try:
            r = session.get("https://store.steampowered.com/api/appdetails", params={"appids": appid, "l": "english"}, timeout=20).json().get(str(appid), {})
            if not r.get("success"):
                continue
            data = r["data"]
            for movie in data.get("movies", [])[: args.trailers]:
                url = movie.get("hls_h264") or movie.get("dash_h264")
                if not url:
                    continue
                with tempfile.TemporaryDirectory() as tmp:
                    trailer = Path(tmp) / "trailer.mp4"
                    if not download_trailer(url, trailer):
                        log.warning("%s: trailer %s could not be read", data["name"], movie["id"])
                        continue
                    total = duration(trailer)
                    for start, length in plan_clips(scene_cuts(trailer), total, args.clips_per_trailer):
                        key = f"{movie['id']}_{int(start * 10)}"
                        if key in used or key in have:
                            continue
                        rel = f"{slug}/clips/{slug}_{key}.mp4"
                        out = GAMES_DIR / rel
                        out.parent.mkdir(parents=True, exist_ok=True)
                        ok = subprocess.run([FF, "-y", "-v", "error", "-ss", str(start), "-t", str(length), "-i", str(trailer), "-an", "-c:v", "libx264",
                                             "-preset", "veryfast", "-crf", "25", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(out)], capture_output=True).returncode == 0
                        if not ok or not out.is_file():
                            continue
                        manifest["videos"].append({
                            "file": rel, "key": key, "game": data["name"], "appid": appid, "tags": tags, "kind": "video", "seconds": length,
                            "developers": data.get("developers", []), "publishers": data.get("publishers", []), "source": "steam_trailer",
                            "source_url": f"https://store.steampowered.com/app/{appid}/", "trailer": movie.get("name", ""),
                            "downloaded_at": datetime.now(timezone.utc).isoformat(),
                        })
                        have.add(key)
                        total_new += 1
            save_manifest(manifest)
            log.info("%s: clips so far %d", data["name"], total_new)
        except Exception as exc:
            log.error("appid %s failed: %s", appid, exc)
        time.sleep(0.5)
    log.info("Done: %d new clips (%d videos in manifest).", total_new, len(manifest["videos"]))


if __name__ == "__main__":
    main()
