"""Compact authoring helpers for hand-written story seeds (data/story_seed/*.py)."""
import re
from typing import Any, Dict, List, Optional

_FILLER_POSES = ["think", "shrug", "idle", "cheer"]


def _cw(w: str) -> str:
    return re.sub(r"[^\w]", "", w.lower())


def _repair_scenes(script: str, scenes: List[Dict[str, Any]], min_scenes: int = 11) -> List[Dict[str, Any]]:
    """Keeps scenes whose anchors appear in spoken order; adds mascot-only beats if there are too few."""
    words = [_cw(w) for w in script.split()]
    kept: List[Dict[str, Any]] = []
    pos = -1
    for scene in scenes:
        a = _cw(scene["word_anchor"])
        nxt = next((i for i, w in enumerate(words) if w == a and i > pos), None)
        if nxt is None:
            continue
        pos = nxt
        kept.append({**scene, "_pos": nxt})
    used = {k["word_anchor"].lower() for k in kept}
    guard = 0
    while len(kept) < min_scenes and guard < 20:
        guard += 1
        # widest gap between consecutive scene positions
        marks = [-1] + [k["_pos"] for k in kept] + [len(words)]
        gaps = sorted(((marks[i + 1] - marks[i], i) for i in range(len(marks) - 1)), reverse=True)
        added = False
        for size, i in gaps:
            if size < 6:
                continue
            mid = (marks[i] + marks[i + 1]) // 2
            for j in sorted(range(marks[i] + 2, marks[i + 1] - 1), key=lambda x: abs(x - mid)):
                if len(words[j]) >= 5 and words[j] not in used and script.split()[j].lower() not in used:
                    kept.insert(i, {"word_anchor": words[j], "pose": _FILLER_POSES[len(kept) % 4], "vector_type": "none", "_pos": j})
                    used.add(words[j])
                    added = True
                    break
            if added:
                break
        if not added:
            break
    kept.sort(key=lambda k: k["_pos"])
    return [{k: v for k, v in sc_.items() if k != "_pos"} for sc_ in kept]


def sc(anchor: str, pose: str = "idle", vt: str = "none", **kw: Any) -> Dict[str, Any]:
    """One scene. kw: icon, icon2, icon3, label, label2, label3, value_from, value_to, a, b, text, flash."""
    return {"word_anchor": anchor, "pose": pose, "vector_type": vt, **kw}


def story(topic: str, banner: str, desc: str, pinned: str, script: str, scenes: List[Dict[str, Any]],
          tags: Optional[List[str]] = None, title: Optional[str] = None) -> Dict[str, Any]:
    """A 'simple' series story (StoryProject)."""
    return {
        "series": "simple",
        "topic": topic,
        "category_name": "EVERYDAY CURIOSITIES",
        "header_banner": banner.upper(),
        "title": title or f"{topic} #Tech #Explained #SiliconVerdict",
        "description": desc,
        "tags": tags or ["SiliconVerdict", "Tech", "Explained", "TechCuriosities", "Shorts"],
        "pinned_comment": pinned,
        "full_script": " ".join(script.split()),
        "scenes": _repair_scenes(" ".join(script.split()), scenes),
    }


def g(anchor: str, label: str, game: Optional[str] = None, ann: Optional[str] = None, flash: bool = False) -> Dict[str, Any]:
    """Game-series beat: a real screenshot of `game` with an annotation, or a data-free text card."""
    if game:
        return {"word_anchor": anchor, "asset_id": "game_frame", "label": label, "game_title": game,
                "annotation": ann or label, "motion_preset": "hero"}
    return {"word_anchor": anchor, "asset_id": "stat_card", "label": label, "annotation": ann,
            "motion_preset": "hero" if flash else "metric"}


def _in_order(script: str, triggers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    words = [_cw(w) for w in script.split()]
    kept: List[Dict[str, Any]] = []
    pos = -1
    for t in triggers:
        a = _cw(t["word_anchor"])
        nxt = next((i for i, w in enumerate(words) if w == a and i > pos), None)
        if nxt is None:
            continue
        pos = nxt
        kept.append(t)
    return kept


def gstory(topic: str, banner: str, desc: str, pinned: str, script: str, triggers: List[Dict[str, Any]],
           tags: Optional[List[str]] = None, title: Optional[str] = None) -> Dict[str, Any]:
    """A 'game' series story (MotionStoryProject)."""
    script = " ".join(script.split())
    return {
        "series": "game",
        "topic": topic,
        "category_id": 3,
        "category_name": "GAME CURIOSITIES",
        "header_banner": banner.upper(),
        "title": title or f"{topic} #GameTech #Gaming #SiliconVerdict",
        "description": desc,
        "tags": tags or ["SiliconVerdict", "GameTech", "Gaming", "GameDev", "Shorts"],
        "pinned_comment": pinned,
        "full_script": script,
        "visual_triggers": [
            {"asset_id": t["asset_id"], "label": t["label"], "word_anchor": t["word_anchor"], "duration_seconds": 3.5,
             "motion_preset": t.get("motion_preset", "hero"), "game_title": t.get("game_title"), "annotation": t.get("annotation")}
            for t in _in_order(script, triggers)
        ],
    }
