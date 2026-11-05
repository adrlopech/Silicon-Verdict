#!/usr/bin/env python3
"""Silicon Verdict Production Scheduler & Daily Rotation Orchestrator.

Manages automated weekly publication rotation across YouTube Shorts and TikTok:
- Monday (0): GPU & Render (theme_a / theme_b alternated)
- Tuesday (1): CPU & Silicon (Cache Hierarchy vs Silicon Degradation)
- Wednesday (2): Memory & Buses (Dual vs Single Channel vs DDR5 Timings)
- Thursday (3): Efficiency & Bottlenecks (Undervolting vs CPU Bottlenecks)
- Friday (4): Generational Leaps & Pricing (Gen-over-Gen Value vs Used Market)

Execution Schedule:
- Triggers automatically at PUBLISH_TIME configured in .env (default: 14:00 UTC/local).
- YouTube Short (25-35s / 35-45s) is produced and uploaded using data/token.json.
- TikTok Vertical Long (61-68s) is produced in Staging Mode (output/tiktok/) if API token
  is pending review, or published directly via TikTok Content Posting API v2 once token exists.
- Strict Round-Robin rotation of 3 ElevenLabs voices recorded in data/history.db.
- Structured persistent logging to logs/pipeline.log.
"""
import argparse
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure venv bin (where ffmpeg/ffprobe live) is in PATH
venv_bin = BASE_DIR / ".venv" / "bin"
if venv_bin.is_dir() and str(venv_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

# Ensure required directories exist
(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "data").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "output" / "youtube").mkdir(parents=True, exist_ok=True)
(BASE_DIR / "output" / "tiktok").mkdir(parents=True, exist_ok=True)

from config.settings import settings
from core.generator import select_daily_short_spec
from main import run_master_video_pipeline
from services.cleaner import purge_previous_day_videos
from services.history import init_db

# Configure dual logging: console stdout + structured logs/pipeline.log
log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
date_format = "%Y-%m-%d %H:%M:%S"

file_handler = logging.FileHandler(BASE_DIR / "logs" / "pipeline.log", encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format, datefmt=date_format))

root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
if not any(isinstance(h, logging.FileHandler) for h in root_logger.handlers):
    root_logger.addHandler(file_handler)

logger = logging.getLogger("silicon_verdict_scheduler")


WEEKDAY_NAMES = {
    0: "Lunes (GPU & Render)",
    1: "Martes (CPU & Silicio)",
    2: "Miércoles (Memorias & Buses)",
    3: "Jueves (Eficiencia & Bottlenecks)",
    4: "Viernes (Saltos Generacionales & Precios)",
    5: "Sábado (Compilación & Weekend Special)",
    6: "Domingo (Resumen Semanal)",
}


