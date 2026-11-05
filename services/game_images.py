"""Real game media (Steam screenshots + trailer clips) for Remotion GameFrame scenes.

Rules enforced here:
- every media item is used in ONE video only: once the video is rendered its files are deleted and its key goes to the used-ledger
  (so a later fetch never downloads it again);
- a game covered in the last 14 days is blacklisted (services/game_registry.py);
- each trigger gets media whose caption matches what the narration says at that moment (one LLM call per video, see assign_media);
  a trigger with no fitting media is downgraded to a vector card instead of showing something irrelevant.
"""
import hashlib
import json
import logging
import re
import shutil
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)

GAMES_DIR = settings.BASE_DIR / "assets" / "games"
MANIFEST = GAMES_DIR / "manifest.json"
REMOTION_GAMES_DIR = settings.BASE_DIR / "remotion_studio" / "public" / "games"
MIN_MEDIA_PER_GAME = 6   # a game with fewer unused, captioned items is considered exhausted
CAPTION_BATCH = 12


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


# ------------------------------- manifest -------------------------------
def load_manifest() -> dict:
    if not MANIFEST.is_file():
        return {"images": [], "videos": []}
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Could not read game media manifest: %s", exc)
        return {"images": [], "videos": []}
    data.setdefault("images", [])
    data.setdefault("videos", [])
    return data


def save_manifest(data: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(data, indent=1, ensure_ascii=False), encoding="utf-8")


def entry_key(entry: dict) -> str:
    """Stable identity of a media item across re-fetches (hash of its source URL, or of its trailer id + start for clips)."""
    if entry.get("key"):
        return entry["key"]
    src = entry.get("image_url") or entry.get("source_url") or entry.get("file", "")
    return hashlib.sha1(src.encode()).hexdigest()[:12]


def kind_of(entry: dict) -> str:
    return "video" if entry.get("file", "").endswith(".mp4") else "image"


def load_images() -> List[dict]:
    """Every media entry (images and clips) whose file still exists and that has not been used in a video."""
    from services.game_registry import used_media_keys
    used = used_media_keys()
    data = load_manifest()
    out = []
    for e in data["images"] + data["videos"]:
        if (GAMES_DIR / e["file"]).is_file() and entry_key(e) not in used:
            e["key"] = entry_key(e)
            e["kind"] = kind_of(e)
            out.append(e)
    return out


# ------------------------------- game availability -------------------------------
def _game_matches(requested: str, game: str) -> bool:
    r, g = _norm(requested), _norm(game)
    if not r or not g:
        return False
    if r in g or g in r:
        return True
    r_words = [w for w in r.split() if len(w) > 3 and not w.isdigit()]
    return bool(r_words) and all(w in g.split() for w in r_words[:1])


def canonical_game(name: str) -> Optional[str]:
    for g in sorted({i["game"] for i in load_images()}) or sorted({i["game"] for i in load_manifest()["images"]}):
        if _game_matches(name, g):
            return g
    return None


def usable_media(game: str, captioned_only: bool = True) -> List[dict]:
    return [i for i in load_images() if _game_matches(game, i["game"]) and (i.get("caption") or not captioned_only)]


def available_games(include_blacklisted: bool = False) -> List[str]:
    """Games with enough unused, captioned media that were not covered in the last 14 days."""
    from services.game_registry import blacklisted_games
    counts = Counter(i["game"] for i in load_images() if i.get("caption"))
    games = [g for g, n in counts.items() if n >= MIN_MEDIA_PER_GAME]
    if not include_blacklisted:
        banned = blacklisted_games()
        games = [g for g in games if not any(_game_matches(b, g) for b in banned)]
    return sorted(games)


def story_game(story) -> Optional[str]:
    """The game a story is about: the most common game_title among its game_frame triggers."""
    titles = [t.game_title for t in story.visual_triggers if getattr(t, "game_title", None)]
    if not titles:
        return None
    top = Counter(titles).most_common(1)[0][0]
    return canonical_game(top) or top


def story_is_allowed(story) -> bool:
    """False when the story is about a blacklisted or exhausted game."""
    game = story_game(story)
    return game is None or any(_game_matches(game, g) for g in available_games())


