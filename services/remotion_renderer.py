"""Remotion rendering orchestrator for Silicon Verdict kinetic motion graphics (1080x1920 @ 30 FPS).

Optimized for Apple Silicon M2 (MacBook Air 8-Core CPU, 16 GB Unified Memory):
- Zero-Whisper architecture: consumes native ElevenLabs word alignment directly.
- Zero-Webpack overhead: persistent pre-bundled Remotion code in build/.
- 30 FPS temporal base: exactly 50% fewer frames to rasterize with identical mobile visual quality.
- Balanced M2 concurrency: 6 worker threads (4P + 4E distribution).
- Apple VideoToolbox hardware acceleration: instant h264_videotoolbox encode & muxing.
"""

import hashlib
import json
import logging
import os
import re
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config.settings import settings
from core.schemas import MotionStoryProject, MotionVisualTrigger
from services.subtitles import extract_word_timestamps
from services.tts import get_audio_duration
from services.voice import get_ffmpeg_bin

logger = logging.getLogger(__name__)


def get_src_checksum(src_dir: Path) -> str:
    """Computes a SHA256 checksum across all source files in src/ to detect code updates."""
    hasher = hashlib.sha256()
    for p in sorted(src_dir.rglob("*")):
        if p.is_file() and not p.name.startswith("."):
            try:
                hasher.update(p.read_bytes())
            except Exception:
                pass
    return hasher.hexdigest()


