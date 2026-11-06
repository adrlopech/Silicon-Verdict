"""Source dossier for game videos: real text about the game (Wikipedia article + Steam store description) that the script must stick to.

Generation is told to use only this text for claims about the game, and the fact-check pass flags anything the text does not support.
Dossiers are cached in data/game_facts/ so each game is fetched once.
"""
import logging
import re
import time
from typing import Optional

import requests

from config.settings import settings

logger = logging.getLogger(__name__)
CACHE_DIR = settings.BASE_DIR / "data" / "game_facts"
HEADERS = {"User-Agent": "SiliconVerdict-facts/1.0 (educational video channel)"}
WIKI = "https://en.wikipedia.org/w/api.php"
MAX_CHARS = 3800
MIN_CHARS = 900   # below this the sources are thin (the script is then told to stay conservative)
WANTED = re.compile(r"develop|technolog|engine|design|gameplay|graphics|release|rendering|production|music|audio|mechanics|multiplayer|modding|legacy", re.I)


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


_last_call = 0.0
MIN_GAP = 1.3  # seconds between Wikipedia requests: the API answers 429 to bursts


def _paced_get(url: str, params: Optional[dict] = None) -> requests.Response:
    """GET with a global minimum gap between requests and Retry-After handling; up to 6 tries."""
    global _last_call
    r = None
    for attempt in range(1, 7):
        wait = MIN_GAP - (time.time() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()
        r = requests.get(url, params=params, headers=HEADERS, timeout=30)
        if r.status_code == 200:
            return r
        try:
            pause = float(r.headers.get("Retry-After", 0))
        except ValueError:
            pause = 0.0
        time.sleep(min(30.0, max(pause, 2.0 * attempt)))
    return r


def _wiki_json(params: dict) -> dict:
    r = _paced_get(WIKI, params)
    try:
        return r.json()
    except ValueError:
        raise RuntimeError(f"Wikipedia kept refusing (last status {r.status_code})") from None


def _wikipedia(game: str) -> str:
    """Lead + the most relevant sections of the game's English Wikipedia article (plain text), or ''."""
    try:
        hits = _wiki_json({"action": "query", "list": "search", "srsearch": f"{game} video game", "srlimit": 6, "format": "json"})["query"]["search"]
        if not hits:
            return ""
        import difflib
        norm = lambda t: re.sub(r"[^a-z0-9]+", " ", re.sub(r"\(.*?\)", "", t.lower().replace("ultimate edition", "").replace("special edition", "").replace("legacy", "").replace("remastered", ""))).strip()
        title = max(hits, key=lambda h: difflib.SequenceMatcher(None, norm(game), norm(h["title"])).ratio())["title"]  # the article whose title is closest to the game name
        pages = _wiki_json({"action": "query", "prop": "extracts", "explaintext": 1, "titles": title, "format": "json", "redirects": 1})["query"]["pages"]
        text = next(iter(pages.values())).get("extract", "")
    except Exception as exc:
        logger.warning("Wikipedia API failed for %s (%s): trying the REST summary.", game, str(exc)[:80])
        try:
            hits = requests.get("https://en.wikipedia.org/w/rest.php/v1/search/title", params={"q": f"{game} video game", "limit": 1}, headers=HEADERS, timeout=20).json()["pages"]
            r = _paced_get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{hits[0]['key']}")
            return r.json().get("extract", "") if r.status_code == 200 else ""
        except Exception as exc2:
            logger.warning("Wikipedia REST also failed for %s: %s", game, str(exc2)[:80])
            return ""
    parts = re.split(r"\n==+ *([^=\n]+?) *==+\n", text)  # [lead, heading1, body1, heading2, body2, ...]
    out = [parts[0].strip()[:1400]]
    for head, body in zip(parts[1::2], parts[2::2]):
        if WANTED.search(head) and body.strip():
            out.append(f"{head.strip()}: {body.strip()}")
    return re.sub(r"\n{2,}", "\n", "\n".join(out))


def _steam(game: str) -> str:
    """Steam store description of the game (official wording), or ''."""
    try:
        from services.game_images import load_manifest
        appid = next((e["appid"] for sec in ("images", "videos") for e in load_manifest()[sec] if e["game"] == game and e.get("appid")), None)
        if not appid:
            return ""
        d = requests.get("https://store.steampowered.com/api/appdetails", params={"appids": appid, "l": "english"}, headers=HEADERS, timeout=20).json()[str(appid)]["data"]
        text = re.sub(r"<[^>]+>", " ", d.get("about_the_game") or d.get("short_description") or "")
        return re.sub(r"\s+", " ", text).strip()[:1200]
    except Exception as exc:
        logger.warning("Steam description failed for %s: %s", game, str(exc)[:100])
        return ""


def get_game_facts(game: str) -> Optional[str]:
    """The source dossier for a game: cached, or built now from Wikipedia + Steam. Returns whatever real text exists (even Steam alone, even short);
    None only when there is no source text at all - the caller then writes the video in 'restrictive mode' (no figures, only well-known facts)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = CACHE_DIR / f"{_slug(game)}.txt"
    if cache.is_file():
        return cache.read_text(encoding="utf-8")
    wiki, steam = _wikipedia(game), _steam(game)
    text = ((f"[Wikipedia]\n{wiki}\n\n" if wiki else "") + (f"[Steam store]\n{steam}" if steam else "")).strip()[:MAX_CHARS]
    if wiki and text:  # only a complete dossier is cached (a Steam-only one would hide a temporary Wikipedia failure)
        cache.write_text(text, encoding="utf-8")
    if len(text) < MIN_CHARS:
        logger.warning("Thin source text for '%s' (%d chars): the video will be written conservatively.", game, len(text))
    return text or None


def figures_in(text: str) -> set:
    """Every number written in the dossier (thousand separators removed), as floats."""
    out = set()
    for m in re.findall(r"\d[\d,]*(?:\.\d+)?", text):
        try:
            out.add(float(m.replace(",", "")))
        except ValueError:
            pass
    return out
