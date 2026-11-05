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
