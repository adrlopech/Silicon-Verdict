#!/usr/bin/env python3
"""Silicon Verdict Algorithmic Feedback Loop & Analytics Sync.

Connects to YouTube Analytics API v2 / Data API v3:
1. Extracts retention & engagement metrics for the last 20 videos:
   - viewerPercentage (Viewed vs Swiped Away | Target > 70%)
   - averageViewPercentage (APV | Target > 80%)
   - likes & comments ratio
2. Computes performance_score: (viewerPercentage * 0.4) + (averageViewPercentage * 0.6).
3. Calibrates category rotation probabilities in data/category_weights.json:
   - Highest performing category: 50% selection weight.
   - Remaining categories: 25% each.
4. Detects ineffective hooks (Swiped Away > 40%) and registers patterns in data/qa_rules.json.

Usage:
  python scripts/analytics_sync.py               # Sync live metrics
  python scripts/analytics_sync.py --simulate    # Offline simulation mode
"""
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from config.settings import settings
from services.history import (
    get_category_performance_averages,
    get_db_connection,
    init_db,
    record_analytics_metric,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("analytics_sync")

QA_RULES_PATH = BASE_DIR / "data" / "qa_rules.json"
CATEGORY_WEIGHTS_PATH = BASE_DIR / "data" / "category_weights.json"


def load_qa_rules() -> Dict[str, Any]:
    """Loads QA rules JSON."""
    if QA_RULES_PATH.is_file():
        try:
            return json.loads(QA_RULES_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_qa_rules(rules: Dict[str, Any]) -> None:
    """Saves updated QA rules."""
    QA_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    QA_RULES_PATH.write_text(json.dumps(rules, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def save_category_weights(weights: Dict[str, Any]) -> None:
    """Persists dynamic category selection weights."""
    CATEGORY_WEIGHTS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATEGORY_WEIGHTS_PATH.write_text(json.dumps(weights, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("Saved calibrated category weights to %s: %s", CATEGORY_WEIGHTS_PATH, weights.get("weights"))


def fetch_youtube_video_stats(token_file: Path) -> List[Dict[str, Any]]:
    """The channel's real numbers from YouTube Analytics (services/yt_analytics.py): views, engaged views (the closest thing the API has to "viewed instead of swiped away") and the
    average percentage viewed per video. Videos without analytics yet are skipped: no number is ever invented. Returns [] when the token lacks the analytics scopes."""
    from services import yt_analytics as ya

    try:
        vids = ya.videos()
        rep = ya.video_report(90)
    except ya.AnalyticsUnavailable as exc:
        logger.warning("YouTube Analytics is not set up (%s).", exc)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.warning("Live YouTube Analytics query failed (%s).", exc)
        return []
    out = []
    for v in vids:
        r = rep.get(v["video_id"])
        if not r or not r.get("views"):
            continue
        views = int(r["views"])
        out.append({
            "video_id": v["video_id"], "title": v["title"], "views": views, "likes": int(r.get("likes", v["likes"])), "comments": int(r.get("comments", v["comments"])),
            "viewer_percentage": min(100.0, 100.0 * r.get("engagedViews", 0) / views),
            "avg_view_percentage": min(100.0, float(r.get("averageViewPercentage", 0.0))),  # a replayed loop passes 100: capped so the score stays comparable
        })
    logger.info("Read real analytics for %d of %d videos.", len(out), len(vids))
    return out


def generate_simulation_data() -> List[Dict[str, Any]]:
    """Generates realistic retention telemetry for the 3 core pillars to calibrate feedback."""
    return [
        {
            "video_id": "sim_gps_relatividad",
            "title": "Ningún satélite te ve: el secreto relativista de tu móvil",
            "category": "tech_curiosities",
            "theme_key": "gps_relatividad",
            "views": 18450,
            "viewer_percentage": 78.4,    # 78.4% viewed vs 21.6% swiped away
            "avg_view_percentage": 84.2,   # 84.2% completion rate
            "likes": 1240,
            "comments": 142,
        },
        {
            "video_id": "sim_datacenter_luz",
            "title": "La velocidad de la luz es el verdadero cuello de botella",
            "category": "tech_curiosities",
            "theme_key": "velocidad_luz_datacenter",
            "views": 22100,
            "viewer_percentage": 82.1,
            "avg_view_percentage": 86.5,
            "likes": 1680,
            "comments": 210,
        },
        {
            "video_id": "sim_rtx4060_gaming",
            "title": "¿Vale la pena la RTX 4060 a 1080p en 2026?",
            "category": "gaming_benchmarks",
            "theme_key": "gaming_benchmarks",
            "views": 14200,
            "viewer_percentage": 62.0,
            "avg_view_percentage": 68.4,
            "likes": 780,
            "comments": 95,
        },
        {
            "video_id": "sim_am5_zen4",
            "title": "Arquitectura AM5 vs LGA1700: comparativa técnica",
            "category": "hardware_benchmarks",
            "theme_key": "silicon_deep_dive",
            "views": 9800,
            "viewer_percentage": 56.5,    # High swiped away: 43.5%
            "avg_view_percentage": 62.1,
            "likes": 420,
            "comments": 48,
        },
    ]


def run_analytics_sync(simulate: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Runs complete analytics extraction, scoring, category calibration, and hook auditing."""
    init_db()
    token_path = settings.resolve_token_path()

    records = []
    if not simulate and token_path.is_file():
        records = fetch_youtube_video_stats(token_path)

    if records and not dry_run:  # real numbers replace the simulated rows of the first calibration
        with get_db_connection() as conn:
            conn.execute("DELETE FROM analytics_history WHERE video_id LIKE 'sim\\_%' ESCAPE '\\'")
    if not records:
        logger.info("Using simulated retention dataset for feedback loop calibration...")
        records = generate_simulation_data()

    logger.info("Processing %d video analytics records...", len(records))

    synced_count = 0
    high_swiped_hooks = []

    for item in records:
        vid_id = item["video_id"]
        title = item["title"]
        cat = item.get("category", "")
        if not cat:
            if any(w in title.lower() for w in ["satélite", "luz", "cable", "fibra", "asml", "relativid"]):
                cat = "tech_curiosities"
            elif any(w in title.lower() for w in ["4060", "fps", "gaming", "rendimiento"]):
                cat = "gaming_benchmarks"
            else:
                cat = "hardware_benchmarks"

        theme = item.get("theme_key", cat)
        views = item.get("views", 0)
        viewer_pct = item.get("viewer_percentage", 65.0)
        avg_view_pct = item.get("avg_view_percentage", 70.0)
        likes = item.get("likes", 0)
        comments = item.get("comments", 0)

        res = record_analytics_metric(
            video_id=vid_id,
            title=title,
            category=cat,
            theme_key=theme,
            views=views,
            viewer_percentage=viewer_pct,
            avg_view_percentage=avg_view_pct,
            likes=likes,
            comments=comments,
        )
        synced_count += 1

        # Check for ineffective hook: Swiped Away > 40% (viewer_percentage < 60%)
        if res["swiped_away_percentage"] > 40.0:
            high_swiped_hooks.append({
                "video_id": vid_id,
                "title": title,
                "swiped_away_pct": res["swiped_away_percentage"],
            })

    # Calibrate category weights based on real performance score averages
    cat_averages = get_category_performance_averages()
    logger.info("Category Performance Score Averages: %s", cat_averages)

    # Dynamic Weight Adjustment:
    # If a category averages > 75 (e.g. tech_curiosities at ~81), it gets 50% probability, others 25% each.
    best_cat = None
    best_score = -1.0
    for cat, score in cat_averages.items():
        if score > best_score:
            best_score = score
            best_cat = cat

    weights_dict = {
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "category_averages": cat_averages,
        "best_performing_category": best_cat,
        "weights": {},
    }

    if best_cat and best_score >= 70.0:
        # 50% to best category, split remaining 50% among other active categories
        other_cats = [c for c in ["tech_curiosities", "gaming_benchmarks", "hardware_benchmarks"] if c != best_cat]
        weights_dict["weights"][best_cat] = 0.50
        for oc in other_cats:
            weights_dict["weights"][oc] = round(0.50 / len(other_cats), 2)
    else:
        # Equal distribution if no clear runaway winner
        weights_dict["weights"] = {
            "tech_curiosities": 0.34,
            "gaming_benchmarks": 0.33,
            "hardware_benchmarks": 0.33,
        }

    if not dry_run:
        save_category_weights(weights_dict)

    # Ineffective hook registration in data/qa_rules.json
    if high_swiped_hooks and not dry_run:
        qa_rules = load_qa_rules()
        existing_ineffective = qa_rules.setdefault("ineffective_hook_patterns", [])
        for h in high_swiped_hooks:
            entry = f"Baja retención inicial ({h['swiped_away_pct']:.1f}% abandono en T<3s): '{h['title']}'"
            if entry not in existing_ineffective:
                existing_ineffective.append(entry)
                logger.info("Flagged ineffective hook pattern in qa_rules: %s", entry)
        save_qa_rules(qa_rules)

    return {
        "videos_synced": synced_count,
        "category_averages": cat_averages,
        "calibrated_weights": weights_dict["weights"],
        "flagged_ineffective_hooks": len(high_swiped_hooks),
    }


def main():
    parser = argparse.ArgumentParser(description="Silicon Verdict Algorithmic Feedback Loop & Analytics Sync")
    parser.add_argument("--simulate", action="store_true", help="Run with simulated retention dataset")
    parser.add_argument("--dry-run", action="store_true", help="Calculate scores without modifying DB or rules")
    parser.add_argument("--auth", action="store_true", help="Launch OAuth 2.0 flow to grant yt-analytics scopes")
    args = parser.parse_args()

    if args.auth:
        from scripts.authenticate_yt import authenticate_local
        authenticate_local()
        return

    res = run_analytics_sync(simulate=args.simulate, dry_run=args.dry_run)
    print("\n" + "=" * 70)
    print(" 📊 SILICON VERDICT: REPORTE DE SINCRONIZACIÓN DE ANALYTICS")
    print("=" * 70)
    print(f" Vídeos Sincronizados:          {res['videos_synced']}")
    print(f" Promedio Performance Scores:  {res['category_averages']}")
    print(f" Pesos Calibrados de Rotación: {res['calibrated_weights']}")
    print(f" Ganchos Ineficaces Detectados: {res['flagged_ineffective_hooks']}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
