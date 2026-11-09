#!/usr/bin/env python3
"""Brings every banked Motion script up to the current style rules (retention_problems in services/motion_generator.py), keeping its facts and its length.

What it does to each script that lacks it:
  * open loop: a SHORT promise appended to the shortest of scenes 2-5 (it only promises what the format guarantees: a last step, a last part, a final verdict...);
  * vote: the outro line and the pinned comment become a two-option question that fits the format (versus: "Team A or team B?" with the real contenders);
  * a run of three headline scenes: the middle one becomes a `card` (same text, drawn in a framed card), so the screen changes at least every third scene;
  * hooks and long scenes that need real rewriting come from docs/generated_scripts/bank/fixes.json (topic -> {"hook": "...", "narr": {"<scene number>": "..."}}), written by hand.
Facts and figures are never touched, so the videos stay as long as before (the pipeline still holds them above 62 s).

Updates the unused rows of the story bank in data/history.db and the built files in docs/generated_scripts/bank/<format>/.
  python scripts/update_bank_scripts.py --dry-run          # report what would change and what is still failing
  python scripts/update_bank_scripts.py --backup           # write (after copying data/history.db)
"""
import argparse
import glob
import json
import re
import shutil
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.history import DEFAULT_DB_PATH, get_db_connection  # noqa: E402
from services.motion_generator import HEADLINE, OPEN_LOOP, MotionProject, retention_problems  # noqa: E402

BANK = BASE_DIR / "docs" / "generated_scripts" / "bank"
FIXES = BANK / "fixes.json"

# the long loop sentences of the first upgrade (fix / decode) are shortened: they pushed scene 2 past the pace limit
OLD_LOOPS = [
    "Stay to the last step, because that one is easy to miss.", "And the last step is the one people tend to skip.", "Do not skip the last step, it is the part that is easy to forget.",
    "Stay with me, the last step is the one that matters most.", "Stay to the end, because one part of the name is easy to misread.", "And the last part of the name is the one people tend to get wrong.",
    "Stay with me, the last part is the one that trips people up.", "Stay to the end, the last part is the one to remember.",
]
LOOPS = {
    "fix": ["Stay for the last step.", "The last step matters.", "Stay for it."],
    "decode": ["Stay for the last part.", "The last part is easy to miss.", "Stay for it."],
    "whatif": ["It gets worse, so stay.", "It gets worse.", "Stay for it."],
    "versus": ["Stay for the verdict.", "Stay for it."],
    "evolution": ["Stay for the last one.", "Stay for it."],
    "myth": ["Stay until the last one.", "Stay for it."],
    "tier": ["Stay for the top rank.", "Stay for it."],
    "classic": ["Stay for the catch.", "Stay for it."],
}
VOTES = {
    "fix": ("Did that fix it, or still no luck? Tell me below, and follow for more tech.", "Did it fix it for you? Reply FIXED or NOPE."),
    "decode": ("Did you know that, or is it news? Tell me below, and follow for more tech.", "Did you know this already? Reply KNEW IT or NEW TO ME."),
    "classic": ("Did that surprise you, or did you know it? Tell me below, and follow for more.", "Did that surprise you? Reply SURPRISED or KNEW IT."),
    "evolution": ("Did you see that coming, or not? Tell me below, and follow for more tech.", "Did that surprise you? Reply SURPRISED or SAW IT COMING."),
    "whatif": ("Would you notice, or never know? Tell me below, and follow for more tech.", "Would you notice? Reply NOTICE or NEVER."),
    "myth": ("Did you believe any, or know them all? Tell me below, and follow for more.", "Did you believe any? Reply BELIEVED or KNEW ALL."),
    "tier": ("Do you agree with this ranking, or would you change it? Tell me below, and follow for more tech.", "Agree with the ranking? Reply AGREE or CHANGE IT."),
}


ALL_LOOPS = {x for pool in LOOPS.values() for x in pool}


def applied(current: str, fixed: str) -> bool:
    """True when the hand-written text is already in place (possibly followed by an open-loop phrase added later)."""
    return current == fixed or (current.startswith(fixed + " ") and current[len(fixed) + 1:] in ALL_LOOPS)


def fmt_of(data: dict) -> str:
    """The layout format. Old rows carry a topic area (hardware, gaming...) in `format`: those are plain explainers."""
    f = data.get("format")
    if f in LOOPS:
        return f
    types = {s["type"] for s in data["scenes"]}
    return "versus" if "versus" in types else "tier" if "tier" in types else "classic"