# ------------------------------- staging & credits -------------------------------
def stage_media_for_remotion(entry: dict) -> str:
    REMOTION_GAMES_DIR.mkdir(parents=True, exist_ok=True)
    src = GAMES_DIR / entry["file"]
    dest = REMOTION_GAMES_DIR / Path(entry["file"]).name
    if not dest.is_file() or dest.stat().st_size != src.stat().st_size:
        shutil.copyfile(src, dest)
    return f"games/{dest.name}"


stage_image_for_remotion = stage_media_for_remotion  # backwards-compatible name


def build_credits(entries: List[dict]) -> List[str]:
    seen: Dict[str, str] = {}
    for e in entries:
        pubs = ", ".join(e.get("publishers") or e.get("developers") or [])
        seen[e["game"]] = f"{e['game']} © {pubs}" if pubs else e["game"]
    return list(seen.values())


# ------------------------------- consumption -------------------------------
def commit_story_media(story) -> int:
    """Called once the video is rendered: deletes every media file the story used (assets + Remotion copies), forgets it in the manifest,
    records its key so it is never fetched again, and blacklists the game for 14 days. Returns how many items were consumed."""
    from services.game_registry import mark_media_used, record_game
    keys = list(getattr(story, "media_keys", None) or [])
    data = load_manifest()
    consumed = 0
    for section in ("images", "videos"):
        keep = []
        for e in data[section]:
            if entry_key(e) in keys:
                for f in (GAMES_DIR / e["file"], REMOTION_GAMES_DIR / Path(e["file"]).name):
                    f.unlink(missing_ok=True)
                consumed += 1
            else:
                keep.append(e)
        data[section] = keep
    save_manifest(data)
    game = story_game(story)
    if keys:
        mark_media_used(keys, game or "")
    if game:
        record_game(game, getattr(story, "title", ""))
    logger.info("Game media consumed: %d item(s) deleted for '%s'.", consumed, game)
    return consumed


