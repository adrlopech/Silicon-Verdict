#!/usr/bin/env python3
"""CLI utility to purge generated assets according to Silicon Verdict retention rules.

Usage:
  python scripts/cleanup_old_videos.py                 # Full cleanup (invoked by 'limpieza')
  python scripts/cleanup_old_videos.py --keep-tiktok   # Preserves TikTok videos (for cron/background)
  python scripts/cleanup_old_videos.py --dry-run       # Simulation mode
"""
import argparse
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.cleaner import execute_comprehensive_cleanup


def main():
    parser = argparse.ArgumentParser(
        description="Comprehensive cleanup of generated videos, frames, and render assets"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate cleanup without deleting any files.",
    )
    parser.add_argument(
        "--keep-tiktok",
        action="store_true",
        help="Preserve TikTok videos for manual upload (default: False for explicit 'limpieza').",
    )
    args = parser.parse_args()

    res = execute_comprehensive_cleanup(
        clean_tiktok=not args.keep_tiktok,
        clean_youtube=True,
        clean_frames_and_scratch=True,
        clean_temp_dirs=True,
        clean_metadata_txt=not args.keep_tiktok,
        dry_run=args.dry_run,
    )

    print("\n" + "=" * 70)
    print(" 🧹 SILICON VERDICT: REPORTE DE LIMPIEZA")
    print("=" * 70)
    print(f" Modo:                     {'SIMULACIÓN (DRY RUN)' if res['dry_run'] else 'EJECUCIÓN REAL'}")
    print(f" Vídeos Eliminados (.mp4): {len(res['deleted_videos'])}")
    for v in res['deleted_videos'][:8]:
        print(f"   • {Path(v).name}")
    if len(res['deleted_videos']) > 8:
        print(f"   ... y {len(res['deleted_videos']) - 8} vídeos más.")

    print(f" Frames / Imágenes Borradas: {len(res['deleted_frames'])}")
    print(f" Pistas de Audio Borradas:   {len(res['deleted_audio'])}")
    print(f" Carpetas de Render:         {len(res['deleted_dirs'])}")

    if res['preserved_tiktok']:
        print(f" 🛡️ Vídeos TikTok Conservados: {len(res['preserved_tiktok'])} (pendientes de subida manual)")
        for pt in res['preserved_tiktok']:
            print(f"   ✓ {Path(pt).name}")
    else:
        print(" 📲 Vídeos TikTok:           Purgados (comando limpieza ejecutado)")

    print("-" * 70)
    print(f" 💾 Espacio Total Liberado:  {res['freed_mb']:.2f} MB")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
