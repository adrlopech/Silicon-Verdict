#!/usr/bin/env python3
"""Validates hand-written story seeds (data/story_seed/*.py) and loads them into the story bank.

Each seed file defines STORIES = [story(...), ...] using services/story_seed_helpers.py.
Existing topics (in the bank or recently produced) are skipped.

Usage:
  python scripts/import_story_seed.py                 # import every file in data/story_seed/
  python scripts/import_story_seed.py --check         # validate only, change nothing
  python scripts/import_story_seed.py data/story_seed/simple_01.py
"""
import argparse
import importlib.util
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.schemas import MotionStoryProject, StoryProject  # noqa: E402
from services.history import get_recently_used_topics_safe  # noqa: E402
from services.story_bank import add_story, count_ready, topics_in_bank  # noqa: E402
from services.story_generator import validate_story  # noqa: E402


def load_file(path: Path) -> list:
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(getattr(mod, "STORIES", []))


def validate_game(st: MotionStoryProject) -> list:
    problems = []
    n = len(st.full_script.split())
    if not 125 <= n <= 190:
        problems.append(f"word count {n} outside 125-190")
    if len(st.visual_triggers) < 10:
        problems.append(f"{len(st.visual_triggers)} triggers (need 10+)")
    games = [t for t in st.visual_triggers if t.asset_id == "game_frame"]
    if len(games) < 5:
        problems.append(f"only {len(games)} game_frame triggers (need 5+)")
    from services.game_images import available_games, canonical_game
    for t in games:
        if not canonical_game(t.game_title or ""):
            problems.append(f"no media for '{t.game_title}' (have: {available_games(include_blacklisted=True)})")
            break
    return problems


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    files = [Path(f) for f in args.files] or sorted((BASE_DIR / "data" / "story_seed").glob("*.py"))
    known = {t.lower() for t in topics_in_bank("simple") + topics_in_bank("game") + get_recently_used_topics_safe()}
    ok = bad = dup = 0
    for f in files:
        for raw in load_file(f):
            series = raw.pop("series", "simple")
            cls = MotionStoryProject if series == "game" else StoryProject
            try:
                st = cls.model_validate(raw)
            except Exception as exc:
                bad += 1
                print(f"[INVALID] {f.name}: {raw.get('topic')}: {str(exc)[:150]}")
                continue
            problems = validate_game(st) if series == "game" else validate_story(st)
            if problems:
                bad += 1
                print(f"[REJECTED] {f.name}: {st.topic}: {problems}")
                continue
            if st.topic.lower() in known:
                dup += 1
                continue
            if not args.check:
                add_story(series, st, model="seed:hand-written")
            known.add(st.topic.lower())
            ok += 1
    print(f"{'Checked' if args.check else 'Imported'}: {ok} ok, {bad} rejected, {dup} duplicates. Ready in bank: simple={count_ready('simple')}, game={count_ready('game')}")


if __name__ == "__main__":
    main()
