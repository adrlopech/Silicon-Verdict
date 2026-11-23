"""Visual looks of the Motion videos: which one a video gets.

A look (remotion_studio/src/motion/looks.ts) is a whole visual identity: palette, background, headline typeface, alignment, HUD, camera, transitions and caption style.
The audit of Nov 2026 found every video drawn with the same obsidian-and-cyan look, centred, with the same icons: they read as one video. Now each video gets one of fourteen looks,
chosen by the format's affinities, never one of the last few used, and varied by a hash of the topic. All are blue (cyan, ocean, indigo, cobalt, glass, paper, ice, blueprint, neon, midnight, steel, electric, frost, deepsea).
"""
import hashlib
from typing import List, Optional

LOOKS = ("obsidian", "ocean", "indigo", "cobalt", "glass", "paper", "ice", "blueprint", "neon", "midnight", "steel", "electric", "frost", "deepsea")  # all blue: the channel colour in fourteen tonalities

# what each format looks best in (most fitting first); every look is allowed for the classic explainer
AFFINITY = {
    "fix": ("glass", "paper", "steel", "obsidian", "ocean"),
    "decode": ("blueprint", "steel", "ice", "frost", "indigo", "paper"),
    "whatif": ("indigo", "midnight", "ocean", "deepsea", "ice", "glass"),
    "versus": ("cobalt", "neon", "indigo", "electric", "obsidian", "ocean"),
    "evolution": ("ocean", "deepsea", "ice", "midnight", "blueprint", "cobalt"),
    "myth": ("cobalt", "neon", "obsidian", "frost", "glass", "ice"),
    "tier": ("ocean", "electric", "indigo", "neon", "cobalt", "paper"),
    "hardware": ("blueprint", "steel", "obsidian", "glass", "ocean"),
    "simple": ("paper", "ocean", "glass", "ice"),
    "easter": ("indigo", "midnight", "cobalt", "ocean", "obsidian"),
    "top5": ("cobalt", "neon", "electric", "indigo", "ocean", "obsidian"),
    "eli5": ("paper", "glass", "ocean", "ice"),
    "fails": ("obsidian", "neon", "indigo", "cobalt", "blueprint"),
    "numbers": ("blueprint", "steel", "ice", "cobalt", "ocean"),
    "quiz": ("indigo", "neon", "electric", "cobalt", "glass", "ocean"),
    "stop": ("cobalt", "obsidian", "glass", "paper"),
    "rumor": ("glass", "midnight", "ice", "frost", "indigo", "obsidian"),
    "review": ("paper", "obsidian", "ocean", "glass"),
    "news": ("ocean", "frost", "ice", "blueprint", "glass"),
    "priced": ("cobalt", "neon", "obsidian", "electric", "indigo", "ocean"),
    None: LOOKS,
}
AVOID_LAST = 3  # a look is not used again until three other videos have been made


def recent_looks(limit: int = AVOID_LAST) -> List[str]:
    """Looks of the last videos, newest first (best effort: empty on any error). They are stored in shorts_history.preset as 'remotion_motion:<look>'."""
    try:
        from services.history import get_db_connection, init_db

        init_db()
        with get_db_connection() as conn:
            rows = conn.execute("SELECT preset FROM shorts_history WHERE preset LIKE 'remotion_motion:%' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [r["preset"].split(":", 1)[1] for r in rows]
    except Exception:
        return []


def choose_look(fmt: Optional[str], topic: str = "", recent: Optional[List[str]] = None) -> str:
    """The look of a video: from the format's affinities, skipping the recent ones, starting at a point set by the topic so the same format varies from video to video."""
    recent = recent_looks() if recent is None else recent
    pool = list(AFFINITY.get(fmt, LOOKS))
    fresh = [x for x in pool if x not in recent[:AVOID_LAST]] or [x for x in LOOKS if x not in recent[:AVOID_LAST]] or pool
    start = int(hashlib.sha256((topic or "").lower().encode()).hexdigest(), 16)
    return fresh[start % len(fresh)]
