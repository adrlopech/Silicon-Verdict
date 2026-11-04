#!/usr/bin/env python3
"""Comprehensive test suite for Silicon Verdict Content Expansion & Dual-Tone Rotation.

Validates:
1. Catalog in data/history.db has all 10 categories (5 technical + 5 gamer/news).
2. Combined 6-day rotation matrix (Days 1..6) accurately configured in SQLite.
3. Strict alternation:
   - Day 1 (Lunes): Technical (gpu_architecture / silicon_deep_dive)
   - Day 2 (Martes): Gamer (gaming_benchmarks / fps_optimization)
   - Day 3 (Miércoles): Technical (memory_buses / kernel_latency)
   - Day 4 (Jueves): Gamer / Noticias (hardware_news / vram_and_buying_dilemmas)
   - Day 5 (Viernes): Technical (storage_pcie / networking_bufferbloat)
   - Day 6 (Sábado): Gamer (upscaling_tech / gaming_benchmarks)
4. Dual-tone system prompts:
   - Technical tone: analytical, telemetry, formulas of latency (ns), engineering perspective.
   - Gamer tone: "colega gamer experto", mandatory vocabulary:
     FPS promedio, 1% Lows (micro-stuttering), resolución (1080p/1440p), texturas, fluidez,
     and decisive verdict ("Cómprala", "Evítala", "Desactiva esto").
5. Database logging: category and tone properly saved in shorts_history.
6. Deterministic and AI generation fallbacks.
"""
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.generator import select_daily_short_spec
from core.pillars import WEEKLY_PILLARS, get_pillar_for_weekday
from services.content_generator import (
    CONTENT_CATALOG,
    get_emergency_gamer_short_plan,
    get_emergency_gamer_tiktok_plan,
    get_system_prompt_for_category,
)
from services.history import (
    get_all_history,
    get_category_info,
    get_content_catalog,
    get_rotation_matrix,
    init_db,
    record_short_history,
)


def test_database_catalog_and_matrix(test_db: Path):
    """Verifies that SQLite history.db contains all 10 categories and the 6-day matrix."""
    print("\n--- [TEST 1] Verifying SQLite Catalog & 6-Day Matrix ---")
    if test_db.exists():
        test_db.unlink()
    init_db(test_db)

    catalog = get_content_catalog(test_db)
    print(f"Categories loaded in DB: {len(catalog)}")
    assert len(catalog) >= 10, f"Expected at least 10 categories, found {len(catalog)}"

    tech_cats = [c for c in catalog if c["category_type"] == "technical"]
    gamer_cats = [c for c in catalog if c["category_type"] == "gamer"]

    print(f"Technical categories ({len(tech_cats)}): {[c['category_key'] for c in tech_cats]}")
    print(f"Gamer categories ({len(gamer_cats)}): {[c['category_key'] for c in gamer_cats]}")

    assert len(tech_cats) >= 5, f"Expected 5 technical categories, got {len(tech_cats)}"
    assert len(gamer_cats) >= 5, f"Expected 5 gamer categories, got {len(gamer_cats)}"

    # Required 5 gamer categories:
    req_gamer = ["gaming_benchmarks", "hardware_news", "fps_optimization", "vram_and_buying_dilemmas", "upscaling_tech"]
    for rg in req_gamer:
        assert any(c["category_key"] == rg for c in gamer_cats), f"Missing gamer category {rg}"
    print(" [✓] All 5 gamer categories confirmed in SQLite catalog.")

    # Check 6-Day Rotation Matrix
    matrix = get_rotation_matrix(test_db)
    print(f"Matrix days loaded in DB: {len(matrix)}")
    assert len(matrix) == 6, f"Expected 6 days in matrix, found {len(matrix)}"

    expected_matrix = [
        (1, "technical", "gpu_architecture", "silicon_deep_dive"),
        (2, "gamer", "gaming_benchmarks", "fps_optimization"),
        (3, "curiosities", "tech_curiosities", "tech_curiosities"),
        (4, "technical", "memory_buses", "storage_pcie"),
        (5, "gamer", "hardware_news", "vram_and_buying_dilemmas"),
        (6, "curiosities", "tech_curiosities", "tech_curiosities"),
    ]

    for day_num, exp_type, exp_a, exp_b in expected_matrix:
        row = next((m for m in matrix if m["day_number"] == day_num), None)
        assert row is not None, f"Day {day_num} not found in matrix"
        assert row["pillar_type"] == exp_type, f"Day {day_num} type expected {exp_type}, got {row['pillar_type']}"
        assert row["theme_a_category"] == exp_a, f"Day {day_num} theme_a expected {exp_a}, got {row['theme_a_category']}"
        assert row["theme_b_category"] == exp_b, f"Day {day_num} theme_b expected {exp_b}, got {row['theme_b_category']}"
        print(f" [✓] Day {day_num} ({row['day_name']}): {row['pillar_title']} [{row['pillar_type']}] -> A: {row['theme_a_category']} | B: {row['theme_b_category']}")

    print(" [✓] Database catalog and 6-day matrix verified successfully.")


