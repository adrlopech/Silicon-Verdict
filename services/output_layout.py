"""Output layout: one folder per video, named after the video title.

output/<platform>/<Video title>/<YYYY-MM-DD_HH-MM-SS>.mp4   (+ _cover.jpg, and .txt metadata for TikTok)
"""
import re
from datetime import datetime
from pathlib import Path
from typing import Optional

from config.settings import settings

OUTPUT_DIR = settings.BASE_DIR / "output"
PLATFORMS = ("youtube", "tiktok")

_HASHTAG = re.compile(r"#\w+")
_ALLOWED = re.compile(r"[^\w\s\-.,'&!()+%]", flags=re.UNICODE)
_EMOJI_AND_SYMBOLS = re.compile(r"[\U0001F000-\U0001FFFF☀-➿️]")


def sanitize_title(title: str, max_len: int = 80) -> str:
    """Readable, filesystem-safe folder name from a video title (hashtags and emojis removed)."""
    t = _EMOJI_AND_SYMBOLS.sub("", title or "")
    t = _HASHTAG.sub("", t)
    t = _ALLOWED.sub("", t)
    t = re.sub(r"\s+", " ", t).strip(" .-_")
    if len(t) > max_len:
        t = t[:max_len].rsplit(" ", 1)[0].strip(" .-_,") or t[:max_len]
    return t or "Untitled video"


def timestamp_stem(now: Optional[datetime] = None) -> str:
    return (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")


def video_dir(platform: str, title: str, create: bool = True) -> Path:
    d = OUTPUT_DIR / platform / sanitize_title(title)
    if create:
        d.mkdir(parents=True, exist_ok=True)
    return d


def mirror_path(video_path: Path, platform: str) -> Path:
    """Same folder/file name for the other platform, e.g. output/youtube/X/ts.mp4 -> output/tiktok/X/ts.mp4."""
    video_path = Path(video_path).resolve()
    for p in PLATFORMS:
        base = (OUTPUT_DIR / p).resolve()
        try:
            rel = video_path.relative_to(base)
            return OUTPUT_DIR / platform / rel
        except ValueError:
            continue
    return OUTPUT_DIR / platform / video_path.name
