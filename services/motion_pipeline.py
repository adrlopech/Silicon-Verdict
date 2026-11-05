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
MIN_VIDEO_SECONDS = 62.0  # final length floor (YouTube monetisation: more than 60 s)
VOICE_LEAD = 0.2  # seconds after a scene starts before the narrator speaks (the text lands first)


def render_motion(props: dict, out_mp4: Path, public_dir: Optional[Path] = None) -> Path:
    """Renders the MotionGraphic composition with scripts/render_motion.mjs. Always 1080x1920 (the script refuses anything else)."""
    import json
    out_mp4 = Path(out_mp4).resolve()
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    props_path = out_mp4.with_suffix(".props.json")
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    cmd = ["node", str(settings.BASE_DIR / "scripts" / "render_motion.mjs"), str(props_path), str(out_mp4)] + ([str(public_dir)] if public_dir else [])
    proc = subprocess.Popen(cmd, cwd=str(settings.BASE_DIR),
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


def narrate_scenes(project: Any, work_dir: Path) -> list:
    """ElevenLabs narration, one clip per scene (parallel). Each scene is stretched to fit its line. Returns [(scene_index, mp3, seconds)]."""
    import math
    from concurrent.futures import ThreadPoolExecutor
    from services import voice_synthesizer
    from services.voice_synthesizer import synthesize_voice_with_timestamps
    work_dir.mkdir(parents=True, exist_ok=True)

    def one(i: int):
        path, dur, _ = synthesize_voice_with_timestamps(
            project.scenes[i].narration, work_dir / f"scene_{i:02d}.mp3", voice_id=settings.ELEVENLABS_VOICE_3, model_id="eleven_multilingual_v2",
            natural=True, min_duration=None, max_duration=None, stability=0.32, style=0.5)
        return i, path, dur

    clips = []
    for workers in (2, 1):  # ElevenLabs limits concurrent requests: a failed pass is retried one line at a time before giving up
        before = voice_synthesizer.FALLBACK_COUNT
        with ThreadPoolExecutor(max_workers=workers) as pool:
            clips = list(pool.map(one, range(len(project.scenes))))
        if voice_synthesizer.FALLBACK_COUNT == before:
            break
        logger.warning("ElevenLabs failed for some lines with %d worker(s); retrying slower...", workers)
        time.sleep(6)
    else:
        raise RuntimeError("ElevenLabs failed for some lines (a robotic local voice would have been used): not producing this video")
    for i, _p, dur in clips:  # the scene lasts at least as long as its narration (+ a short breath), never less than its own minimum
        project.scenes[i].durationInFrames = max(project.scenes[i].durationInFrames, math.ceil((dur + VOICE_LEAD + 0.45) * FPS))
    if project.total_frames > 88 * FPS:
        raise RuntimeError(f"narrated video would last {project.total_frames / FPS:.1f}s (> 88 s); script too long")
    deficit = int(MIN_VIDEO_SECONDS * FPS) - project.total_frames  # YouTube monetisation needs MORE than 60 s: hold scenes a little longer if short
    if deficit > 0:
        per = math.ceil(deficit / len(project.scenes))
        for sc in project.scenes:
            sc.durationInFrames += per
        logger.info("Narrated video was %.1f s: scenes held %.2f s longer each to pass %.0f s.", (project.total_frames - per * len(project.scenes)) / FPS, per / FPS, MIN_VIDEO_SECONDS)
    logger.info("Narration ready: %d lines, %.1f s of speech, video %.1f s", len(clips), sum(c[2] for c in clips), project.total_frames / FPS)
    return clips


def add_sound(raw: Path, out: Path, scene_starts: list, voice_clips: Optional[list] = None) -> Path:
    """Muxes a quiet ambient bed plus a soft whoosh on every scene start (both are the project's own assets), normalised to -14 LUFS."""
    from services.voice import get_ffmpeg_bin
    audio = settings.BASE_DIR / "assets" / "audio"
    ins = ["-i", str(raw), "-stream_loop", "-1", "-i", str(audio / "schematic_ambient.wav")]
    voiced = bool(voice_clips)
    parts = [f"[1:a]volume={0.12 if voiced else 0.22},afade=t=in:d=1.2[bed]"]
    labels = ["[bed]"]
    n = 2
    for start in scene_starts:
        ins += ["-i", str(audio / "sfx_whoosh.wav")]
        ms = int(start / FPS * 1000)
        parts.append(f"[{n}:a]adelay={ms}|{ms},volume={0.3 if voiced else 0.55}[w{n}]")
        labels.append(f"[w{n}]")
        n += 1
    for idx, clip, _d in voice_clips or []:
        ins += ["-i", str(clip)]
        ms = int((scene_starts[idx] / FPS + VOICE_LEAD) * 1000)
        parts.append(f"[{n}:a]adelay={ms}|{ms},volume=1.6[v{n}]")
        labels.append(f"[v{n}]")
        n += 1
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
    """Objective checks: 1080x1920, 61-90 s, H.264, audio present and audible, file not tiny."""
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
    vol = subprocess.run([get_ffmpeg_bin(), "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    mean = re.search(r"mean_volume: (-?[\d.]+) dB", vol)
    if mean and float(mean[1]) < -28:
        fails.append(f"audio mean {mean[1]} dB is too quiet: the narration seems to be missing")
    d = _duration(path)
    if not 61 <= d <= 92:
        fails.append(f"duration {d:.1f}s outside 61-92 s (YouTube monetisation needs more than 60 s)")
    return fails


def run_motion_pipeline(topic: Optional[str] = None, export_only: bool = False, dry_run: bool = False, privacy: str = "public", kind: str = "auto") -> Dict[str, Any]:
    """kind: curiosity | game | auto (a game video when a game with unused footage is not blacklisted, otherwise a curiosity)."""
    from services.history import get_recently_used_topics_safe, record_short_history
    from services.motion_generator import generate_motion_project
    from services.output_layout import timestamp_stem, video_dir

    t0 = time.time()
    run_id = uuid.uuid4().hex[:8]
    import random
    from services.game_images import build_credits, commit_media, footage_catalog, stage_media

    from services.game_facts import get_game_facts
    from services.game_images import available_games

    facts = None
    game = None
    if kind in ("game", "auto"):
        candidates = available_games()
        random.shuffle(candidates)
        if candidates:
            game = candidates[0]
            facts = get_game_facts(game)  # paced + cached; None only when no source text exists at all -> the script is then written conservatively (no figures)
            if not facts:
                logger.warning("No source text for %s: writing the game video in conservative mode (no figures, only well-known facts).", game)
    if kind == "auto" and game and random.random() < 0.5:
        game, facts = None, None  # alternate between game videos and curiosities
    if kind == "game" and not game:
        raise RuntimeError("No game is available: every game with stocked footage was covered in the last 14 days, ran out of unused footage or has no source text "
                           "(fetch more: scripts/fetch_game_images.py, scripts/fetch_game_clips.py, scripts/caption_game_media.py; blacklist: python -m services.game_registry).")
    catalog = footage_catalog(game) if game else None
    project = generate_motion_project(topic, avoid_topics=get_recently_used_topics_safe(), kind="game" if game else "curiosity", game=game, catalog=catalog, facts=facts)
    logger.info("Motion Graphics (%s%s): '%s' (%d scenes)", project.kind, f", {game}" if game else "", project.title, len(project.scenes))

    work = Path(settings.TMP_DIR) / f"run_motion_{run_id}"
    work.mkdir(parents=True, exist_ok=True)
    public = work / "public"
    public.mkdir(exist_ok=True)
    used_entries = []
    for sc in project.scenes:  # footage scenes get their (already chosen) item copied into the render's own public dir
        if sc.type == "footage" and catalog and sc.mediaId in catalog:
            entry = catalog[sc.mediaId]
            sc.mediaSrc, sc.mediaKind, sc.mediaSeconds = stage_media(entry, public), entry["kind"], float(entry.get("seconds", 3.0))
            sc.credit = entry["game"]
            used_entries.append(entry)
    if used_entries:
        project.description = project.description.rstrip() + "\n\nGame footage: " + "; ".join(build_credits(used_entries)) + " (official Steam store media)."
    clips = narrate_scenes(project, work / "voice")  # first: the narration decides how long each scene lasts
    raw = render_motion(project.to_props(), work / "raw.mp4", public)
    starts, acc = [], 0
    for sc in project.scenes:
        starts.append(acc)
        acc += sc.durationInFrames
    video = add_sound(raw, work / "motion_master.mp4", starts, clips)

    fails = qa_motion(video)
    if fails:
        logger.error("Video QA FAILED, it will not be uploaded: %s", "; ".join(fails))
    if not project.fact_checked:
        logger.warning("No reviewer could fact-check the script: publishing anyway (the script was still grounded and validated).")
    if fails:
        export_only = True  # only an objective technical failure of the video itself holds it back
    if used_entries and not fails:  # the footage is spent only when a finished, checked video exists: delete it, never reuse it, blacklist the game 14 days
        commit_media([e["key"] for e in used_entries], game, project.title)

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
    return {"kind": project.kind, "game": project.game, "youtube_video": str(out["youtube"]), "youtube_url": youtube_url, "tiktok_video": str(out["tiktok"]), "tiktok_metadata": str(meta),
            "title": project.title, "topic": project.topic, "qa_failures": fails, "uploaded": not export_only and not dry_run}