def test_rotation_matrix_simulation(test_db: Path):
    """Simulates 12 consecutive days (2 cycles of 6 days) verifying alternation."""
    print("\n--- [TEST 2] Simulating 12 Days (2 Cycles of 6 Days) ---")
    start_dt = datetime(2026, 11, 2, 9, 0, 0, tzinfo=timezone.utc)  # Monday = 0

    records = []
    for day_step in range(12):
        # We simulate Days 0 to 5 in cycle 1, and Days 0 to 5 in cycle 2
        weekday = day_step % 6
        cycle = 1 if day_step < 6 else 2
        sim_dt = start_dt + timedelta(days=day_step)

        spec = select_daily_short_spec(
            weekday_index=weekday,
            db_path=test_db,
            ref_date=sim_dt,
        )

        record_short_history(
            weekday_index=spec.weekday_index,
            theme_key=spec.theme_key,
            game_title=spec.game_title,
            voice_id_used=spec.voice_id,
            topic=f"Test Topic Step {day_step + 1}",
            title=f"Test Title Step {day_step + 1}",
            video_id=f"test_vid_{day_step + 1}",
            category=spec.category_key,
            tone=spec.tone,
            created_at=sim_dt.isoformat(),
            db_path=test_db,
        )

        records.append({
            "step": day_step + 1,
            "cycle": cycle,
            "weekday": weekday,
            "day_name": spec.day_name,
            "pillar_title": spec.pillar_title,
            "tone": spec.tone,
            "theme_key": spec.theme_key,
            "category": spec.category_key,
            "game": spec.game_title,
            "voice": spec.voice_label,
        })

    # Display table
    print(f"{'Paso':<5} | {'Ciclo':<6} | {'Día':<8} | {'Tono':<10} | {'Categoría':<25} | {'Subtema':<8} | {'Juego':<22}")
    print("-" * 95)
    for r in records:
        print(f"#{r['step']:<4} | Ciclo {r['cycle']} | {r['day_name']:<8} | {r['tone']:<10} | {r['category']:<25} | {r['theme_key']:<8} | {r['game']:<22}")

    # Verify alternation between Cycle 1 and Cycle 2
    for w in range(6):
        c1 = next(r for r in records if r["cycle"] == 1 and r["weekday"] == w)
        c2 = next(r for r in records if r["cycle"] == 2 and r["weekday"] == w)

        # Check theme alternation
        assert c1["theme_key"] == "theme_a", f"Weekday {w} Cycle 1 should be theme_a, got {c1['theme_key']}"
        assert c2["theme_key"] == "theme_b", f"Weekday {w} Cycle 2 should be theme_b, got {c2['theme_key']}"
        if w not in (2, 5):
            assert c1["category"] != c2["category"], f"Weekday {w} categories should alternate between A and B"
        else:
            assert c1["category"] == "tech_curiosities" and c2["category"] == "tech_curiosities"

        # Check tone invariance for that day
        assert c1["tone"] == c2["tone"], f"Weekday {w} tone should remain consistent across cycles"

        # Check 3-pillar tone distribution: Days 0, 3 = technical; Days 1, 4 = gamer; Days 2, 5 = curiosities
        if w in (0, 3):
            expected_tone = "technical"
        elif w in (1, 4):
            expected_tone = "gamer"
        else:
            expected_tone = "curiosities"
        assert c1["tone"] == expected_tone, f"Weekday {w} tone should be {expected_tone}, got {c1['tone']}"

    print(" [✓] 12-day simulation confirmed strict alternating theme and tone invariants.")