def execute_daily_production(
    weekday_index: Optional[int] = None,
    dry_run: bool = False,
    export_only: bool = False,
    privacy: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, Any]:
    """Executes the complete daily production cycle: YouTube Short + TikTok Video."""
    init_db()
    w_idx = weekday_index if weekday_index is not None else datetime.now().weekday()
    day_label = WEEKDAY_NAMES.get(w_idx, f"Weekday {w_idx}")
    timestamp_start = time.time()
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    logger.info("================================================================================")
    logger.info(">>> INICIANDO CICLO DIARIO SILICON VERDICT: %s <<<", day_label.upper())
    logger.info("Fecha / Hora:     %s", date_str)
    logger.info("Modo Dry Run:     %s", dry_run)
    logger.info("TikTok Export:    %s", "FORZADO LOCAL (STAGING)" if export_only else "AUTO (STAGING / DIRECTO)")
    logger.info("================================================================================")

    # 0. Retention policy enforcement: Automatically purge previous day's videos
    purge_info = purge_previous_day_videos(clean_temp=True, dry_run=dry_run)
    if purge_info["deleted_videos"]:
        logger.info(
            "[RETENCIÓN] %d vídeos del día anterior eliminados automáticamente (Liberados: %.2f MB)",
            len(purge_info["deleted_videos"]),
            purge_info["freed_mb"],
        )

    # 1. Resolve daily specification and voice rotation
    spec = select_daily_short_spec(weekday_index=w_idx)
    target_category = category or spec.category_key
    logger.info(
        "Pilar Temático:  %s (%s) [%s]\n"
        "Categoría:       %s\n"
        "Subtema (%s):   '%s'\n"
        "Juego Asignado:  '%s'\n"
        "Voz ElevenLabs:  %s (ID: %s)",
        spec.day_name,
        spec.pillar_title,
        spec.tone.upper(),
        target_category,
        spec.theme_key,
        spec.theme_description,
        spec.game_title,
        spec.voice_label,
        spec.voice_id,
    )

    results = {
        "weekday_index": w_idx,
        "day_label": day_label,
        "category_key": target_category,
        "tone": spec.tone,
        "theme_key": spec.theme_key,
        "game_title": spec.game_title,
        "voice_id": spec.voice_id,
        "youtube": None,
        "tiktok": None,
        "errors": [],
    }

    # =========================================================================
    # SINGLE UNIFIED MASTER VIDEO PIPELINE (60-120s)
    # Renders 1 master vertical video, publishes to YouTube, and stages for TikTok
    # =========================================================================
    logger.info("--- Producción de Vídeo Máster Vertical Unificado (1080x1920 @ 60 FPS | 60-120s) ---")
    yt_privacy = privacy or settings.YOUTUBE_PRIVACY_STATUS or "public"

    try:
        master_res = run_master_video_pipeline(
            topic=None,
            category=target_category,
            platform="all",
            dry_run=dry_run,
            privacy=yt_privacy,
            export_only=export_only,
            preset=getattr(spec, "preset", "auto"),
            weekday_index=w_idx,
        )

        results["youtube"] = {
            "title": master_res.get("title"),
            "shorts_url": master_res.get("youtube_url"),
            "short_id": master_res.get("youtube_url", "").split("/")[-1],
            "local_file": master_res.get("youtube_video"),
            "duration": master_res.get("duration", 0.0),
        }

        v_path = Path(master_res.get("tiktok_video", ""))
        m_path = Path(master_res.get("tiktok_metadata", ""))
        c_path = Path(master_res.get("tiktok_cover", ""))
        results["tiktok"] = {
            "status": "STAGING_MODE",
            "staging_data": {
                "video_path": str(v_path),
                "metadata_path": str(m_path),
                "cover_path": str(c_path),
            },
            "title": master_res.get("title"),
            "duration": master_res.get("duration", 0.0),
            "file_size_mb": master_res.get("file_size_mb", 0.0),
            "estimated_cost_usd": master_res.get("estimated_cost_usd", 0.0),
            "broll_used": master_res.get("broll_used", ""),
            "tags": master_res.get("tags", []),
        }

        logger.info(
            "[✓] Vídeo Máster Unificado completado con éxito: '%s' (Duración: %.2fs)",
            master_res.get("title"),
            master_res.get("duration", 0.0),
        )
    except Exception as exc:
        err_msg = f"Fallo en Master Video Pipeline: {exc}"
        logger.error(err_msg, exc_info=True)
        results["errors"].append(err_msg)

    total_dur = time.time() - timestamp_start
    logger.info("================================================================================")
    logger.info(
        ">>> RESUMEN CICLO DIARIO COMPLETADO [%s] (Duración total: %.2fs) <<<",
        day_label,
        total_dur,
    )
    if results["errors"]:
        logger.warning("Incidentes registrados (%d): %s", len(results["errors"]), "; ".join(results["errors"]))
    else:
        logger.info("Estado: 100% OPERATIVO SIN INCIDENTES. Rotación guardada en data/history.db.")
    logger.info("================================================================================")

    # Clean, structured summary block in terminal
    print("\n" + "=" * 80)
    print(" >>> SILICON VERDICT • RESUMEN DE EJECUCIÓN DEL PIPELINE UNIFICADO <<<")
    print("=" * 80)
    if results.get("youtube"):
        yt = results["youtube"]
        print(" [1] YOUTUBE SHORTS (Vídeo Máster 60-120s)")
        print(f"     • Estado:         PUBLICADO EN VIVO ({yt_privacy.upper()})")
        print(f"     • ID / URL:       {yt.get('shorts_url')}")
        print(f"     • Título:         {yt.get('title')}")
        print(f"     • Duración:       {yt.get('duration', 0.0):.2f}s")
        print(f"     • Archivo Local:  {yt.get('local_file')}")
    else:
        print(" [1] YOUTUBE: Error en ejecución o no completado.")

    print("-" * 80)
    if results.get("tiktok") and results["tiktok"].get("staging_data"):
        st = results["tiktok"]["staging_data"]
        v_path = Path(st.get("video_path", ""))
        m_path = Path(st.get("metadata_path", ""))
        c_path = Path(st.get("cover_path", ""))
        v_size_mb = results["tiktok"].get("file_size_mb", 0.0)
        v_dur = results["tiktok"].get("duration", 0.0)
        cost_usd = results["tiktok"].get("estimated_cost_usd", 0.0)
        broll_used = results["tiktok"].get("broll_used", "")
        print(" [2] TIKTOK (Staging Local para Subida Manual)")
        print("     • Modo:           STAGING / EXPORTACIÓN LOCAL")
        print(f"     • Ruta Vídeo MP4: {v_path.resolve() if v_path.is_file() else v_path}")
        print(f"     • Portada Cover:  {c_path.resolve() if c_path.is_file() else c_path}")
        print(f"     • Ruta Metadatos: {m_path.resolve() if m_path.is_file() else m_path}")
        print(f"     • B-Roll Usado:   {broll_used}")
        print(f"     • Peso Vídeo:     {v_size_mb:.2f} MB")
        print(f"     • Duración:       {v_dur:.2f}s (Elegible TikTok Creator Rewards: >60.5s)")
        print(f"     • Coste Estimado: ${cost_usd:.5f} USD")
    else:
        print(" [2] TIKTOK: Error o no procesado.")
    print("=" * 80 + "\n")

    return results


