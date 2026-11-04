"""Silicon Verdict Semantic B-Roll Selector.

Selects the most coherent background video clip using:
1. Antagonistic Exclusion Filtering (rejects clips whose conflicts_with matches topic entities).
2. Visual Cooldown (prevents reusing clips from the last 3 generated videos).
3. Semantic Scoring (intersection between clip tags and extracted script entities).
4. Fallback to abstract neutral background (assets/broll/abstract_neutral.mp4).
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent

from config.settings import settings

logger = logging.getLogger("broll_selector")

MANIFEST_PATH = BASE_DIR / "assets" / "broll" / "manifest.json"
BROLL_DIR = BASE_DIR / "assets" / "broll"


def load_manifest() -> Dict[str, Any]:
    """Loads manifest.json or triggers indexer if missing."""
    if not MANIFEST_PATH.is_file():
        logger.info("B-roll manifest not found. Invoking auto-indexer...")
        from scripts.index_broll import index_broll
        index_broll()

    if MANIFEST_PATH.is_file():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Error reading B-roll manifest (%s).", exc)

    return {"version": "1.0", "clips": []}


def save_manifest(manifest: Dict[str, Any]) -> None:
    """Saves updated manifest with incremented usage counters."""
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalize_terms(terms: List[str]) -> Set[str]:
    """Normalizes terms into lowercase tokens."""
    tokens = set()
    for t in terms:
        clean = str(t).lower().replace("_", " ").replace("-", " ")
        for part in clean.split():
            if len(part) > 1:
                tokens.add(part)
        tokens.add(str(t).lower().strip())
    return tokens


def select_broll_clip(
    theme_key: str,
    category: str = "gaming_benchmarks",
    entities: Optional[List[str]] = None,
    cooldown_count: int = 3,
) -> Path:
    """Selects the best B-roll video clip conforming to semantic constraints."""
    manifest = load_manifest()
    clips = manifest.get("clips", [])

    if not clips:
        # Fallback if empty
        fallback = BROLL_DIR / "abstract_neutral.mp4"
        if not fallback.is_file():
            fallback = BROLL_DIR / "test_broll.mp4"
        return fallback

    # Extract topic terms
    topic_terms = [theme_key, category]
    if entities:
        topic_terms.extend(entities)

    topic_tokens = normalize_terms(topic_terms)
    logger.info("Semantic B-Roll Selection for '%s' (%s) | Tokens: %s", theme_key, category, sorted(list(topic_tokens)))

    # Fetch recently used clips for cooldown check
    # Sort all clips by last_used_timestamp descending
    used_clips = [c for c in clips if c.get("last_used_timestamp")]
    used_clips.sort(key=lambda c: c["last_used_timestamp"], reverse=True)
    recent_clip_files = set(c["file"] for c in used_clips[:cooldown_count])

    candidates = []

    for clip in clips:
        clip_file = clip.get("file", "")
        clip_path = BROLL_DIR / clip_file
        if not clip_path.is_file():
            continue

        clip_conflicts = set(str(c).lower().strip() for c in clip.get("conflicts_with", []))
        clip_tags = set(str(t).lower().strip() for t in clip.get("tags", []))
        clip_brand = str(clip.get("brand", "none")).lower()
        clip_component = str(clip.get("component", "")).lower()

        # 1. Antagonistic Exclusion Filter
        antagonistic_match = topic_tokens.intersection(clip_conflicts)
        if antagonistic_match:
            logger.debug("Discarding clip '%s': antagonistic conflict with %s", clip_file, antagonistic_match)
            continue

        # Check brand mismatch
        if clip_brand != "none":
            # If topic has another rival brand, discard
            if clip_brand == "intel" and any(b in topic_tokens for b in ["amd", "ryzen", "radeon"]):
                continue
            if clip_brand == "amd" and any(b in topic_tokens for b in ["intel", "core", "lga1700", "nvidia"]):
                continue
            if clip_brand == "nvidia" and any(b in topic_tokens for b in ["radeon", "rdna"]):
                continue

        # 2. Cooldown check
        in_cooldown = clip_file in recent_clip_files

        # 3. Semantic Scoring
        # Tag overlap
        overlap = topic_tokens.intersection(clip_tags)
        score = len(overlap) * 2

        # Brand bonus
        if clip_brand != "none" and clip_brand in topic_tokens:
            score += 5

        # Component bonus
        if clip_component and clip_component in topic_tokens:
            score += 4

        # Penalize cooldown
        if in_cooldown:
            score -= 6

        # Prefer lower use count on ties
        use_count = clip.get("use_count", 0)

        candidates.append({
            "clip": clip,
            "path": clip_path,
            "score": score,
            "overlap": overlap,
            "use_count": use_count,
            "in_cooldown": in_cooldown,
        })

    # Sort candidates by score descending, then by use_count ascending
    candidates.sort(key=lambda c: (c["score"], -c["use_count"]), reverse=True)

    selected_clip = None
    if candidates and candidates[0]["score"] > 0:
        selected_clip = candidates[0]
        logger.info(
            "Selected optimal B-roll clip '%s' (Score: %d | Overlap: %s | Use count: %d)",
            selected_clip["clip"]["file"],
            selected_clip["score"],
            list(selected_clip["overlap"]),
            selected_clip["use_count"],
        )
    else:
        # Fallback to neutral abstract clip
        neutral_candidate = next((c for c in candidates if c["clip"].get("category") == "abstract"), None)
        if neutral_candidate:
            selected_clip = neutral_candidate
            logger.info("No high-confidence B-roll match. Falling back to abstract neutral: '%s'", selected_clip["clip"]["file"])
        elif candidates:
            selected_clip = candidates[0]
            logger.info("Using highest remaining candidate: '%s'", selected_clip["clip"]["file"])

    if not selected_clip:
        fallback_path = BROLL_DIR / "abstract_neutral.mp4"
        if not fallback_path.is_file():
            fallback_path = BROLL_DIR / "test_broll.mp4"
        return fallback_path

    # Update usage metadata in manifest
    clip_entry = selected_clip["clip"]
    clip_entry["use_count"] = clip_entry.get("use_count", 0) + 1
    clip_entry["last_used_timestamp"] = datetime.now(timezone.utc).isoformat()
    save_manifest(manifest)

    return selected_clip["path"]