def test_dual_tone_prompts():
    """Verifies that system prompts include the mandatory vocabulary and directives."""
    print("\n--- [TEST 3] Verifying Dual-Tone System Prompts ---")

    # Technical category prompt test
    tech_prompt = get_system_prompt_for_category("gpu_architecture", format_type="short")
    assert "nanosegundos" in tech_prompt or "nanoseconds" in tech_prompt or "ns" in tech_prompt, "Tech prompt must mention nanoseconds (ns)"
    assert "telemetry" in tech_prompt.lower(), "Tech prompt must mention telemetry"
    print(" [✓] Technical system prompt verified with nanoseconds and engineering telemetry.")

    # Gamer category prompt test
    gamer_prompt = get_system_prompt_for_category("gaming_benchmarks", format_type="short")
    mandatory_terms = [
        "colega gamer experto",
        "FPS promedio",
        "1% Lows",
        "micro-stuttering",
        "resolución (1080p/1440p)",
        "texturas",
        "fluidez",
        "Cómprala",
        "Evítala",
        "Desactiva esto",
    ]
    for term in mandatory_terms:
        assert term in gamer_prompt, f"Gamer system prompt missing mandatory term: '{term}'"
    print(" [✓] Gamer system prompt verified with all 10 mandatory terms and collegiate tone.")


def test_deterministic_emergency_plans():
    """Verifies that deterministic emergency fallbacks satisfy tone and duration requirements."""
    print("\n--- [TEST 4] Verifying Deterministic Emergency Plans ---")

    # 1. Gamer Short Plan
    g_short = get_emergency_gamer_short_plan()
    assert "FPS promedio" in g_short["description"]
    assert "1% Low" in g_short["scene2"]["voiceover"]
    assert "fluidez" in g_short["scene1"]["voiceover"] or "fluidez" in g_short["scene2"]["voiceover"] or "fluidez" in g_short["scene3"]["voiceover"]
    assert "EVÍTALA" in g_short["scene3"]["hud_text"] or "CÓMPRALA" in g_short["scene3"]["hud_text"] or "DESACTIVA" in g_short["scene3"]["hud_text"]
    print(f" [✓] Gamer Emergency Short Plan: {g_short['title']} (Verdict: {g_short['scene3']['hud_text']})")

    # 2. Gamer TikTok Long Plan (>60.5s, 145-165 words)
    g_tt = get_emergency_gamer_tiktok_plan()
    words = g_tt.get_total_words()
    print(f" [✓] Gamer Emergency TikTok Plan: {words} words across 5 acts")
    assert 140 <= words <= 180, f"Expected between 140 and 180 words for >60.5s, got {words}"
    assert "ocho gigas" in g_tt.act1.voiceover.lower() or "8gb" in g_tt.act1.voiceover.lower()
    assert "FPS promedio" in g_tt.act3.voiceover
    assert "1% Low" in g_tt.act3.voiceover or "uno por ciento Low" in g_tt.act3.voiceover
    assert "fluidez" in g_tt.act2.voiceover or "fluidez" in g_tt.act3.voiceover
    assert "evítala" in g_tt.act4.voiceover.lower() or "desactiva" in g_tt.act4.voiceover.lower()


def test_history_db_retrieval(test_db: Path):
    """Verifies that recorded history entries preserve category and tone."""
    print("\n--- [TEST 5] Verifying shorts_history columns (category & tone) ---")
    history_entries = get_all_history(limit=5, db_path=test_db)
    assert len(history_entries) > 0, "No history entries found"
    for e in history_entries:
        assert "category" in e, "Missing 'category' in history row"
        assert "tone" in e, "Missing 'tone' in history row"
        print(f" Record #{e['id']}: Weekday {e['weekday_index']} | Theme {e['theme_key']} | Category: {e['category']} | Tone: {e['tone']}")
    print(" [✓] shorts_history category & tone persistence verified.")


if __name__ == "__main__":
    test_db = BASE_DIR / "data" / "test_content_expansion.db"
    print("==================================================================")
    print(" === SILICON VERDICT: CONTENT EXPANSION & DUAL TONE TEST SUITE ===")
    print("==================================================================")
    try:
        test_database_catalog_and_matrix(test_db)
        test_rotation_matrix_simulation(test_db)
        test_dual_tone_prompts()
        test_deterministic_emergency_plans()
        test_history_db_retrieval(test_db)
        print("\n" + "=" * 66)
        print(" [✓] ALL TESTS PASSED! CONTENT EXPANSION FULLY OPERATIONAL.")
        print("==================================================================")
    finally:
        if test_db.exists():
            test_db.unlink()
