#!/usr/bin/env python3
"""Brings the banked (unused) motion scripts up to the style rules of Nov 2026:

  * the accent phrase no longer repeats the headline's first or last words (deterministic);
  * a generic closing vote ("Did that surprise you or did you know it? Tell me below...") is rewritten into a question that names the video's own two options, with its pinned comment;
  * a "Let us ..." cold open is rewritten as a concrete claim (same fact, at most 14 words).

The two rewrites are one short model call each (Cloudflare first, Gemini as fallback) and are only kept when they pass the same checks the generator applies; otherwise the script keeps its old text.
  python scripts/rewrite_bank_closers.py [--dry-run] [--limit N]
The database is copied to data/history.db.bak-<stamp>-closers before the first write.
"""
import argparse
import json
import shutil
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.motion_generator import BAD_OPENER, GENERIC_CLOSER, fix_duplicate_accents, vote_options  # noqa: E402

DB = BASE_DIR / "data" / "history.db"
MODELS = ["@cf/meta/llama-3.3-70b-instruct-fp8-fast"]


class _Closer(BaseModel):
    question: str = Field(..., description='One question naming two options of THIS video, e.g. "Team 7800X3D or team 9800X3D?" or "Would you buy it, or skip it?" (at most 14 words)')
    option_a: str = Field(..., description="The first option, 1-3 words, exactly as written in the question")
    option_b: str = Field(..., description="The second option, 1-3 words, exactly as written in the question")


class _Hook(BaseModel):
    hook: str = Field(..., description="The cold open: the claim itself, at most 14 words, no greeting, never starting with Let us / Let's / So / Today")


def _call(schema, prompt: str, system: str):
    from services.gemini_client import generate_structured
    obj, _tokens, _model = generate_structured(prompt=prompt, system_instruction=system, schema=schema, temperature=0.7, max_output_tokens=300, provider_first="cloudflare", provider_models=MODELS)
    return obj


def _digest(p: Dict[str, Any]) -> str:
    lines = [f"- {s.get('text', '')} / {s.get('accentText') or ''}: {s.get('narration', '')}" for s in p["scenes"][:-1]]
    return f"Title: {p['title']}\nTopic: {p.get('topic', '')}\nScenes (headline / accent: narration):\n" + "\n".join(lines)


def new_closer(p: Dict[str, Any]) -> Optional[Dict[str, str]]:
    system = "You write the last line of a short tech video. Name the video's own two options in the question, in plain spoken American English. Never ask 'did that surprise you', never 'tell me below'."
    for attempt in range(3):
        try:
            c = _call(_Closer, _digest(p) + "\n\nWrite the closing question and its two options.", system)
        except Exception:
            continue
        q, a, b = c.question.strip(), c.option_a.strip(" ,.?!"), c.option_b.strip(" ,.?!")
        closing, pinned = f"Follow for more tech. {q}", f"{a} or {b}? Reply with one word."
        if (a and b and a.lower() in q.lower() and b.lower() in q.lower() and len(a.split()) <= 3 and len(b.split()) <= 3 and vote_options(pinned) and q.endswith("?")
                and not GENERIC_CLOSER.search(closing + " " + pinned) and len(q.split()) <= 16):
            return {"closing": closing, "pinned": pinned}
    return None


def new_hook(p: Dict[str, Any]) -> Optional[str]:
    system = "You rewrite the first spoken line of a short tech video as a cold open: a number, a concrete claim or a tension. Keep the same fact. Plain spoken American English."
    old = p["scenes"][0].get("narration", "")
    for attempt in range(3):
        try:
            h = _call(_Hook, _digest(p) + f"\n\nCurrent first line: {old}\nRewrite it.", system).hook.strip()
        except Exception:
            continue
        if h and not BAD_OPENER.search(h) and len(h.split()) <= 14:
            return h
    return None