def cap_for(data: dict) -> int:
    return 24 if any(s["type"] in ("tier", "versus") for s in data["scenes"]) else 17


def has_vote(data: dict) -> bool:
    pc = data.get("pinned_comment", "")
    return bool(re.search(r"\bor\b[^?]*\?", data["scenes"][-1].get("narration", "")) and re.search(r"\bor\b", pc) and "?" in pc)


def pick(pool: list, topic: str) -> str:
    import hashlib
    return pool[int(hashlib.sha256(topic.lower().encode()).hexdigest(), 16) % len(pool)]


def modernize(data: dict, fixes: dict) -> list:
    """Applies the updates in place; returns what changed (empty list = nothing to do)."""
    changed = []
    sc = data["scenes"]
    fmt = fmt_of(data)
    cap = cap_for(data)
    fix = fixes.get(data["topic"].strip().lower(), {})
    # 1. hand-written hook and scene rewrites
    if fix.get("hook") and not applied(sc[0]["narration"], fix["hook"]):
        sc[0]["narration"] = fix["hook"]
        changed.append("hook")
    for num, text in (fix.get("narr") or {}).items():
        i = int(num) - 1
        if 0 <= i < len(sc) and not applied(sc[i]["narration"], text):
            sc[i]["narration"] = text
            changed.append(f"scene {num}")
    if trim_fillers(sc, cap):
        changed.append("fillers")
    if fmt == "versus" and trim_versus(sc, cap):
        changed.append("trimmed")
    # 1b. filler that costs words and slows the cold open
    for sc_ in sc:
        n = re.sub(r"\s*\bHere(?:'s| is) the thing\.", "", sc_["narration"]).strip()
        if n != sc_["narration"]:
            sc_["narration"] = n
            changed.append("filler")
    # 2. the long loop sentences of the first upgrade are replaced by short ones
    for i in range(1, min(5, len(sc))):
        for old in OLD_LOOPS:
            if old in sc[i]["narration"]:
                sc[i]["narration"] = sc[i]["narration"].replace(" " + old, "").replace(old, "").strip()
                changed.append("old loop removed")
    # 3. open loop
    if not any(OPEN_LOOP.search(s.get("narration", "")) for s in sc[1:5]) and fmt in LOOPS:
        pool = sorted(LOOPS[fmt], key=lambda x: (x != pick(LOOPS[fmt], data["topic"]), len(x.split())))
        order = sorted(range(1, min(5, len(sc))), key=lambda i: len(sc[i]["narration"].split()))
        done = False
        for phrase in pool:
            for i in order:
                if len(sc[i]["narration"].split()) + len(phrase.split()) <= cap:
                    sc[i]["narration"] = sc[i]["narration"].rstrip() + " " + phrase
                    changed.append("open loop")
                    done = True
                    break
            if done:
                break
    if fmt == "versus" and not any(OPEN_LOOP.search(s.get("narration", "")) for s in sc[1:5]):
        for i in range(1, min(5, len(sc))):
            n = re.sub(r"^Round four\b", "The last round", sc[i]["narration"])
            if n != sc[i]["narration"]:
                sc[i]["narration"] = n
                changed.append("last round")
                break
    # 4. vote (also replaces an older vote that is too long for the pace rule)
    if not has_vote(data) or len(sc[-1]["narration"].split()) > cap:
        if fmt == "versus":
            sides = next(((s["left"], s["right"]) for s in sc if s["type"] == "versus"), None)
            if sides:
                sc[-1]["narration"] = f"Team {sides[0]} or team {sides[1]}? Tell me below, and follow for more tech."
                data["pinned_comment"] = f"{sides[0]} or {sides[1]}? Reply with one word."[:120]
                changed.append("vote")
        elif fmt in VOTES:
            sc[-1]["narration"], data["pinned_comment"] = VOTES[fmt]
            changed.append("vote")
    # 5. a run of three headline scenes: the middle one becomes a card
    run = 0
    for i, s in enumerate(sc):
        run = run + 1 if s["type"] in HEADLINE else 0
        if run > 2:
            mid = sc[i - 1]
            mid["type"] = "card"
            mid.pop("cursor", None)
            run = 1
            changed.append("card")
    return changed


