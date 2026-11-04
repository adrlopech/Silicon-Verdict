"""Selects real game screenshots from assets/games/manifest.json for Remotion GameFrame scenes."""
import json
import logging
import random
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from config.settings import settings

logger = logging.getLogger(__name__)

GAMES_DIR = settings.BASE_DIR / "assets" / "games"
MANIFEST = GAMES_DIR / "manifest.json"
REMOTION_GAMES_DIR = settings.BASE_DIR / "remotion_studio" / "public" / "games"


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def load_images() -> List[dict]:
    if not MANIFEST.is_file():
        return []
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8")).get("images", [])
    except Exception as exc:
        logger.warning("Could not read game image manifest: %s", exc)
        return []


def available_games() -> List[str]:
    """Display names of games that have downloaded screenshots."""
    return sorted({i["game"] for i in load_images() if (GAMES_DIR / i["file"]).is_file()})


def _game_matches(requested: str, game: str) -> bool:
    r, g = _norm(requested), _norm(game)
    if not r or not g:
        return False
    if r in g or g in r:
        return True
    # Match on the first meaningful word(s), e.g. "Doom 2016" -> "DOOM", "Skyrim" -> "...Skyrim..."
    r_words = [w for w in r.split() if len(w) > 3 and not w.isdigit()]
    return bool(r_words) and all(w in g.split() for w in r_words[:1])


def pick_image(game_title: str, used: Optional[set] = None, rng: Optional[random.Random] = None) -> Optional[dict]:
    """Returns a manifest entry for the game, preferring images not yet used in this video."""
    rng = rng or random.Random()
    used = used if used is not None else set()
    candidates = [
        i for i in load_images()
        if _game_matches(game_title, i["game"]) and (GAMES_DIR / i["file"]).is_file()
    ]
    if not candidates:
        return None
    fresh = [c for c in candidates if c["file"] not in used] or candidates
    choice = rng.choice(fresh)
    used.add(choice["file"])
    return choice


def stage_image_for_remotion(entry: dict) -> str:
    """Copies the screenshot into remotion_studio/public/games and returns the staticFile-relative path."""
    REMOTION_GAMES_DIR.mkdir(parents=True, exist_ok=True)
    src = GAMES_DIR / entry["file"]
    dest = REMOTION_GAMES_DIR / Path(entry["file"]).name
    if not dest.is_file() or dest.stat().st_size != src.stat().st_size:
        shutil.copyfile(src, dest)
    return f"games/{dest.name}"


def build_credits(entries: List[dict]) -> List[str]:
    """Attribution lines for the video description."""
    seen: Dict[str, str] = {}
    for e in entries:
        pubs = ", ".join(e.get("publishers") or e.get("developers") or [])
        seen[e["game"]] = f"{e['game']} © {pubs}" if pubs else e["game"]
    return list(seen.values())
