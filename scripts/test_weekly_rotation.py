#!/usr/bin/env python3
"""Validation and Simulation Script for Silicon Verdict Weekly Thematic & Voice Rotation.

Simulates 10 consecutive working days (2 full weeks: Lunes a Viernes Semana 1 & Semana 2):
1. Verifies exact alternation between 'theme_a' and 'theme_b' for each weekday week-over-week.
2. Verifies strict Round-Robin rotation across the 3 ElevenLabs voices (1 -> 2 -> 3 -> 1).
3. Verifies zero game repetitions within the 14-day window.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.generator import select_daily_short_spec
from services.history import init_db, record_short_history
from services.voice import get_voice_pool


def run_weekly_rotation_simulation(test_db_path: Path):
    """Executes a 10-day simulation and validates rotation invariants."""
    if test_db_path.exists():
        test_db_path.unlink()
    init_db(test_db_path)

    # Reference start date: Monday Nov 2, 2026
    start_monday = datetime(2026, 11, 2, 9, 0, 0, tzinfo=timezone.utc)
    # 10 working days: Week 1 (Days 0..4), Week 2 (Days 7..11)
    day_offsets = [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]

    simulation_records = []
    voice_pool = get_voice_pool()

    for idx, offset in enumerate(day_offsets):
        current_date = start_monday + timedelta(days=offset)
        weekday = current_date.weekday()
        week_num = 1 if idx < 5 else 2

        # 1. Generate daily specification
        spec = select_daily_short_spec(
            weekday_index=weekday,
            db_path=test_db_path,
            ref_date=current_date,
        )

        # 2. Record short in database
        topic_summary = f"{spec.theme_description} in {spec.game_title}"
        title = f"{spec.pillar_title} Telemetry: {spec.game_title} #Shorts"
        record_short_history(
            weekday_index=spec.weekday_index,
            theme_key=spec.theme_key,
            game_title=spec.game_title,
            voice_id_used=spec.voice_id,
            topic=topic_summary,
            title=title,
            video_id=f"sim_vid_{idx + 1:02d}",
            created_at=current_date.isoformat(),
            db_path=test_db_path,
        )

        voice_idx = voice_pool.index(spec.voice_id) + 1 if spec.voice_id in voice_pool else 0

        simulation_records.append({
            "step": idx + 1,
            "week": week_num,
            "date_str": current_date.strftime("%Y-%m-%d"),
            "weekday_idx": weekday,
            "day_name": spec.day_name,
            "pillar_title": spec.pillar_title,
            "theme_key": spec.theme_key,
            "theme_desc": spec.theme_description,
            "game_title": spec.game_title,
            "voice_id": spec.voice_id,
            "voice_num": f"VOICE_{voice_idx}",
        })

    # =========================================================================
    # DISPLAY SIMULATION RESULTS TABLE
    # =========================================================================
    print("\n" + "=" * 120)
    print(" === SILICON VERDICT: SIMULACIÓN DE ROTACIÓN SEMANAL (10 DÍAS LABORABLES / 2 SEMANAS) ===")
    print("=" * 120)
    header = (
        f"{'Día':<4} | {'Fecha':<10} | {'Semana':<6} | {'Día / Pilar':<24} | "
        f"{'Subtema':<8} | {'Voz ElevenLabs':<14} | {'Juego Seleccionado (Pool 6)':<26}"
    )
    print(header)
    print("-" * 120)

    for r in simulation_records:
        day_p = f"{r['day_name']} ({r['pillar_title']})"
        row = (
            f"#{r['step']:<3} | {r['date_str']:<10} | Sem {r['week']:<2} | {day_p:<24} | "
            f"{r['theme_key']:<8} | {r['voice_num']:<14} | {r['game_title']:<26}"
        )
        print(row)
        if r["step"] == 5:
            print("-" * 120)

    print("=" * 120)

    # Detailed breakdown of themes
    print("\n[DETALLE DE TEMÁTICAS ASIGNADAS]")
    for r in simulation_records:
        print(f" • Día #{r['step']:02d} ({r['day_name']}, Sem {r['week']}) [{r['theme_key']}]: {r['theme_desc']}")

    # =========================================================================
    # INVARIANT VALIDATIONS & ASSERTIONS
    # =========================================================================
    print("\n" + "=" * 80)
    print(" === VALIDACIÓN DE REGLAS DE NEGOCIO Y ROTACIÓN ===")
    print("=" * 80)

    # 1. Validation: Theme Alternation per Weekday
    theme_errors = []
    for w in range(5):
        w1_record = simulation_records[w]
        w2_record = simulation_records[w + 5]

        if w1_record["theme_key"] != "theme_a":
            theme_errors.append(f"Semana 1 ({w1_record['day_name']}) debió ser 'theme_a', fue '{w1_record['theme_key']}'")
        if w2_record["theme_key"] != "theme_b":
            theme_errors.append(f"Semana 2 ({w2_record['day_name']}) debió ser 'theme_b', fue '{w2_record['theme_key']}'")

    if not theme_errors:
        print(" [✓] REGLA 1 (Alternancia de Subtemas): SUPERADA")
        print("     Semana 1 operó 100% en 'theme_a' y Semana 2 alternó 100% a 'theme_b' para cada día.")
    else:
        print(" [X] REGLA 1 FALLÓ:")
        for e in theme_errors:
            print(f"     - {e}")

    # 2. Validation: Strict Round-Robin Voice Sequence (1 -> 2 -> 3 -> 1)
    voice_errors = []
    expected_voices = [
        voice_pool[0], voice_pool[1], voice_pool[2],
        voice_pool[0], voice_pool[1], voice_pool[2],
        voice_pool[0], voice_pool[1], voice_pool[2],
        voice_pool[0]
    ]

    for idx, (rec, exp) in enumerate(zip(simulation_records, expected_voices)):
        if rec["voice_id"] != exp:
            voice_errors.append(f"Día #{idx + 1}: Esperada voz '{exp}', asignada '{rec['voice_id']}'")

    # Consecutive repeat check
    for idx in range(len(simulation_records) - 1):
        if simulation_records[idx]["voice_id"] == simulation_records[idx + 1]["voice_id"]:
            voice_errors.append(f"Días #{idx + 1} y #{idx + 2} repitieron la misma voz consecutiva.")

    if not voice_errors:
        print(" [✓] REGLA 2 (Rotación Round-Robin de 3 Voces): SUPERADA")
        print("     Secuencia exacta: VOICE_1 -> VOICE_2 -> VOICE_3 -> VOICE_1 -> VOICE_2...")
        print("     Cero repeticiones consecutivas entre Shorts.")
    else:
        print(" [X] REGLA 2 FALLÓ:")
        for e in voice_errors:
            print(f"     - {e}")

    # 3. Validation: Game Veto Window (Zero duplicate games in 14 days)
    selected_games = [r["game_title"] for r in simulation_records]
    unique_games = set(selected_games)
    duplicate_errors = []

    if len(selected_games) != len(unique_games):
        seen = set()
        for g in selected_games:
            if g in seen:
                duplicate_errors.append(f"Juego duplicado dentro de la ventana de 14 días: '{g}'")
            seen.add(g)

    if not duplicate_errors:
        print(" [✓] REGLA 3 (Filtro de Juegos en Ventana de 14 Días): SUPERADA")
        print(f"     Se seleccionaron {len(unique_games)} juegos distintos en 10 días laborables.")
        print("     Cero repeticiones en la ventana de 14 días.")
    else:
        print(" [X] REGLA 3 FALLÓ:")
        for e in duplicate_errors:
            print(f"     - {e}")

    print("=" * 80 + "\n")

    # Final assertion
    assert not theme_errors, "Error en alternancia de subtemas"
    assert not voice_errors, "Error en secuencia de voces"
    assert not duplicate_errors, "Error en veto de juegos"
    print(" >>> TODAS LAS COMPROBACIONES DE ROTACIÓN SE SUPERARON CON ÉXITO <<<\n")


def main():
    test_db = BASE_DIR / "data" / "test_weekly_rotation.db"
    try:
        run_weekly_rotation_simulation(test_db)
    finally:
        # Keep test db or clean up
        pass


if __name__ == "__main__":
    main()