def run_scheduler_daemon(
    publish_time: str = "14:00",
    dry_run: bool = False,
    export_only: bool = False,
) -> None:
    """Continuous production daemon sleeping and waking at PUBLISH_TIME each day."""
    logger.info("Iniciando Silicon Verdict Scheduler Daemon...")
    logger.info("Hora de publicación diaria configurada: %s (HH:MM)", publish_time)
    logger.info("Ruta de log estructurado:              %s", BASE_DIR / "logs" / "pipeline.log")
    logger.info("Presiona Ctrl+C para detener el planificador.")

    # Initial boot cleanup of previous day videos
    purge_previous_day_videos(clean_temp=True, dry_run=dry_run)

    last_run_date: Optional[str] = None
    last_cleanup_date: Optional[str] = None

    while True:
        try:
            now = datetime.now()
            current_hhmm = now.strftime("%H:%M")
            current_date = now.strftime("%Y-%m-%d")

            # Daily midnight cleanup at 00:05
            if current_hhmm == "00:05" and last_cleanup_date != current_date:
                logger.info("Ejecutando limpieza automática de medianoche (vídeos del día anterior)...")
                purge_previous_day_videos(clean_temp=True, dry_run=dry_run)
                last_cleanup_date = current_date

            # Check if current time matches publish time and hasn't run yet today
            if current_hhmm == publish_time and last_run_date != current_date:
                # Monday to Friday (0 to 4)
                if now.weekday() in (0, 1, 2, 3, 4):
                    logger.info("Alcanzada la hora programada (%s). Ejecutando rotación semanal...", publish_time)
                    execute_daily_production(
                        weekday_index=now.weekday(),
                        dry_run=dry_run,
                        export_only=export_only,
                    )
                else:
                    logger.info("Hoy es fin de semana (%s). Omitiendo rotación de días laborales.", WEEKDAY_NAMES.get(now.weekday()))

                last_run_date = current_date

            # Sleep 20 seconds before checking again
            time.sleep(20)

        except KeyboardInterrupt:
            logger.info("Scheduler daemon detenido por el usuario.")
            break
        except Exception as exc:
            logger.error("Error imprevisto en el bucle del scheduler: %s", exc, exc_info=True)
            time.sleep(30)


def parse_args():
    parser = argparse.ArgumentParser(description="Silicon Verdict Production Scheduler & Automated Orchestrator")
    parser.add_argument(
        "--run-now",
        action="store_true",
        help="Execute today's production run immediately and exit.",
    )
    parser.add_argument(
        "--weekday",
        type=int,
        choices=[0, 1, 2, 3, 4, 5, 6],
        default=None,
        help="Override weekday index (0=Lunes, 1=Martes, 2=Miércoles, 3=Jueves, 4=Viernes).",
    )
    parser.add_argument(
        "--publish-time",
        type=str,
        default=settings.PUBLISH_TIME or "14:00",
        help="Target execution time in HH:MM format (default from .env: 14:00).",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Force TikTok local export/staging mode without attempting API upload.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate video generation and uploads without posting to YouTube or TikTok.",
    )
    parser.add_argument(
        "--privacy",
        type=str,
        default="private",
        choices=["private", "unlisted", "public"],
        help="Upload privacy status (default: private).",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Content category override (1: hardware_benchmarks, 2: gaming_benchmarks, 3: tech_curiosities, 4: auto).",
    )
    parser.add_argument(
        "--choice",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        help="Numeric selection for genera workflow (1: Hardware, 2: Gaming, 3: Tech Curiosities, 4: Auto).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    chosen_category = args.category
    if args.choice:
        from main import get_category_from_choice
        chosen_category = get_category_from_choice(args.choice)

    if args.run_now:
        logger.info("Flag --run-now detectado. Ejecutando ciclo de producción inmediato...")
        execute_daily_production(
            weekday_index=args.weekday,
            dry_run=args.dry_run,
            export_only=args.export_only,
            privacy=args.privacy,
            category=chosen_category,
        )
    else:
        run_scheduler_daemon(
            publish_time=args.publish_time,
            dry_run=args.dry_run,
            export_only=args.export_only,
        )