def process(row: sqlite3.Row, dry: bool) -> Dict[str, Any]:
    p = json.loads(row["payload"])
    changed = []
    objs = [SimpleNamespace(text=s.get("text", ""), accentText=s.get("accentText"), type=s["type"]) for s in p["scenes"]]
    fix_duplicate_accents(objs)
    for s, o in zip(p["scenes"], objs):
        if o.text != s.get("text", ""):
            s["text"] = o.text
            changed.append("accent")
    outro = p["scenes"][-1]
    if outro["type"] == "outro" and GENERIC_CLOSER.search(outro.get("narration", "") + " " + (p.get("pinned_comment") or "")):
        c = new_closer(p)
        if c:
            outro["narration"], p["pinned_comment"] = c["closing"], c["pinned"]
            outro.pop("items", None)
            changed.append("closer")
    if BAD_OPENER.search(p["scenes"][0].get("narration", "")):
        h = new_hook(p)
        if h:
            p["scenes"][0]["narration"] = h
            changed.append("hook")
    return {"id": row["id"], "payload": json.dumps(p, ensure_ascii=False), "changed": changed, "title": p["title"][:50]}


def sync_files(dry: bool) -> None:
    """The on-disk mirror of the bank (docs/generated_scripts/bank/*/*.json, git-ignored, read by the tests): each file takes the rewritten text of the database row with the same topic,
    or is rewritten on its own when the database has no such row (an already used script)."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    by_topic = {json.loads(r["payload"]).get("topic"): json.loads(r["payload"]) for r in conn.execute("SELECT payload FROM story_bank WHERE series = 'motion'")}
    files = sorted((BASE_DIR / "docs" / "generated_scripts" / "bank").glob("*/*.json"))
    n = 0
    for f in files:
        data = json.loads(f.read_text(encoding="utf-8"))
        if "scenes" not in data:
            continue
        src = by_topic.get(data.get("topic"))
        if src is None or src["scenes"][-1]["type"] != data["scenes"][-1]["type"] or len(src["scenes"]) != len(data["scenes"]) or GENERIC_CLOSER.search(src["scenes"][-1].get("narration", "")):
            src = json.loads(process({"id": 0, "payload": json.dumps(data)}, dry)["payload"])
        changed = False
        for key in ("pinned_comment",):
            if data.get(key) != src.get(key):
                data[key], changed = src[key], True
        for a, b in zip(data["scenes"], src["scenes"]):
            for key in ("text", "narration"):
                if a.get(key) != b.get(key):
                    a[key], changed = b[key], True
            if a["type"] == "outro" and a.get("items") != b.get("items"):
                a.pop("items", None)
        if changed and not dry:
            f.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
            n += 1
    print(f"files updated: {n} of {len(files)}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--files", action="store_true", help="only sync the on-disk mirror of the bank with the database")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    if args.files:
        sync_files(args.dry_run)
        return 0
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT id, payload FROM story_bank WHERE series = 'motion' AND used_at IS NULL ORDER BY id").fetchall()
    if args.limit:
        rows = rows[: args.limit]
    print(f"{len(rows)} unused motion scripts")
    if not args.dry_run:
        backup = DB.with_name(f"history.db.bak-{datetime.now():%Y%m%d-%H%M%S}-closers")
        shutil.copy2(DB, backup)
        print("backup:", backup.name)
    done = {"accent": 0, "closer": 0, "hook": 0, "untouched": 0}
    with ThreadPoolExecutor(max_workers=4) as pool:
        for res in pool.map(lambda r: process(r, args.dry_run), rows):
            for k in res["changed"]:
                done[k] += 1
            if not res["changed"]:
                done["untouched"] += 1
            elif not args.dry_run:
                conn.execute("UPDATE story_bank SET payload = ? WHERE id = ?", (res["payload"], res["id"]))
                conn.commit()
            print(f"  #{res['id']} {res['title']}: {', '.join(res['changed']) or '-'}", flush=True)
    print("done:", done)
    return 0


if __name__ == "__main__":
    sys.exit(main())
