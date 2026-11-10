#!/usr/bin/env python3
"""The `genera` command: 4 Motion videos picked from the channel's own numbers, rendered, and scheduled for TOMORROW at the best hours.

  python scripts/genera_batch.py --plan            # only show the plan (formats, hours, why) and stop
  python scripts/genera_batch.py                   # plan + render 4 + schedule them on YouTube + prepare the TikTok copies
  python scripts/genera_batch.py --date 2026-11-12 # another day (UTC date)

What it does
 1. Formats: scores every format with the YouTube Analytics numbers (average % viewed 60 %, engaged views 40 %, views-weighted, joined with
    shorts_history); formats with no data yet count as "unknown" and keep their FORMAT_WEIGHTS prior. The batch is 4 DIFFERENT formats:
    the 2 best proven ones, 1 exploration (the format with the fewest published videos) and 1 weighted draw. No data at all = weighted draws.
 2. Hours (UTC): data/batch_log.json remembers the slot of every scheduled video; once a slot has 2+ videos with views, slots are ranked by average views.
    Until then the default slots below are used (English-speaking tech/gaming audience: US morning/lunch/evening and EU evening).
 3. Renders each video with the normal Motion pipeline (export only), uploads it to YouTube as private + publishAt (scripts/upload_existing.py) and writes
    data/batch_latest.json: title, joined hashtags, TikTok caption, a <10 MB copy for the TikTok upload and the slot in UTC and in Madrid time.
 TikTok has no API here: the assistant finishes it in TikTok Studio (see .claude/commands/genera.md): upload the copy, caption + each hashtag picked from the dropdown,
 "Programación" at the slot (TikTok Studio shows GMT+0 Lisbon = UTC).
"""
import argparse
import json
import random
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

DEFAULT_SLOTS_UTC = ["13:00", "16:00", "19:00", "22:00"]  # 8-9 am / noon / 3 pm / 6 pm New York; 2 pm / 5 pm / 8 pm / 11 pm Madrid
LOG = BASE_DIR / "data" / "batch_log.json"
LATEST = BASE_DIR / "data" / "batch_latest.json"
SMALL_DIR = BASE_DIR / "output" / "tiktok_small"
FFMPEG_DIR = BASE_DIR / "remotion_studio" / "node_modules" / "@remotion" / "compositor-darwin-arm64"
FORMAT_ALIASES = {"hardware deep dive": "hardware", "everyday curiosities": "classic"}


def format_stats() -> Dict[str, Dict[str, float]]:
    """format -> {videos, views, score} from YouTube Analytics; {} when analytics are unavailable."""
    try:
        from scripts.report_retention import build, groups
        rep = build(90, 10 ** 9)  # no retention curves needed here
    except Exception as exc:  # token missing, offline...
        print(f"  (analytics unavailable: {exc}; using the format weights)")
        return {}
    out: Dict[str, Dict[str, float]] = {}
    for g in groups([r for r in rep["videos"]], "format"):
        name = FORMAT_ALIASES.get(g["name"], g["name"])
        score = 0.6 * min(g["avg"], 100.0) + 0.4 * g["engaged"]  # replayed loops pass 100 %: capped so one loop does not win
        prev = out.setdefault(name, {"videos": 0, "views": 0, "score": 0.0})
        tot = prev["views"] + g["views"]
        prev["score"] = (prev["score"] * prev["views"] + score * g["views"]) / tot if tot else score
        prev["videos"] += g["videos"]
        prev["views"] = tot
    return out


