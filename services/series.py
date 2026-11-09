"""Named, numbered series for the Motion formats ("Fix It Now #7", "Decoded #12").

The content study (notes/content_style_study_2026-11.md) found that the biggest niche accounts run numbered series ("PC tip that can save you - Pt 73"): the title, the first frame and
the hashtag repeat, so a viewer who liked one video recognises the next. Each format has a series name and a one-word hashtag; the number is how many different topics of that format
the history already holds, plus one.
"""
import re
from typing import Any, Dict, Optional, Tuple

from services.history import get_db_connection, init_db

# format -> (series name shown in the title and on the first frame, one-word hashtag without the #)
SERIES: Dict[str, Tuple[str, str]] = {
    "fix": ("Fix It Now", "fixitnow"),
    "decode": ("Decoded", "decoded"),
    "whatif": ("What If", "whatif"),
    "versus": ("Spec Duel", "specduel"),
    "evolution": ("Evolution", "techevolution"),
    "myth": ("Myth or Fact", "mythorfact"),
    "tier": ("Tier List", "pctierlist"),
    "hardware": ("Silicon Files", "siliconfiles"),
    "simple": ("Everyday Tech", "everydaytech"),
}
MAX_TITLE = 100  # MotionProject.title limit
_HASHTAGS = re.compile(r"\s*#\w+")


def next_number(fmt: str) -> int:
    """How many different topics of this format are in shorts_history, plus one."""
    init_db()
    with get_db_connection() as conn:
        row = conn.execute("SELECT COUNT(DISTINCT topic) FROM shorts_history WHERE category = ?", (f"MOTION GRAPHICS {fmt.upper()}",)).fetchone()
    return int(row[0]) + 1


def joined_hashtag(text: str) -> str:
    """'#' plus the text with every space and symbol removed: hashtags are always one joined word."""
    return "#" + re.sub(r"[^0-9A-Za-z]", "", text)


def apply_series(project: Any, number: Optional[int] = None) -> Optional[str]:
    """Prefixes the title with the series label ("Fix It Now #7: ..."), puts the label on the first scene's kicker (the cover frame), adds the series hashtag to the tags and a line to the
    description. Returns the label, or None when the format has no series or the project already carries it."""
    entry = SERIES.get(project.format or "")
    if not entry:
        return None
    name, tag = entry
    if project.title.lower().startswith(name.lower()):
        return None
    n = number if number is not None else next_number(project.format)
    label = f"{name} #{n}"
    hashtags = "".join(_HASHTAGS.findall(project.title))
    text = _HASHTAGS.sub("", project.title).strip()
    room = MAX_TITLE - len(label) - 2 - len(hashtags)
    if len(text) > room:
        text = text[: max(10, room - 1)].rstrip(" ,:;-") + "…"
    project.title = f"{label}: {text}{hashtags}"
    if project.scenes:
        project.scenes[0].kicker = label.lower()
    if tag not in [t.lstrip("#").lower() for t in project.tags]:
        project.tags = list(project.tags) + [tag]
    project.description = project.description.rstrip() + f" Part of the {name} series."
    return label
