#!/usr/bin/env python3
"""Real retention report of the YouTube channel, with the format and the visual look of each video.

Reads YouTube Analytics (services/yt_analytics.py; needs the token from `python scripts/authenticate_yt.py`), joins every video with data/history.db to know its Motion format and
look, and prints: the channel summary, one row per video, the averages by format and by look, the traffic sources and the last days.
It also writes notes/analytics_report_<date>.md and data/analytics_report.json (both private, git-ignored).

  .venv/bin/python scripts/report_retention.py                # last 90 days, retention curves of every video with 100+ views
  .venv/bin/python scripts/report_retention.py --days 28 --min-views 300

Reading the columns: `engaged` = engaged views / views (the closest the API gets to "viewed instead of swiped away"); `avg%` = average percentage viewed (a loop replayed can pass 100);
`r20 r50 r80` = audience watch ratio a fifth, half and four fifths of the way into the video. Fewer than ~10 videos per format or look is noise, not a result.
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services import yt_analytics as ya  # noqa: E402
from services.history import get_db_connection, init_db  # noqa: E402


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"#\w+", "", title).lower()).strip()


def history_index() -> Dict[str, Dict[str, str]]:
    """video id and normalised title -> {format, look} from shorts_history."""
    init_db()
    out: Dict[str, Dict[str, str]] = {}
    with get_db_connection() as conn:
        for r in conn.execute("SELECT video_id, title, category, preset FROM shorts_history"):
            cat = (r["category"] or "").replace("MOTION GRAPHICS", "").strip().lower() or "classic"
            look = r["preset"].split(":", 1)[1] if (r["preset"] or "").startswith("remotion_motion:") else ""
            info = {"format": cat, "look": look}
            if r["video_id"]:
                out[r["video_id"]] = info
            if r["title"]:
                out[_norm(r["title"])] = info
    return out


def build(days: int, min_views: int) -> Dict[str, Any]:
    ch = ya.channel()
    vids = ya.videos()
    rep = ya.video_report(days)
    hist = history_index()
    rows: List[Dict[str, Any]] = []
    for v in vids:
        r = rep.get(v["video_id"], {})
        views = int(r.get("views", 0))
        info = hist.get(v["video_id"]) or hist.get(_norm(v["title"])) or {}
        curve = ya.retention_curve(v["video_id"], days) if views >= min_views else []
        rows.append({
            "video_id": v["video_id"], "title": v["title"], "published": v["published"][:10], "length": v["seconds"], "privacy": v["privacy"], "views": views,
            "engaged_pct": round(100 * r.get("engagedViews", 0) / views, 1) if views else None,
            "avg_view_pct": round(r.get("averageViewPercentage", 0), 1) if views else None, "avg_seconds": r.get("averageViewDuration"),
            "subs": int(r.get("subscribersGained", 0)), "likes": int(r.get("likes", 0)), "comments": int(r.get("comments", 0)),
            "r20": ya.retention_at(curve, 0.2), "r50": ya.retention_at(curve, 0.5), "r80": ya.retention_at(curve, 0.8),
            "format": info.get("format", ""), "look": info.get("look", ""),
        })
    return {"date": str(date.today()), "days": days, "channel": ch, "videos": rows, "traffic": ya.traffic_sources(days), "daily": ya.daily(14)}


def groups(rows: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    """Views-weighted averages by a field (format or look); videos without it are left out."""
    acc: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in rows:
        if r[key] and r["views"] and r["engaged_pct"] is not None:
            acc[r[key]].append(r)
    out = []
    for name, rs in acc.items():
        w = sum(x["views"] for x in rs)
        out.append({"name": name, "videos": len(rs), "views": w, "engaged": round(sum(x["engaged_pct"] * x["views"] for x in rs) / w, 1), "avg": round(sum(x["avg_view_pct"] * x["views"] for x in rs) / w, 1)})
    return sorted(out, key=lambda g: -g["avg"])


def fmt(v: Optional[float], nd: int = 0) -> str:
    return "-" if v is None else f"{v:.{nd}f}"


def render(rep: Dict[str, Any]) -> str:
    ch = rep["channel"]
    rows = sorted(rep["videos"], key=lambda r: -r["views"])
    lines = [f"# {ch['title']}: retention report ({rep['date']}, last {rep['days']} days)", "",
             f"Subscribers {ch['subscribers']} | videos {ch['videos']} | lifetime views {ch['views']}", "",
             "## Videos", "", "| views | engaged | avg% | avg s / len | r20 | r50 | r80 | subs | format | look | title |", "|--:|--:|--:|--:|--:|--:|--:|--:|--|--|--|"]
    for r in rows:
        lines.append(f"| {r['views']} | {fmt(r['engaged_pct'])}% | {fmt(r['avg_view_pct'])} | {fmt(r['avg_seconds'])} / {r['length']} | {fmt(r['r20'] and r['r20'] * 100)} | {fmt(r['r50'] and r['r50'] * 100)} | "
                     f"{fmt(r['r80'] and r['r80'] * 100)} | {r['subs']} | {r['format'] or '?'} | {r['look'] or '-'} | {r['title'][:52]} |")
    for key, name in (("format", "format"), ("look", "look")):
        g = groups(rows, key)
        lines += ["", f"## By {name} (views-weighted)", ""]
        lines += ["| " + name + " | videos | views | engaged | avg% |", "|--|--:|--:|--:|--:|"] + [f"| {x['name']} | {x['videos']} | {x['views']} | {x['engaged']}% | {x['avg']} |" for x in g] if g else ["Nothing yet: videos carry no " + name + " in the history."]
    lines += ["", "## Traffic sources", "", "| source | views | avg% |", "|--|--:|--:|"] + [f"| {t['insightTrafficSourceType']} | {t['views']} | {t['averageViewPercentage']:.0f} |" for t in rep["traffic"]]
    lines += ["", "## Last days", "", "| day | views | minutes | avg% | subs |", "|--|--:|--:|--:|--:|"] + [f"| {d['day']} | {d['views']} | {d['estimatedMinutesWatched']} | {d['averageViewPercentage']:.0f} | {d['subscribersGained']} |" for d in rep["daily"][-7:]]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--min-views", type=int, default=100, help="only videos with at least this many views get their retention curve read")
    args = ap.parse_args()
    try:
        rep = build(args.days, args.min_views)
    except ya.AnalyticsUnavailable as exc:
        print(f"YouTube Analytics is not set up: {exc}")
        return 1
    text = render(rep)
    notes = BASE_DIR / "notes"
    notes.mkdir(exist_ok=True)
    (notes / f"analytics_report_{rep['date']}.md").write_text(text, encoding="utf-8")
    (BASE_DIR / "data" / "analytics_report.json").write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