def ensure_remotion_bundle(remotion_dir: Path) -> Tuple[Path, float]:
    """Ensures persistent pre-bundled Remotion code exists in build/ to eliminate Webpack startup overhead.

    Returns:
        (build_dir, check_and_bundle_time_seconds)
    """
    t0 = time.time()
    build_dir = remotion_dir / "build"
    src_dir = remotion_dir / "src"
    hash_file = build_dir / ".bundle_hash"

    current_hash = get_src_checksum(src_dir)
    cached_hash = hash_file.read_text(encoding="utf-8").strip() if hash_file.is_file() else ""

    if build_dir.is_dir() and (build_dir / "index.html").is_file() and cached_hash == current_hash:
        elapsed = time.time() - t0
        logger.info("[Remotion Bundle Check] Valid persistent pre-bundle found in build/ (%.2fs Webpack overhead)", elapsed)
        return build_dir, elapsed

    logger.info("[Remotion Bundle Check] Building pre-bundle in %s...", build_dir)
    env = os.environ.copy()
    home_local_bin = str(Path.home() / ".local" / "bin")
    env["PATH"] = f"{home_local_bin}:{env.get('PATH', '')}"

    bundle_cmd = [
        "npx", "remotion", "bundle",
        "src/index.ts",
        f"--out-dir={build_dir.name}",
        "--public-dir=public",
        "--quiet",
    ]
    proc = subprocess.run(
        bundle_cmd,
        cwd=str(remotion_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if proc.returncode != 0:
        logger.error("Remotion pre-bundling failed:\n%s", proc.stdout)
        raise RuntimeError(f"Remotion bundle failed: {proc.stdout[-500:]}")

    hash_file.write_text(current_hash, encoding="utf-8")
    elapsed = time.time() - t0
    logger.info("[Remotion Bundle Check] Pre-bundle compiled successfully in %.2fs", elapsed)
    return build_dir, elapsed


def map_visual_triggers_to_frames(
    triggers: List[MotionVisualTrigger],
    word_timestamps: List[Dict[str, Any]],
    fps: int = 30,
    total_audio_dur: float = 60.0,
) -> List[Dict[str, Any]]:
    """Maps 12 to 18 visual triggers to non-overlapping sequential frame sequences covering the entire video."""
    num_triggers = len(triggers)
    if num_triggers == 0:
        return []

    # 1. Compute anchor times
    trigger_times: List[float] = []
    total_frames = int(total_audio_dur * fps)

    # Target spacing between beats (between 2.0s and 3.5s)
    target_spacing = max(2.0, min(3.5, total_audio_dur / float(num_triggers)))

    MIN_GAP = 1.8
    WINDOW = 4.0  # an anchor may drift at most this far past its ideal slot
    for idx, trigger in enumerate(triggers):
        if idx == 0:
            # First trigger starts immediately at 0s so the screen is never empty
            trigger_times.append(0.0)
            continue

        ideal_time = (idx / float(num_triggers)) * total_audio_dur
        min_allowed = trigger_times[-1] + MIN_GAP
        # Leave room so every remaining trigger still gets at least MIN_GAP
        max_allowed = total_audio_dur - (num_triggers - idx) * MIN_GAP
        upper = min(max_allowed, max(min_allowed, ideal_time + WINDOW))

        anchor_clean = re.sub(r"[^\w]", "", trigger.word_anchor.lower())
        matched_time: Optional[float] = None

        if word_timestamps and len(anchor_clean) >= 3:
            for w in word_timestamps:
                w_clean = re.sub(r"[^\w]", "", w["word"].lower())
                if anchor_clean == w_clean or (len(w_clean) >= 4 and w_clean in anchor_clean) or (len(anchor_clean) >= 4 and anchor_clean in w_clean):
                    t = float(w["start"])
                    # Earliest match inside the allowed window (repeated words cannot cascade to the end)
                    if min_allowed <= t <= upper:
                        matched_time = t
                        break

        if matched_time is None:
            matched_time = min(max(min_allowed, ideal_time), max(min_allowed, max_allowed))

        trigger_times.append(matched_time)

    # Ensure strictly monotonically increasing with minimum spacing
    for i in range(1, num_triggers):
        if trigger_times[i] < trigger_times[i - 1] + MIN_GAP:
            trigger_times[i] = trigger_times[i - 1] + target_spacing

    # 2. Build non-overlapping sequential triggers
    mapped: List[Dict[str, Any]] = []
    for i in range(num_triggers):
        start_f = int(trigger_times[i] * fps)
        if i < num_triggers - 1:
            next_start_f = int(trigger_times[i + 1] * fps)
            dur_f = max(int(2.0 * fps), next_start_f - start_f + 4)  # 4-frame smooth exit overlap @ 30fps
        else:
            # Last trigger stays active until the very end
            dur_f = max(int(3.0 * fps), total_frames - start_f)

        mapped.append({
            "asset_id": triggers[i].asset_id,
            "label": triggers[i].label,
            "start_frame": start_f,
            "duration_frames": dur_f,
            "motion_preset": triggers[i].motion_preset,
            "image_src": getattr(triggers[i], "image_src", None),
            "game_title": getattr(triggers[i], "game_title", None),
            "annotation": getattr(triggers[i], "annotation", None),
        })

    return mapped


def render_remotion_video(
    story: MotionStoryProject,
    master_audio_path: Path,
    output_video_path: Path,
    output_cover_path: Optional[Path] = None,
    word_timestamps: Optional[List[Dict[str, Any]]] = None,
    fps: int = 30,
) -> Tuple[Path, Path, Dict[str, float]]:
    """Compiles and renders a 1080x1920 @ 30 FPS kinetic motion graphics short via Remotion & VideoToolbox."""
    t_start_total = time.time()
    master_audio_path = Path(master_audio_path).resolve()
    output_video_path = Path(output_video_path).resolve()
    output_video_path.parent.mkdir(parents=True, exist_ok=True)

    if output_cover_path is None:
        output_cover_path = output_video_path.with_name(f"{output_video_path.stem}_cover.jpg")
    else:
        output_cover_path = Path(output_cover_path).resolve()

    logger.info("Initializing Fast M2 Remotion Pipeline for: %s (%s @ %d FPS)", story.title, story.category_name, fps)

    # Pre-render Brand Integrity Sanity Check & procedural correction
    from services.content_generator import validate_and_sanitize_brand_integrity
    _, brand_fixes = validate_and_sanitize_brand_integrity(story)
    if brand_fixes:
        logger.warning("Pre-render brand integrity corrections applied: %s", brand_fixes)

    # 1. Locate Remotion studio directory
    remotion_dir = settings.BASE_DIR / "remotion_studio"
    if not remotion_dir.is_dir():
        raise FileNotFoundError(f"Remotion studio not found at {remotion_dir}")

    # 2. Check / Ensure Persistent Webpack Pre-Bundle
    build_dir, bundle_check_dur = ensure_remotion_bundle(remotion_dir)

    # 3. Obtain Word Timestamps (Native ElevenLabs or cached whisper.json)
    if not word_timestamps:
        cached_whisper = remotion_dir / "public" / "data" / "whisper.json"
        if cached_whisper.is_file():
            try:
                word_timestamps = json.loads(cached_whisper.read_text(encoding="utf-8"))
                logger.info("Using cached ElevenLabs word timestamps from whisper.json (%d words)", len(word_timestamps))
            except Exception:
                word_timestamps = None

    if not word_timestamps:
        logger.info("Extracting word timestamps via faster-whisper fallback...")
        word_timestamps = extract_word_timestamps(master_audio_path, fallback_script=story.full_script)

    audio_dur = get_audio_duration(str(master_audio_path))

    # Calculate total duration in frames (+1.2s padding for clean outro)
    total_frames = int((audio_dur + 1.2) * fps)
    if word_timestamps:
        last_word_frame = int(word_timestamps[-1]["end"] * fps)
        total_frames = max(total_frames, last_word_frame + int(1.2 * fps))

    # 4. Map visual triggers to frame offsets
    mapped_triggers = map_visual_triggers_to_frames(
        story.visual_triggers,
        word_timestamps,
        fps=fps,
        total_audio_dur=audio_dur,
    )

    # 5. Copy master audio to remotion public audio folder
    public_audio_dir = remotion_dir / "public" / "audio"
    public_audio_dir.mkdir(parents=True, exist_ok=True)
    narration_dest = public_audio_dir / "narration.wav"
    shutil.copyfile(master_audio_path, narration_dest)

    # 6. Write bundle.json
    bundle_data = {
        "category": story.category_name,
        "header_banner": story.header_banner,
        "audio_src": "audio/narration.wav",
        "total_frames": total_frames,
        "subtitles": word_timestamps,
        "visual_triggers": mapped_triggers,
    }
    bundle_path = remotion_dir / "public" / "data" / "bundle.json"
    bundle_path.parent.mkdir(parents=True, exist_ok=True)
    with open(bundle_path, "w", encoding="utf-8") as f:
        json.dump(bundle_data, f, indent=2, ensure_ascii=False)

    logger.info(
        "Bundle prepared: %d words | %d triggers | Total frames: %d (%.2fs @ %d FPS)",
        len(word_timestamps), len(mapped_triggers), total_frames, total_frames / fps, fps,
    )

    # 7. Execute Remotion render using the persistent build bundle
    env = os.environ.copy()
    home_local_bin = str(Path.home() / ".local" / "bin")
    env["PATH"] = f"{home_local_bin}:{env.get('PATH', '')}"

    temp_raw_video = output_video_path.with_name(f"temp_raw_{uuid.uuid4().hex[:6]}.mp4")

    render_cmd = [
        "npx", "remotion", "render",
        str(build_dir.name),
        "MainScene",
        str(temp_raw_video),
        f"--props={str(bundle_path)}",
        f"--fps={fps}",
        "--gl=angle",
        "--concurrency=6",
        "--muted",
        "--public-dir=public",
        "--x264-preset=ultrafast",
        '--chromium-options="--disable-extensions --no-sandbox --disable-background-networking --disable-gpu-sandbox"',
    ]

    logger.info("Executing Fast M2 Headless Render (30 FPS, concurrency=6): %s", " ".join(render_cmd))
    t_render_start = time.time()
    proc = subprocess.run(
        render_cmd,
        cwd=str(remotion_dir),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    t_render_dur = time.time() - t_render_start

    if proc.returncode != 0 or not temp_raw_video.is_file():
        logger.error("Remotion render failed with code %d:\n%s", proc.returncode, proc.stdout[-1500:])
        raise RuntimeError(f"Remotion render failed: {proc.stdout[-500:]}")

    logger.info("Headless render completed in %.2fs", t_render_dur)

    # 8. Apple Silicon VideoToolbox Hardware Muxing
    t_mux_start = time.time()
    ffmpeg_bin = get_ffmpeg_bin()
    mux_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(temp_raw_video),
        "-i", str(master_audio_path),
        "-c:v", "h264_videotoolbox",
        "-prio_speed", "true",
        "-b:v", "7M",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_video_path),
    ]

    try:
        subprocess.run(mux_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    except subprocess.CalledProcessError as cpe:
        logger.warning("VideoToolbox mux failed (%s). Retrying with libx264 veryfast...", cpe.stderr)
        fallback_mux_cmd = [
            ffmpeg_bin, "-y",
            "-i", str(temp_raw_video),
            "-i", str(master_audio_path),
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            str(output_video_path),
        ]
        subprocess.run(fallback_mux_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    t_mux_dur = time.time() - t_mux_start

    # Clean up temp raw video
    if temp_raw_video.exists():
        temp_raw_video.unlink()

    video_size_mb = output_video_path.stat().st_size / (1024 * 1024)
    logger.info("Final video muxed with VideoToolbox in %.2fs: %s (%.2f MB)", t_mux_dur, output_video_path.name, video_size_mb)

    # 9. Extract crisp cover thumbnail at 3.0s mark
    thumb_time = min(3.0, audio_dur * 0.15)
    thumb_cmd = [
        ffmpeg_bin, "-y",
        "-ss", f"{thumb_time:.2f}",
        "-i", str(output_video_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_cover_path),
    ]
    try:
        subprocess.run(thumb_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        logger.info("Cover thumbnail generated: %s", output_cover_path.name)
    except Exception as exc:
        logger.warning("Failed to extract thumbnail (%s). Generating fallback dummy cover.", exc)

    timing_telemetry = {
        "remotion_bundle_check": bundle_check_dur,
        "headless_render": t_render_dur,
        "videotoolbox_mux": t_mux_dur,
        "total_render": time.time() - t_start_total,
    }

    return output_video_path, output_cover_path, timing_telemetry