def pick_formats(stats: Dict[str, Dict[str, float]], rng: random.Random, n: int = 4, avoid: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    from services.motion_generator import FORMAT_WEIGHTS, FORMATS
    pool = [f for f in FORMATS if f not in ("easter",) and f in FORMAT_WEIGHTS and f not in (avoid or [])]
    chosen: List[Dict[str, Any]] = []

    def add(fmt: str, why: str) -> None:
        if fmt not in [c["format"] for c in chosen]:
            chosen.append({"format": fmt, "why": why})

    proven = sorted([f for f in pool if stats.get(f, {}).get("videos", 0) >= 1 and stats[f]["views"] >= 100], key=lambda f: -stats[f]["score"])
    for f in proven[:2]:
        add(f, f"proven: {stats[f]['score']:.0f} points over {stats[f]['videos']} video(s), {stats[f]['views']:.0f} views")
    explore = sorted(pool, key=lambda f: (stats.get(f, {}).get("videos", 0), -FORMAT_WEIGHTS.get(f, 1)))
    for f in explore:
        if len(chosen) >= 3:
            break
        add(f, f"exploration: only {stats.get(f, {}).get('videos', 0):.0f} published")
    rest = [f for f in pool if f not in [c["format"] for c in chosen]]
    while len(chosen) < n and rest:
        f = rng.choices(rest, weights=[FORMAT_WEIGHTS.get(x, 1) for x in rest])[0]
        add(f, "weighted draw")
        rest.remove(f)
    return chosen[:n]


def ranked_slots() -> List[str]:
    """Default slots, re-ordered by the average views of past videos in each slot once there are 2+ samples per slot."""
    if not LOG.is_file():
        return DEFAULT_SLOTS_UTC
    try:
        from services import yt_analytics as ya
        views = {v["video_id"]: v["views"] for v in ya.videos()}
    except Exception:
        return DEFAULT_SLOTS_UTC
    per: Dict[str, List[int]] = {}
    for e in json.loads(LOG.read_text()):
        if e.get("video_id") in views:
            per.setdefault(e["slot"], []).append(views[e["video_id"]])
    known = {s: sum(v) / len(v) for s, v in per.items() if len(v) >= 2}
    if len(known) < 2:
        return DEFAULT_SLOTS_UTC
    return sorted(set(DEFAULT_SLOTS_UTC) | set(known), key=lambda s: -known.get(s, 0))[:4]


def small_copy(src: str, dst: Path) -> Path:
    """<10 MB copy for the TikTok upload tool (it caps one call at 10 MB)."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["./ffmpeg", "-i", src], cwd=FFMPEG_DIR, capture_output=True, text=True)
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", p.stderr)
    secs = int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 75.0
    kbps = int(8.0 * 8192 / secs) - 96  # 8 MB target
    subprocess.run(["./ffmpeg", "-loglevel", "error", "-y", "-i", src, "-c:v", "libx264", "-b:v", f"{kbps}k", "-maxrate", f"{kbps + 100}k", "-bufsize", f"{2 * kbps}k", "-c:a", "aac", "-b:a", "96k", str(dst)], cwd=FFMPEG_DIR, check=True)
    return dst


def tiktok_caption(title: str) -> Dict[str, Any]:
    tags = re.findall(r"#([A-Za-z0-9]+)", re.sub(r"#\d+", "", title))
    text = re.sub(r"#(\d+)", r"\1", title)  # "#1" would turn into a hashtag in the TikTok box: write "1"
    text = re.sub(r"\s*#\w+", "", text).strip()
    return {"caption": text, "hashtags": ["#" + t for t in tags]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--plan", action="store_true", help="show the plan and stop")
    ap.add_argument("--date", help="UTC date to publish on (default: tomorrow)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--avoid", default="", help="comma-separated formats to leave out (e.g. the ones of the previous day)")
    ap.add_argument("--out", default=None, help="where to write the batch manifest (default data/batch_latest.json)")
    args = ap.parse_args()

    day = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else (datetime.now(timezone.utc) + timedelta(days=1)).date()
    print("Reading the channel's numbers...")
    stats = format_stats()
    picks = pick_formats(stats, random.Random(args.seed), avoid=[x for x in args.avoid.split(",") if x])
    slots = ranked_slots()
    plan = []
    for pick, slot in zip(picks, slots):  # the best formats take the best-ranked slots
        when = datetime.strptime(f"{day} {slot}", "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        plan.append({**pick, "slot": slot, "publish_at": when.strftime("%Y-%m-%dT%H:%M:00Z"), "madrid": (when + timedelta(hours=1)).strftime("%H:%M")})
    plan.sort(key=lambda p: p["slot"])
    print(f"\nPlan for {day} (UTC; Madrid = UTC+1):")
    for p in plan:
        print(f"  {p['slot']} UTC / {p['madrid']} Madrid  {p['format']:<10} {p['why']}")
    if args.plan:
        return 0

    from services.motion_pipeline import run_motion_pipeline
    done: List[Dict[str, Any]] = []
    for p in plan:
        print(f"\n== {p['format']} ==")
        res = run_motion_pipeline(export_only=True, fmt=p["format"])
        video = res["youtube_video"]
        up = subprocess.run([sys.executable, str(BASE_DIR / "scripts" / "upload_existing.py"), video, "--publish-at", p["publish_at"]], cwd=BASE_DIR, capture_output=True, text=True, env={**__import__("os").environ, "PYTHONPATH": str(BASE_DIR)})
        m = re.search(r"youtu\.be/([\w-]+)", up.stdout)
        if not m:
            print("  YouTube upload failed:", (up.stdout + up.stderr)[-300:])
        small = small_copy(res["tiktok_video"], SMALL_DIR / f"{Path(video).parent.name[:40].replace(' ', '_')}.mp4")
        entry = {**p, "title": res["title"], **tiktok_caption(res["title"]), "video": video, "tiktok_copy": str(small), "video_id": m[1] if m else None}
        done.append(entry)
        print(f"  {res['title']}\n  YouTube: {m[0] if m else 'FAILED'}  | TikTok copy: {small}")
    out = Path(args.out) if args.out else LATEST
    out.write_text(json.dumps(done, ensure_ascii=False, indent=1))
    log = json.loads(LOG.read_text()) if LOG.is_file() else []
    log += [{"video_id": e["video_id"], "slot": e["slot"], "format": e["format"], "date": str(day)} for e in done if e["video_id"]]
    LOG.write_text(json.dumps(log, indent=1))
    print(f"\nYouTube is scheduled. TikTok: finish in TikTok Studio from {out} (caption, hashtags picked from the dropdown, Programación at each slot).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
