"""The `limpieza` cleaner: purges generated videos, covers, TikTok copies and scratch render folders.

Policy:
1. TikTok videos (output/tiktok/ and the <10 MB copies in output/tiktok_small/) are kept for the manual upload until `limpieza` is run explicitly (clean_tiktok=True).
2. output/youtube/ and the scratch files in temp/ go every time.
3. data/, assets/, .env, tokens and logs are never touched.
"""
import logging
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings

logger = logging.getLogger("silicon_verdict_cleaner")

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
AUDIO_SUFFIXES = (".mp3", ".aiff", ".wav")
SCRATCH_SUFFIXES = (".ass", ".srt", ".txt")
MB = 1024 * 1024


class _Tally:
    """What a run removed (or would remove, in a dry run) and what it kept."""

    def __init__(self, dry_run: bool):
        self.dry_run = dry_run
        self.freed = 0
        self.videos: List[str] = []
        self.frames: List[str] = []
        self.audio: List[str] = []
        self.dirs: List[str] = []
        self.meta: List[str] = []
        self.preserved: List[str] = []

    def file(self, path: Path, bucket: Optional[List[str]], label: str = "") -> None:
        """Counts one file into `bucket` (None = only the freed space) and deletes it unless this is a dry run."""
        try:
            self.freed += path.stat().st_size
            if bucket is not None:
                bucket.append(str(path))
            if not self.dry_run:
                path.unlink()
                if label:
                    logger.info("[BORRADO] %s: %s", label, path.name)
        except OSError as exc:
            logger.warning("Error eliminando %s: %s", path, exc)

    def tree(self, folder: Path, label: str) -> None:
        """Counts every file of a folder by kind and removes the folder."""
        try:
            for f in (x for x in folder.rglob("*") if x.is_file()):
                self.freed += f.stat().st_size
                bucket = self.videos if f.suffix == ".mp4" else self.frames if f.suffix in IMAGE_SUFFIXES else self.meta if f.suffix == ".txt" else None
                if bucket is not None:
                    bucket.append(str(f))
            self.dirs.append(str(folder))
            if not self.dry_run:
                shutil.rmtree(folder, ignore_errors=True)
                logger.info("[BORRADO] %s: %s", label, folder.name)
        except OSError as exc:
            logger.warning("Error eliminando carpeta %s: %s", folder, exc)


def _purge_output_dir(t: _Tally, folder: Path, label: str, with_meta: bool, delete: bool) -> None:
    """output/<platform>/: one folder per video, plus loose files of the old flat layout. With delete=False the videos are only listed as preserved."""
    if not folder.is_dir():
        return
    for item in sorted(folder.iterdir()):
        if item.name.startswith("."):
            continue
        if item.is_dir():
            if delete:
                t.tree(item, f"Carpeta de vídeo {label}")
            else:
                t.preserved.extend(str(m) for m in item.rglob("*.mp4"))
                logger.info("[PRESERVADO] Carpeta %s pendiente de subida manual: %s", label, item.name)
        elif item.suffix == ".mp4":
            if delete:
                t.file(item, t.videos, f"vídeo ({label})")
            else:
                t.preserved.append(str(item))
                logger.info("[PRESERVADO] Vídeo %s pendiente de subida manual: %s", label, item.name)
        elif delete and item.name.endswith("_cover.jpg"):
            t.file(item, t.frames, f"cover ({label})")
        elif delete and item.suffix == ".txt" and with_meta:
            t.file(item, t.meta, f"meta ({label})")


def _purge_temp_files(t: _Tally, temp_dir: Path) -> None:
    """Loose frames, clips, narration and subtitle files in temp/."""
    for suffixes, bucket in ((IMAGE_SUFFIXES, t.frames), ((".mp4",), t.videos), (AUDIO_SUFFIXES, t.audio), (SCRATCH_SUFFIXES, None)):
        for f in sorted(x for x in temp_dir.iterdir() if x.is_file() and x.suffix in suffixes):
            t.file(f, bucket)


def _purge_scratch_dirs(t: _Tally, roots: List[Path]) -> None:
    """Render work folders (run_*, test_*) in temp/ and /tmp/yt_automation/."""
    for root in roots:
        if not root.is_dir():
            continue
        for item in sorted(root.iterdir()):
            if item.is_dir() and item.name.startswith(("run_", "test_")):
                before = t.freed
                t.tree(item, "Carpeta de render")
                logger.info("(%.2f MB)", (t.freed - before) / MB)


def execute_comprehensive_cleanup(
    base_dir: Optional[Path] = None,
    clean_tiktok: bool = True,
    clean_youtube: bool = True,
    clean_frames_and_scratch: bool = True,
    clean_temp_dirs: bool = True,
    clean_metadata_txt: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Cleans generated videos, covers and render artifacts according to the policy above.

    clean_tiktok: delete output/tiktok/ and output/tiktok_small/ (only on an explicit `limpieza`); clean_youtube: output/youtube/;
    clean_frames_and_scratch: loose files in temp/; clean_temp_dirs: run_* folders; clean_metadata_txt: the .txt files in output/tiktok/; dry_run: only report.
    """
    root = Path(base_dir or settings.BASE_DIR).resolve()
    t = _Tally(dry_run)
    logger.info(">>> INICIANDO LIMPIEZA DE ARTEFACTOS SILICON VERDICT (purgar TikTok: %s, dry run: %s) <<<", clean_tiktok, dry_run)

    if clean_youtube:
        _purge_output_dir(t, root / "output" / "youtube", "YouTube", with_meta=False, delete=True)
    _purge_output_dir(t, root / "output" / "tiktok", "TikTok", with_meta=clean_metadata_txt, delete=clean_tiktok)
    _purge_output_dir(t, root / "output" / "tiktok_small", "TikTok (copia ligera)", with_meta=False, delete=clean_tiktok)
    if clean_frames_and_scratch and (root / "temp").is_dir():
        _purge_temp_files(t, root / "temp")
    if clean_temp_dirs:
        _purge_scratch_dirs(t, [root / "temp", Path("/tmp/yt_automation")])

    freed_mb = t.freed / MB
    logger.info("Limpieza finalizada: %d vídeos | %d frames | %d carpetas | liberado: %.2f MB", len(t.videos), len(t.frames), len(t.dirs), freed_mb)
    if t.preserved:
        logger.info("Vídeos de TikTok preservados para subida manual (%d): %s", len(t.preserved), ", ".join(Path(p).name for p in t.preserved))
    return {
        "status": "SUCCESS",
        "clean_tiktok": clean_tiktok,
        "deleted_videos": t.videos,
        "deleted_frames": t.frames,
        "deleted_audio": t.audio,
        "deleted_dirs": t.dirs,
        "deleted_meta": t.meta,
        "preserved_tiktok": t.preserved,
        "total_files_deleted": len(t.videos) + len(t.frames) + len(t.audio) + len(t.meta),
        "freed_bytes": t.freed,
        "freed_mb": freed_mb,
        "dry_run": dry_run,
    }