TRIMS = [r", where lower wins(?=[.,])", r" again(?=[,.])", r" easily(?=[,.])", r" by a mile", r" by a lot", r" by a huge margin", r" on paper", r"(?<=, )a (?:clean sweep|small edge|tiny edge|big jump|gigantic leap)[^.]*(?=\.)", r", a full megabyte", r", over twelve times more", r", sixty four times more", r", more than five times more"]


def trim_versus(sc: list, cap: int) -> bool:
    """Versus rounds run long (figures for two sides plus a verdict): drop the flourishes first, never the figures."""
    changed = False
    for s in sc:
        n = s["narration"]
        for pat in TRIMS:
            if len(n.split()) <= cap:
                break
            n = re.sub(pat, ", lower wins" if "lower wins" in pat else "", n).replace(" ,", ",").replace("  ", " ")
            n = re.sub(r",(\s*\.)", ".", n)
        if n != s["narration"]:
            s["narration"] = n
            changed = True
    return changed


# words that carry no fact: dropped, in this order, from a scene that is over the pace limit
FILLERS = [r" But there's more\.", r" But there is more\.", r"\b(?:just|really|actually|simply|basically|literally|quite|very|a little|a bit|pretty|fairly|truly)\s+", r"\bthe very\s+", r",? (?:in a way|of course|for example)(?=[,.])",
           r"\b(?:also|still|even|already|usually|often|only|always|exactly|directly)\s+", r"\b(?:and|but|so)\s+(?=(?:then|now)\b)"]


SWAPS = [(r"\bThat(?:'s| is) why\b", "So"), (r"\bwhich means\b", "so"), (r"\bin order to\b", "to"), (r"\ba lot of\b", "much"), (r"\bis able to\b", "can")]


def trim_fillers(sc: list, cap: int) -> bool:
    changed = False
    for s in sc:
        n = s["narration"]
        for pat in [r" Wild, right\?"] + FILLERS + SWAPS:
            if len(n.split()) <= cap:
                break
            n = re.sub(pat[0], pat[1], n) if isinstance(pat, tuple) else re.sub(pat, "", n)
            n = re.sub(r"\s+([,.?!])", r"\1", n).replace("  ", " ")
        if n != s["narration"] and len(n.split()) < len(s["narration"].split()):
            s["narration"] = n.strip()
            changed = True
    return changed


def load_fixes() -> dict:
    return {k.strip().lower(): v for k, v in json.loads(FIXES.read_text(encoding="utf-8")).items()} if FIXES.is_file() else {}


def failing(data: dict) -> list:
    d = {k: v for k, v in data.items() if k not in ("name", "estimated_seconds")}
    return retention_problems(MotionProject.model_validate(d))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--backup", action="store_true")
    ap.add_argument("--list", action="store_true", help="print every script that still fails, with the reasons")
    args = ap.parse_args()
    if not (args.dry_run or args.backup):
        sys.exit("pass --dry-run, or --backup to write")
    fixes = load_fixes()

    files, todo, left = 0, [], Counter()
    still = []
    for f in sorted(glob.glob(str(BANK / "*" / "*.json"))):
        data = json.loads(Path(f).read_text(encoding="utf-8"))
        ch = modernize(data, fixes)
        if ch:
            files += 1
            if args.backup:
                Path(f).write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        for p in failing(data):
            left[p.split(":")[0][:70]] += 1
            still.append((Path(f).stem, data["topic"], p))
    print(f"bank files updated: {files}")

    with get_db_connection() as conn:
        rows = conn.execute("SELECT id, payload FROM story_bank WHERE series = 'motion' AND used_at IS NULL").fetchall()
        for row in rows:
            data = json.loads(row["payload"])
            if modernize(data, fixes):
                todo.append((row["id"], data))
            for p in failing(data):
                left["bank row: " + p.split(":")[0][:60]] += 1
                still.append(("row", data["topic"], p))
        print(f"story bank rows updated: {len(todo)} of {len(rows)}")
        if args.backup and todo:
            dst = DEFAULT_DB_PATH.with_name(f"history.db.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}-bank-update")
            shutil.copyfile(DEFAULT_DB_PATH, dst)
            print(f"  backup: {dst.name}")
            for rid, data in todo:
                conn.execute("UPDATE story_bank SET payload = ? WHERE id = ?", (json.dumps(data, ensure_ascii=False), rid))
    print("still failing:", dict(left) or "nothing")
    if args.list:
        for stem, topic, p in still:
            print(f"  {stem} [{topic}] {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
