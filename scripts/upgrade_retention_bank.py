#!/usr/bin/env python3
"""Adds an open loop (a promise of a later payoff) and a two-option vote (outro line and pinned comment), see RETENTION_RULES, to the banked `fix` and `decode` scripts that lack them.

Only scripts that were NEVER published are touched: whatif / versus / evolution already produced our best TikTok results, so their bank stays as the control group of the style test.
The loop phrase is appended to scene 2's narration and promises only what the format itself guarantees (the fix has a last step, a decoded label has a last part).
The vote is a binary question that fits every script of the format ("fixed it, or still no luck?", "already knew it, or news to you?"), so it replaces the open question of the outro.
It is chosen from a small pool by a hash of the topic, so reruns give the same result and the channel does not repeat one sentence everywhere.

Updates the story bank rows that are still unused in data/history.db and the built bank files in docs/generated_scripts/bank/<format>/.
Back up data/history.db first (this script refuses to write without --backup or --no-backup).

Usage:
  python scripts/upgrade_retention_bank.py --dry-run
  python scripts/upgrade_retention_bank.py --backup
"""
import argparse
import hashlib
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.history import DEFAULT_DB_PATH, get_db_connection  # noqa: E402
from services.motion_generator import OPEN_LOOP  # noqa: E402

POOLS = {
    "fix": [
        "Stay to the last step, because that one is easy to miss.",
        "And the last step is the one people tend to skip.",
        "Do not skip the last step, it is the part that is easy to forget.",
        "Stay with me, the last step is the one that matters most.",
    ],
    "decode": [
        "Stay to the end, because one part of the name is easy to misread.",
        "And the last part of the name is the one people tend to get wrong.",
        "Stay with me, the last part is the one that trips people up.",
        "Stay to the end, the last part is the one to remember.",
    ],
}
VOTES = {
    "fix": ("Did that fix it for you, or still no luck? Tell me below, and follow for more tech.", "Did it fix it for you? Reply FIXED or NOPE."),
    "decode": ("Did you already know that, or is it news to you? Tell me below, and follow for more tech.", "Did you know this already? Reply KNEW IT or NEW TO ME."),
}
BANK_DIR = BASE_DIR / "docs" / "generated_scripts" / "bank"


def pick(fmt: str, topic: str) -> str:
    pool = POOLS[fmt]
    return pool[int(hashlib.sha256(topic.lower().encode()).hexdigest(), 16) % len(pool)]


def upgrade(data: dict) -> bool:
    """Adds the open-loop phrase to scene 2 (when scenes 2-5 have none) and the two-option vote to the outro and the pinned comment (when missing). True when the script changed."""
    fmt = data.get("format")
    scenes = data.get("scenes") or []
    if fmt not in POOLS or len(scenes) < 5:
        return False
    changed = False
    if not any(OPEN_LOOP.search(s.get("narration", "")) for s in scenes[1:5]):
        scenes[1]["narration"] = scenes[1]["narration"].rstrip() + " " + pick(fmt, data["topic"])
        changed = True
    if not re.search(r"\bor\b[^?]*\?", scenes[-1].get("narration", "")) or not (re.search(r"\bor\b", data.get("pinned_comment", "")) and "?" in data.get("pinned_comment", "")):
        scenes[-1]["narration"], data["pinned_comment"] = VOTES[fmt]
        changed = True
    return changed


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup", action="store_true", help="copy data/history.db to data/history.db.bak-<timestamp> before writing")
    ap.add_argument("--no-backup", action="store_true")
    args = ap.parse_args()
    if not (args.dry_run or args.backup or args.no_backup):
        sys.exit("pass --dry-run, or --backup (recommended) / --no-backup to write")

    changed_db = 0
    with get_db_connection() as conn:
        rows = conn.execute("SELECT id, payload FROM story_bank WHERE series = 'motion' AND used_at IS NULL").fetchall()
        todo = []
        for row in rows:
            data = json.loads(row["payload"])
            if upgrade(data):
                todo.append((row["id"], data))
        print(f"story bank: {len(todo)} unused fix/decode scripts need an open loop or a vote")
        if todo:
            print(f"  e.g. #{todo[0][0]} {todo[0][1]['topic']!r}: ... {todo[0][1]['scenes'][1]['narration']}")
        if not args.dry_run and todo:
            if args.backup:
                dst = DEFAULT_DB_PATH.with_name(f"history.db.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
                shutil.copyfile(DEFAULT_DB_PATH, dst)
                print(f"  backup: {dst.name}")
            for row_id, data in todo:
                conn.execute("UPDATE story_bank SET payload = ? WHERE id = ?", (json.dumps(data, ensure_ascii=False), row_id))
                changed_db += 1

    files = 0
    for fmt in POOLS:
        for f in sorted((BANK_DIR / fmt).glob("*.json")):
            data = json.loads(f.read_text(encoding="utf-8"))
            if upgrade(data):
                files += 1
                if not args.dry_run:
                    f.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"bank files: {files} {'would be ' if args.dry_run else ''}updated; story bank rows written: {changed_db}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
