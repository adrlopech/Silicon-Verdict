"""Real game media (Steam screenshots + trailer clips) for the Motion Graphics game videos.

Rules enforced here:
- every media item is used in ONE video only: once the video is rendered its files are deleted and its key goes to the used-ledger
  (so a later fetch never downloads it again);
- a game covered in the last 14 days is blacklisted (services/game_registry.py);
- the script is written against the captions of the chosen game's footage, so each footage scene shows what the narration mentions.
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


MIN_LUMA = 28  # mean brightness (0-255) below which a frame is a fade-to-black / empty shot


def _luma(entry: dict) -> Optional[float]:
    """Mean brightness of the item's middle frame (cached in the manifest); None if it cannot be measured."""
    if entry.get("luma") is not None:
        return float(entry["luma"])
    import io
    from PIL import Image, ImageStat
    raw = _thumb_bytes({**entry, "kind": kind_of(entry)})
    if not raw:
        return None
    value = float(ImageStat.Stat(Image.open(io.BytesIO(raw)).convert("L")).mean[0])
    data = load_manifest()
    for sec in ("images", "videos"):
        for e in data[sec]:
            if entry_key(e) == entry_key(entry):
                e["luma"] = round(value, 1)
    save_manifest(data)
    return value


def usable_media(game: str, captioned_only: bool = True) -> List[dict]:
    """Unused items of a game; black / near-black shots (trailer fades) are never offered."""
    out = []
    items = load_images()
    exact = any(i["game"] == game for i in items)  # an exact manifest name must never match a sibling ("Half-Life: Alyx" vs "Half-Life 2")
    for i in items:
        if not (i["game"] == game if exact else _game_matches(game, i["game"])) or not (i.get("caption") or not captioned_only):
            continue
        luma = _luma(i)
        if luma is not None and luma < MIN_LUMA:
            continue
        out.append(i)
    return out


def available_games(include_blacklisted: bool = False) -> List[str]:
    """Games with enough unused, captioned media that were not covered in the last 14 days."""
    from services.game_registry import blacklisted_games
    counts = Counter(i["game"] for i in load_images() if i.get("caption"))
    games = [g for g, n in counts.items() if n >= MIN_MEDIA_PER_GAME]
    if not include_blacklisted:
        banned = blacklisted_games()
        games = [g for g in games if not any(_game_matches(b, g) for b in banned)]
    return sorted(games)


# ------------------------------- staging & credits -------------------------------
def stage_media(entry: dict, public_dir: Path) -> str:
    """Copies the item into <public_dir>/games and returns the staticFile-relative path ("games/<name>")."""
    dest_dir = Path(public_dir) / "games"
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(entry["file"]).name
    shutil.copyfile(GAMES_DIR / entry["file"], dest)
    return f"games/{dest.name}"


def build_credits(entries: List[dict]) -> List[str]:
    seen: Dict[str, str] = {}
    for e in entries:
        pubs = ", ".join(e.get("publishers") or e.get("developers") or [])
        seen[e["game"]] = f"{e['game']} © {pubs}" if pubs else e["game"]
    return list(seen.values())


# ------------------------------- consumption -------------------------------
def commit_media(keys: List[str], game: str, title: str = "") -> int:
    """Called once the video is rendered: deletes every media file it used (assets + Remotion copies), forgets them in the manifest,
    records their keys so they are never fetched again, and blacklists the game for 14 days. Returns how many items were consumed."""
    from services.game_registry import mark_media_used, record_game
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
    if keys:
        mark_media_used(keys, game or "")
    if game:
        record_game(game, title)
    logger.info("Game media consumed: %d item(s) deleted for '%s'.", consumed, game)
    return consumed


def pick_game() -> Optional[str]:
    """A random game that is not blacklisted and still has enough unused, captioned footage."""
    import random
    games = available_games()
    return random.choice(games) if games else None


def footage_catalog(game: str, limit: int = 40) -> Dict[str, dict]:
    """{media_id: entry} of the unused, captioned footage of a game. Ids are short (m01, m02...) so a model cannot garble them;
    entry["key"] is the stable key used for the used-ledger."""
    return {f"m{i:02d}": e for i, e in enumerate(usable_media(game)[:limit], start=1)}


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
