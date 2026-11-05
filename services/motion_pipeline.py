"""End-to-end pipeline for series 6 (Motion Graphics): script -> render (@remotion/renderer) -> sound -> QA -> output folders -> optional YouTube upload."""
import logging
import re
import shutil
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import settings

logger = logging.getLogger(__name__)
FPS = 30


def render_motion(props: dict, out_mp4: Path) -> Path:
    """Renders the MotionGraphic composition with scripts/render_motion.mjs. Always 1080x1920 (the script refuses anything else)."""
    import json
    out_mp4 = Path(out_mp4).resolve()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    props_path = out_mp4.with_suffix(".props.json")
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    proc = subprocess.Popen(["node", str(settings.BASE_DIR / "scripts" / "render_motion.mjs"), str(props_path), str(out_mp4)], cwd=str(settings.BASE_DIR),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = []
    for line in proc.stdout:  # progress goes straight to the logs
        line = line.rstrip()
        if line.startswith("[motion]"):
            logger.info(line)
        tail.append(line)
    proc.wait()
    props_path.unlink(missing_ok=True)
    if proc.returncode != 0 or not out_mp4.is_file():
        raise RuntimeError("Motion render failed: " + " | ".join(tail[-6:])[-600:])
    return out_mp4


def add_sound(raw: Path, out: Path, scene_starts: list) -> Path:
    """Muxes a quiet ambient bed plus a soft whoosh on every scene start (both are the project's own assets), normalised to -14 LUFS."""
    from services.voice import get_ffmpeg_bin
    audio = settings.BASE_DIR / "assets" / "audio"
    ins = ["-i", str(raw), "-stream_loop", "-1", "-i", str(audio / "schematic_ambient.wav")]
    parts = ["[1:a]volume=0.22,afade=t=in:d=1.2[bed]"]
    labels = ["[bed]"]
    for n, start in enumerate(scene_starts, start=2):
        ins += ["-i", str(audio / "sfx_whoosh.wav")]
        ms = int(start / FPS * 1000)
        parts.append(f"[{n}:a]adelay={ms}|{ms},volume=0.55[w{n}]")
        labels.append(f"[w{n}]")
    parts.append("".join(labels) + f"amix=inputs={len(labels)}:duration=longest:normalize=0,loudnorm=I=-14:TP=-2:LRA=11[a]")
    cmd = [get_ffmpeg_bin(), "-y", *ins, "-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[a]", "-t", f"{_duration(raw):.2f}",
           "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-movflags", "+faststart", str(out)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return out


def _duration(path: Path) -> float:
    from services.voice import get_ffmpeg_bin
    log = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    m = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log)
    return int(m[1]) * 3600 + int(m[2]) * 60 + float(m[3]) if m else 0.0


def qa_motion(path: Path) -> list:
    """Objective checks: 1080x1920, 20-45 s, H.264, audio present, file not tiny."""
    from services.voice import get_ffmpeg_bin
    fails = []
    if not path.is_file() or path.stat().st_size < 300_000:
        return ["video file missing or suspiciously small"]
    log = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", str(path)], capture_output=True, text=True).stderr
    if "1080x1920" not in log:
        fails.append("video is not 1080x1920")
    if "h264" not in log:
        fails.append("video is not H.264")
    if "Audio:" not in log:
        fails.append("no audio track")
    d = _duration(path)
    if not 20 <= d <= 45.5:
        fails.append(f"duration {d:.1f}s outside 20-45 s")
    return fails


def run_motion_pipeline(topic: Optional[str] = None, export_only: bool = False, dry_run: bool = False, privacy: str = "public") -> Dict[str, Any]:
    from services.history import get_recently_used_topics_safe, record_short_history
    from services.motion_generator import generate_motion_project
    from services.output_layout import timestamp_stem, video_dir

    t0 = time.time()
    run_id = uuid.uuid4().hex[:8]
    project = generate_motion_project(topic, avoid_topics=get_recently_used_topics_safe())
    logger.info("Motion Graphics: '%s' (%d scenes, %.1f s)", project.title, len(project.scenes), project.total_frames / FPS)

    work = Path(settings.TMP_DIR) / f"run_motion_{run_id}"
    work.mkdir(parents=True, exist_ok=True)
    raw = render_motion(project.to_props(), work / "raw.mp4")
    starts, acc = [], 0
    for s in project.scenes:
        starts.append(acc)
        acc += s.durationInFrames
    video = add_sound(raw, work / "motion_master.mp4", starts)

    fails = qa_motion(video)
    if fails:
        logger.error("Video QA FAILED, it will not be uploaded: %s", "; ".join(fails))
    if not project.fact_checked:
        logger.warning("The script could not be fact-checked: not uploading automatically.")
    if fails or not project.fact_checked:
        export_only = True

    stem = timestamp_stem()
    out = {}
    for platform in ("youtube", "tiktok"):
        d = video_dir(platform, project.title)
        shutil.copyfile(video, d / f"{stem}.mp4")
        out[platform] = d / f"{stem}.mp4"
    tags = [t if t.startswith("#") else f"#{t}" for t in project.tags]
    meta = out["tiktok"].with_suffix(".txt")
    meta.write_text(
        "=" * 80 + "\nSILICON VERDICT • MOTION GRAPHICS • TIKTOK & SHORTS METADATA\n"
        f"Creation Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\nVideo File: {out['tiktok'].name}\nTopic: {project.topic}\n" + "=" * 80
        + f"\n\n[TITLE]\n{project.title}\n\n[DESCRIPTION]\n{project.description}\n\n[HASHTAGS]\n{' '.join(tags)}\n\n[PINNED COMMENT]\n{project.pinned_comment}\n\n[SCENES]\n"
        + "\n".join(f"- {s.type}: {s.text} {s.accentText or ''}".rstrip() for s in project.scenes) + "\n",
        encoding="utf-8",
    )

    youtube_url, yt_id = f"file://{out['youtube'].resolve()}", f"local_export_{run_id}"
    if not export_only and not dry_run:
        try:
            from services.youtube import upload_video_resumable
            youtube_url = upload_video_resumable(file_path=str(out["youtube"]), title=project.title, description=project.description, tags=project.tags, privacy_status=privacy, is_short=True)
            yt_id = youtube_url.split("/")[-1]
        except Exception as exc:
            logger.error("YouTube upload failed (%s). Video kept locally.", exc)
            yt_id = f"local_{run_id}"
    try:
        record_short_history(weekday_index=datetime.now().weekday(), theme_key="motion_graphics", game_title=project.screen_title, voice_id_used="none", topic=project.topic,
                             title=project.title, video_id=yt_id, category="MOTION GRAPHICS", tone="kinetic_typography", preset="remotion_motion")
    except Exception as exc:
        logger.warning("History not recorded: %s", exc)
    logger.info("Motion Graphics video ready in %.0fs: %s", time.time() - t0, out["tiktok"])
    return {"youtube_video": str(out["youtube"]), "youtube_url": youtube_url, "tiktok_video": str(out["tiktok"]), "tiktok_metadata": str(meta),
            "title": project.title, "topic": project.topic, "qa_failures": fails, "uploaded": not export_only and not dry_run}
