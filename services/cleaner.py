"""Automated Video & Render Artifacts Purge Service for 'Silicon Verdict'.

Enforces the operational policy:
1. TikTok videos (output/tiktok/) are STRICTLY PRESERVED for manual upload until the user
   explicitly invokes the 'limpieza' command.
2. Background routines (scheduler, midnight cleanup) NEVER touch output/tiktok/.
3. When the user explicitly runs 'limpieza', all generated videos (including TikTok once uploaded),
   frame images, narration audio, and temporary render folders are purged immediately.
"""

import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings

logger = logging.getLogger("silicon_verdict_cleaner")


def execute_comprehensive_cleanup(
    base_dir: Optional[Path] = None,
    clean_tiktok: bool = True,
    clean_youtube: bool = True,
    clean_frames_and_scratch: bool = True,
    clean_temp_dirs: bool = True,
    clean_metadata_txt: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Cleans generated videos, frames, and render artifacts according to operational policy.

    Args:
        base_dir: Project root directory.
        clean_tiktok: Whether to delete TikTok videos in output/tiktok/. Only True on explicit 'limpieza'.
        clean_youtube: Whether to delete YouTube videos in output/youtube/.
        clean_frames_and_scratch: Whether to delete frame pngs/jpgs, audio, and subtitles in temp/.
        clean_temp_dirs: Whether to remove scratch render directories (temp/run_*, /tmp/yt_automation/*).
        clean_metadata_txt: Whether to delete accompanying .txt metadata in output/tiktok/.
        dry_run: If True, only reports what would be removed without unlinking.
    """
    root = Path(base_dir or settings.BASE_DIR).resolve()
    freed_bytes = 0

    deleted_videos: List[str] = []
    deleted_frames: List[str] = []
    deleted_audio: List[str] = []
    deleted_dirs: List[str] = []
    deleted_meta: List[str] = []
    preserved_tiktok: List[str] = []

    logger.info("================================================================================")
    logger.info(">>> INICIANDO LIMPIEZA DE ARTEFACTOS SILICON VERDICT <<<")
    logger.info("Purgar TikTok: %s (Preservado para subida manual si False) | Dry Run: %s", clean_tiktok, dry_run)
    logger.info("================================================================================")

    # 1. YouTube Output Videos & Covers
    yt_dir = root / "output" / "youtube"
    if clean_youtube and yt_dir.is_dir():
        for vid_file in yt_dir.glob("*.mp4"):
            try:
                f_size = vid_file.stat().st_size
                freed_bytes += f_size
                deleted_videos.append(str(vid_file))
                if not dry_run:
                    vid_file.unlink()
                    logger.info("[BORRADO] Vídeo YouTube: %s (%.2f MB)", vid_file.name, f_size / (1024 * 1024))
            except Exception as exc:
                logger.warning("Error eliminando vídeo YouTube %s: %s", vid_file, exc)

        for cov_file in yt_dir.glob("*_cover.jpg"):
            try:
                f_size = cov_file.stat().st_size
                freed_bytes += f_size
                deleted_frames.append(str(cov_file))
                if not dry_run:
                    cov_file.unlink()
                    logger.info("[BORRADO] Portada YouTube: %s", cov_file.name)
            except Exception as exc:
                logger.warning("Error eliminando portada YouTube %s: %s", cov_file, exc)

    # 2. TikTok Output Videos, Metadata & Covers (Protected unless clean_tiktok=True)
    tiktok_dir = root / "output" / "tiktok"
    if tiktok_dir.is_dir():
        for vid_file in tiktok_dir.glob("*.mp4"):
            if clean_tiktok:
                try:
                    f_size = vid_file.stat().st_size
                    freed_bytes += f_size
                    deleted_videos.append(str(vid_file))
                    if not dry_run:
                        vid_file.unlink()
                        logger.info("[BORRADO] Vídeo TikTok: %s (%.2f MB)", vid_file.name, f_size / (1024 * 1024))
                except Exception as exc:
                    logger.warning("Error eliminando vídeo TikTok %s: %s", vid_file, exc)
            else:
                preserved_tiktok.append(str(vid_file))
                logger.info("[PRESERVADO] Vídeo TikTok pendiente de subida manual: %s", vid_file.name)

        if clean_tiktok:
            # Purge covers in output/tiktok/
            for cov_file in tiktok_dir.glob("*_cover.jpg"):
                try:
                    f_size = cov_file.stat().st_size
                    freed_bytes += f_size
                    deleted_frames.append(str(cov_file))
                    if not dry_run:
                        cov_file.unlink()
                        logger.info("[BORRADO] Portada TikTok: %s", cov_file.name)
                except Exception as exc:
                    logger.warning("Error eliminando portada TikTok %s: %s", cov_file, exc)

            if clean_metadata_txt:
                for txt_file in tiktok_dir.glob("*.txt"):
                    try:
                        f_size = txt_file.stat().st_size
                        freed_bytes += f_size
                        deleted_meta.append(str(txt_file))
                        if not dry_run:
                            txt_file.unlink()
                            logger.info("[BORRADO] Metadatos TikTok: %s", txt_file.name)
                    except Exception as exc:
                        logger.warning("Error eliminando metadatos %s: %s", txt_file, exc)

    # 3. Frames, Audio, and Intermediate Assets in temp/
    if clean_frames_and_scratch:
        temp_dir = root / "temp"
        if temp_dir.is_dir():
            # Frame images: .png, .jpg, .jpeg
            for img_file in list(temp_dir.glob("*.png")) + list(temp_dir.glob("*.jpg")) + list(temp_dir.glob("*.jpeg")):
                try:
                    f_size = img_file.stat().st_size
                    freed_bytes += f_size
                    deleted_frames.append(str(img_file))
                    if not dry_run:
                        img_file.unlink()
                except Exception as exc:
                    logger.warning("Error eliminando frame %s: %s", img_file, exc)

            # Intermediate MP4 video clips in temp/
            for clip in temp_dir.glob("*.mp4"):
                # Always preserve test_broll in assets/
                if clip.name == "test_broll.mp4" and not (root / "assets" / "broll" / "test_broll.mp4").is_file():
                    continue
                try:
                    f_size = clip.stat().st_size
                    freed_bytes += f_size
                    deleted_videos.append(str(clip))
                    if not dry_run:
                        clip.unlink()
                except Exception as exc:
                    logger.warning("Error eliminando clip %s: %s", clip, exc)

            # Narration & audio files in temp/
            for aud in list(temp_dir.glob("*.mp3")) + list(temp_dir.glob("*.aiff")) + list(temp_dir.glob("*.wav")):
                try:
                    f_size = aud.stat().st_size
                    freed_bytes += f_size
                    deleted_audio.append(str(aud))
                    if not dry_run:
                        aud.unlink()
                except Exception as exc:
                    logger.warning("Error eliminando audio %s: %s", aud, exc)

            # Subtitles & concat files in temp/
            for sub in list(temp_dir.glob("*.ass")) + list(temp_dir.glob("*.srt")) + list(temp_dir.glob("*.txt")):
                try:
                    f_size = sub.stat().st_size
                    freed_bytes += f_size
                    if not dry_run:
                        sub.unlink()
                except Exception as exc:
                    logger.warning("Error eliminando archivo %s: %s", sub, exc)

    # 4. Scratch render folders in temp/ and /tmp/yt_automation/
    if clean_temp_dirs:
        candidate_roots = [
            root / "temp",
            Path("/tmp/yt_automation"),
        ]
        for c_root in candidate_roots:
            if not c_root.is_dir():
                continue
            for item in c_root.iterdir():
                if item.is_dir() and (item.name.startswith("run_") or item.name.startswith("test_")):
                    try:
                        dir_size = sum(f.stat().st_size for f in item.glob("**/*") if f.is_file())
                        freed_bytes += dir_size
                        deleted_dirs.append(str(item))
                        if not dry_run:
                            shutil.rmtree(item, ignore_errors=True)
                            logger.info("[BORRADO] Carpeta de render: %s (%.2f MB)", item.name, dir_size / (1024 * 1024))
                    except Exception as exc:
                        logger.warning("Error eliminando directorio %s: %s", item, exc)

    freed_mb = freed_bytes / (1024 * 1024)
    logger.info("--------------------------------------------------------------------------------")
    logger.info(
        "Limpieza finalizada: %d vídeos borrados | %d frames borrados | %d dirs purgados | Liberado: %.2f MB",
        len(deleted_videos),
        len(deleted_frames),
        len(deleted_dirs),
        freed_mb,
    )
    if preserved_tiktok:
        logger.info("Vídeos de TikTok preservados para subida manual (%d): %s", len(preserved_tiktok), ", ".join(Path(p).name for p in preserved_tiktok))
    logger.info("================================================================================")

    return {
        "status": "SUCCESS",
        "clean_tiktok": clean_tiktok,
        "deleted_videos": deleted_videos,
        "deleted_frames": deleted_frames,
        "deleted_audio": deleted_audio,
        "deleted_dirs": deleted_dirs,
        "deleted_meta": deleted_meta,
        "preserved_tiktok": preserved_tiktok,
        "total_files_deleted": len(deleted_videos) + len(deleted_frames) + len(deleted_audio) + len(deleted_meta),
        "freed_bytes": freed_bytes,
        "freed_mb": freed_mb,
        "dry_run": dry_run,
    }


def purge_previous_day_videos(
    base_dir: Optional[Path] = None,
    retention_hours: float = 24.0,
    clean_temp: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Routine background cleanup: NEVER touches TikTok videos (reserved for manual upload)."""
    return execute_comprehensive_cleanup(
        base_dir=base_dir,
        clean_tiktok=False,  # ALWAYS False for automatic/background routines!
        clean_youtube=True,
        clean_frames_and_scratch=True,
        clean_temp_dirs=clean_temp,
        clean_metadata_txt=False,
        dry_run=dry_run,
    )