# ------------------------------- captions (what each item shows) -------------------------------
def _thumb_bytes(entry: dict) -> Optional[bytes]:
    """JPEG bytes for captioning: the screenshot itself, or the middle frame of a clip."""
    import subprocess
    from services.voice import get_ffmpeg_bin
    path = GAMES_DIR / entry["file"]
    cmd = [get_ffmpeg_bin(), "-v", "error"]
    if entry.get("kind") == "video" or path.suffix == ".mp4":
        cmd += ["-ss", f"{max(0.2, float(entry.get('seconds', 3)) / 2):.2f}"]
    cmd += ["-i", str(path), "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "4", "-f", "image2pipe", "-vcodec", "mjpeg", "-"]
    try:
        return subprocess.run(cmd, capture_output=True, timeout=60).stdout or None
    except Exception:
        return None


def caption_pending(limit: int = 200) -> int:
    """Describes (with a vision model) every manifest item that has no caption yet. Returns how many were captioned."""
    from pydantic import BaseModel, Field
    from services.gemini_client import GeminiUnavailable, generate_structured

    class Cap(BaseModel):
        index: int
        caption: str = Field(..., description="12-25 words: what is VISIBLY on screen (place, characters, creatures, objects, UI, action). Facts only, no guesses about game mechanics.")

    class Caps(BaseModel):
        items: List[Cap]

    data = load_manifest()
    todo = [e for sec in ("images", "videos") for e in data[sec] if not e.get("caption") and (GAMES_DIR / e["file"]).is_file()][:limit]
    done = 0
    for start in range(0, len(todo), CAPTION_BATCH):
        batch = todo[start:start + CAPTION_BATCH]
        thumbs = [(e, _thumb_bytes({**e, "kind": kind_of(e)})) for e in batch]
        thumbs = [(e, b) for e, b in thumbs if b]
        if not thumbs:
            continue
        game = thumbs[0][0]["game"]
        prompt = (f"These {len(thumbs)} images are official screenshots / trailer frames of the video game '{game}' (numbered 0..{len(thumbs) - 1} in order). "
                  "For EACH image return its index and a factual caption of what is visibly shown.")
        try:
            res, _tok, model = generate_structured(prompt, "You describe game images precisely and briefly.", Caps, temperature=0.2,
                                                   validate=lambda r: [] if len(r.items) >= len(thumbs) else [f"need {len(thumbs)} captions"],
                                                   images=[b for _, b in thumbs])
        except GeminiUnavailable as exc:
            logger.warning("Captioning stopped (%s). %d item(s) captioned so far.", str(exc)[:140], done)
            break
        by_idx = {c.index: c.caption.strip() for c in res.items}
        for i, (e, _b) in enumerate(thumbs):
            if by_idx.get(i):
                e["caption"] = by_idx[i]
                done += 1
        save_manifest(data)
        logger.info("Captioned %d/%d (%s via %s).", done, len(todo), game, model)
    return done


# ------------------------------- grounded assignment -------------------------------
def _context_for(story, anchor: str, radius: int = 14) -> str:
    words = story.full_script.split()
    low = [re.sub(r"\W+", "", w).lower() for w in words]
    key = re.sub(r"\W+", "", (anchor or "").split()[0] if anchor else "").lower()
    pos = next((i for i, w in enumerate(low) if w == key), 0)
    return " ".join(words[max(0, pos - radius): pos + radius])


def assign_media(story) -> object:
    """Binds each 'game_frame' trigger to an unused screenshot/clip of the SAME game whose caption fits what the narration says there.
    One LLM call per video. Items nobody asked for are never shown; a trigger without a fitting item becomes a vector 'stat_card'.
    The chosen keys are kept in story.media_keys so commit_story_media() can consume them after the render."""
    from pydantic import BaseModel
    from services.gemini_client import GeminiUnavailable, generate_structured

    triggers = [(i, t) for i, t in enumerate(story.visual_triggers) if t.asset_id.lower() == "game_frame"]
    if not triggers:
        return story
    game = story_game(story)
    pool = usable_media(game) if game else []
    chosen: Dict[int, dict] = {}
    if pool:
        catalog = {e["key"]: e for e in pool}

        class Pick(BaseModel):
            trigger: int
            media_id: Optional[str] = None

        class Picks(BaseModel):
            items: List[Pick]

        def _check(r: Picks) -> List[str]:
            ids = [p.media_id for p in r.items if p.media_id]
            bad = [i for i in ids if i not in catalog]
            return ([f"unknown media ids {bad[:3]}"] if bad else []) + (["a media id was used twice"] if len(ids) != len(set(ids)) else [])

        lines = "\n".join(f"- id={k} [{e['kind']}] {e['caption']}" for k, e in catalog.items())
        asks = "\n".join(f"- trigger {i}: callout \"{t.annotation or t.label}\" | narration at that moment: \"{_context_for(story, t.word_anchor)}\"" for i, t in triggers)
        prompt = (f"Game: {game}. Available media (each can be used ONCE):\n{lines}\n\nTriggers to illustrate:\n{asks}\n\n"
                  "For each trigger choose the media whose caption best shows what the narration is talking about at that moment. "
                  "If nothing fits well, return media_id null (a vector graphic will be used instead; do NOT force a bad match). "
                  "Prefer 'video' items when they fit equally well. Never use an id twice.")
        try:
            res, _tok, model = generate_structured(prompt, "You are a careful video editor matching footage to narration.", Picks, temperature=0.2, validate=_check)
            for p in res.items:
                if p.media_id and p.trigger in dict(triggers):
                    chosen[p.trigger] = catalog[p.media_id]
            logger.info("Media assignment via %s: %d of %d triggers matched.", model, len(chosen), len(triggers))
        except GeminiUnavailable as exc:
            logger.warning("Media matching unavailable (%s): game_frame triggers become vector cards rather than showing unverified footage.", str(exc)[:120])

    used_entries: List[dict] = []
    for i, trig in triggers:
        entry = chosen.get(i)
        if not entry:
            trig.asset_id, trig.annotation, trig.image_src, trig.video_src = "stat_card", None, None, None
            continue
        staged = stage_media_for_remotion(entry)
        if entry["kind"] == "video":
            trig.video_src, trig.video_seconds, trig.image_src = staged, float(entry.get("seconds", 3.0)), None
        else:
            trig.image_src, trig.video_src = staged, None
        trig.game_title = entry["game"]
        used_entries.append(entry)
    story.media_keys = [e["key"] for e in used_entries]
    if used_entries:
        story.description = story.description.split("\n\nImages:")[0].rstrip() + "\n\nImages & footage: " + "; ".join(build_credits(used_entries)) + " (official Steam store media)."
    return story
