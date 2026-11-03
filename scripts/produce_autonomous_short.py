#!/usr/bin/env python3
"""Autonomous End-to-End YouTube Short Production Engine for 'Silicon Verdict'.

Executes a complete 100% autonomous cycle:
1. Topic & Script Discovery (Gemini): Selects an unexploited high-impact PC hardware debate.
2. Voice Narration & Audio Mixing (ElevenLabs): Synthesizes voice, normalizes to -14 LUFS,
   and mixes atmospheric dark tech synth music at -22 dB.
3. Kinetic Subtitles (faster-whisper): Word-by-word synchronized captions conforming strictly
   to YouTube Shorts Safe Zone (2-3 words/screen, MarginV: 520, Neon Cyan active word).
4. Visual Engine (Apple Liquid Glass & Pixabay B-roll):
   - Scene 1 (Hook): Pixabay B-roll with Apple Vision Pro HUD glass pill overlay in upper third.
   - Scene 2 (Benchmark): 1080x1920 60 FPS animated Apple Liquid Glass benchmark chart with live bar growth.
   - Scene 3 (Verdict): Pixabay B-roll with definitive verdict HUD pill overlay.
5. Final Assembly & YouTube Upload: Concatenates clips, burns ASS subtitles, and uploads
   with privacyStatus = 'private' to YouTube.
"""
import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure venv bin (where static ffmpeg/ffprobe live) is in PATH
venv_bin = BASE_DIR / ".venv" / "bin"
if venv_bin.is_dir() and str(venv_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

from google import genai
from google.genai import types

from config.settings import settings
from core.generator import DailyShortSpec, select_daily_short_spec
from core.schemas import ChartData, MarketTopic
from core.topic_engine import load_history, record_topic_in_history
from engine.charts import (
    generate_glass_whoosh_sfx,
    render_animated_benchmark_video,
    render_animated_cta_video,
)
from engine.renderer import create_introductory_dilemma_card, create_vision_pro_hud_pill
from services.history import record_short_history
from services.media import search_and_download_pixabay_video
from services.subtitles import generate_kinetic_subtitles
from services.tts import get_audio_duration, resolve_active_voice_id
from services.youtube import upload_video_resumable

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("silicon_verdict_short")


# ==============================================================================
# PHASE 1: AUTONOMOUS TOPIC & SCRIPT GENERATION (GEMINI)
# ==============================================================================
def generate_autonomous_short_plan(
    client: genai.Client,
    history_path: Path,
    topic_override: Optional[str] = None,
    spec: Optional[DailyShortSpec] = None,
) -> Dict:
    """Generates an empirical, data-driven hardware debate script for a 35-45s Short."""
    history = load_history(history_path)
    previous_topics = [h.get("topic") for h in history]

    logger.info("Querying Gemini for autonomous PC hardware debate & telemetry data...")

    if topic_override:
        topic_instruction = f"Target Topic: '{topic_override}'"
    elif spec:
        topic_instruction = (
            f"Daily Pillar: {spec.day_name} ({spec.pillar_title})\n"
            f"Required Subtheme ({spec.theme_key}): '{spec.theme_description}'\n"
            f"Mandatory Benchmark Game: '{spec.game_title}'\n"
            "Build the debate and empirical benchmark directly around this hardware pillar, subtheme, and game."
        )
    else:
        topic_instruction = "Select a fresh, unexploited, high-impact PC hardware debate for enthusiasts."

    prompt = f"""You are the Lead Hardware Telemetry Engineer & Content Director for 'Silicon Verdict', an elite YouTube channel known for empirical PC hardware benchmarks.
Generate a complete specification for an autonomous 35-45 second YouTube Short.
Previously covered topics: {previous_topics}
{topic_instruction}

Debate candidates:
- 128-bit vs 256-bit memory bus bandwidth choking high-res textures at 1440p
- PCIe 4.0 x8 vs x16 link width penalties on PCIe 3.0 platforms
- GDDR6 vs GDDR6X power draw and thermal throttling on memory controllers

Return a strictly valid JSON object conforming exactly to this structure:
{{
  "topic": "string (Concise topic name)",
  "title": "string (High-CTR title under 75 chars, ending with #Shorts)",
  "description": "string (Technical summary, frame pacing methodology, PresentMon telemetry notes, #Shorts #SiliconVerdict #PCGaming)",
  "tags": ["string", "string", ... at least 15 technical tags],
  "pinned_comment": "string (Insightful technical debate prompt)",
  "scene1": {{
    "voiceover": "string (~18-22 words, aggressive hook in the first 3 seconds challenging conventional wisdom)",
    "dilemma_title": "string (uppercase, 2-4 words, e.g. '128-BIT vs 256-BIT BUS')",
    "dilemma_subtitle": "string (concise technical dilemma, e.g. 'Does narrow bus bandwidth choke 1440p textures?')",
    "category_pill": "string (uppercase, 2-3 words, e.g. 'BANDWIDTH BOTTLENECK')",
    "hud_text": "string (uppercase, 2-3 words, e.g. 'MEMORY BANDWIDTH')",
    "pixabay_query": "string (approved query, e.g. 'gaming pc benchmark gameplay' or 'semiconductor silicon wafer macro')"
  }},
  "scene2": {{
    "voiceover": "string (~35-42 words, empirical comparison citing exact numerical FPS and percentage delta)",
    "chart_title": "string (uppercase, e.g. '1440p ULTRA TELEMETRY')",
    "chart_subtitle": "string (e.g. '256-bit Bus vs 128-bit Bus')",
    "preset_pill": "string (uppercase, e.g. '1440p ULTRA • CYBERPUNK 2077')",
    "metric_unit": "FPS",
    "winner_label": "string (e.g. '256-bit Bus (576 GB/s)')",
    "winner_fps": 94.0,
    "loser_label": "string (e.g. '128-bit Bus (288 GB/s)')",
    "loser_fps": 61.0,
    "winner_badge": "string (e.g. '+54% FASTER')"
  }},
  "scene_cta": {{
    "voiceover": "string (STRICTLY 10-14 words, 2.5-3.0s duration, e.g. 'If you are enjoying this breakdown and want daily hardware insights, subscribe to Silicon Verdict.')",
    "headline_highlight": "SUBSCRIBE",
    "headline_rest": "FOR DAILY VERDICTS",
    "sub_text": "Unfiltered PC Hardware Telemetry & Benchmarks"
  }},
  "scene3": {{
    "voiceover": "string (~18-22 words, definitive technical verdict and recommendation for PC builders)",
    "hud_text": "string (uppercase, 2-3 words, e.g. 'SILICON VERDICT')",
    "pixabay_query": "string (approved query, e.g. 'cinematic cpu die silicon' or 'pc gaming graphics 4k')"
  }}
}}"""

    response = None
    candidate_models = ["gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite", settings.GEMINI_MODEL]
    last_err = None

    for model_name in candidate_models:
        for attempt in range(1, 3):
            try:
                logger.info("Requesting Gemini short script using model '%s' (attempt %d)...", model_name, attempt)
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.7,
                    ),
                )
                break
            except Exception as exc:
                last_err = exc
                if "503" in str(exc) or "UNAVAILABLE" in str(exc) or "demand" in str(exc):
                    logger.warning("Model '%s' hit 503 high demand spike. Trying next candidate...", model_name)
                    time.sleep(1)
                    break
                else:
                    time.sleep(1)
        if response is not None:
            break

    if response is None:
        raise RuntimeError(f"All Gemini candidate models failed. Last error: {last_err}")

    data = json.loads(response.text)
    if "scene_cta" not in data or not isinstance(data["scene_cta"], dict) or not data["scene_cta"].get("voiceover"):
        data["scene_cta"] = {
            "voiceover": "If you are enjoying this breakdown and want daily hardware insights, subscribe to Silicon Verdict.",
            "headline_highlight": "SUBSCRIBE",
            "headline_rest": "FOR DAILY VERDICTS",
            "sub_text": "Unfiltered PC Hardware Telemetry & Benchmarks",
        }
    logger.info("Autonomous Topic Selected: '%s'", data.get("topic"))
    logger.info("Short Title: '%s'", data.get("title"))
    return data


# ==============================================================================
# PHASE 2: VOICE SYNTHESIS, NORMALIZATION & AUDIO MIXING
# ==============================================================================
def synthesize_elevenlabs_narration(text: str, output_path: Path, voice_id: Optional[str] = None) -> float:
    """Synthesizes voiceover text via ElevenLabs API and measures duration."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target_voice = resolve_active_voice_id(target_voice=voice_id)
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{target_voice}"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    payload = {
        "text": text,
        "model_id": settings.ELEVENLABS_MODEL_ID,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.8,
            "style": 0.1,
            "use_speaker_boost": True,
        },
    }

    logger.info("Synthesizing voiceover via ElevenLabs (Words: %d)...", len(text.split()))
    res = requests.post(url, headers=headers, json=payload, timeout=60)
    if res.status_code != 200:
        raise RuntimeError(f"ElevenLabs API error ({res.status_code}): {res.text}")

    with open(output_path, "wb") as f:
        f.write(res.content)

    duration = get_audio_duration(str(output_path))
    logger.info("Voiceover ready: %s (Duration: %.2fs)", output_path.name, duration)
    return duration


def generate_dark_tech_synth_music(output_path: Path, duration_sec: float) -> Path:
    """Generates an atmospheric dark tech synth ambient backing track via FFmpeg audio synthesis."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Generating %.1fs atmospheric dark tech synth backing track...", duration_sec)

    filter_graph = (
        f"anoisesrc=c=pink:r=44100:a=0.015,lowpass=f=200[noise];"
        f"sine=f=55:r=44100:d={duration_sec:.2f}[sub];"
        f"sine=f=110:r=44100:d={duration_sec:.2f}[mid];"
        f"[sub][mid]amix=inputs=2:dropout_transition=2[syn];"
        f"[syn]volume=0.07,chorus=0.7:0.9:55:0.4:0.25:2[pad];"
        f"[noise][pad]amix=inputs=2:dropout_transition=2,volume=0.15[out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", filter_graph,
        "-t", f"{duration_sec:.2f}",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(output_path),
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return output_path


def create_mixed_audio_master(
    voice_files: List[Path],
    output_master_audio: Path,
    temp_dir: Path,
) -> float:
    """Concatenates scene voice files, normalizes to -14 LUFS, and mixes background synth music at -22 dB."""
    output_master_audio.parent.mkdir(parents=True, exist_ok=True)

    # 1. Concat Voice Tracks
    concat_list = temp_dir / "voice_concat.txt"
    with open(concat_list, "w", encoding="utf-8") as f:
        for vf in voice_files:
            f.write(f"file '{vf.resolve()}'\n")

    voice_raw = temp_dir / "voice_raw.mp3"
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(voice_raw)],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    # 2. Voice Normalization to -14 LUFS
    voice_norm = temp_dir / "voice_norm_14lufs.mp3"
    logger.info("Normalizing voice narration to broadcast standard -14 LUFS...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(voice_raw),
            "-filter:a", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(voice_norm),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    total_duration = get_audio_duration(str(voice_norm))
    logger.info("Total normalized voice duration: %.2fs", total_duration)

    # 3. Generate Dark Tech Ambient Synth Music
    music_file = temp_dir / "dark_tech_synth_music.mp3"
    generate_dark_tech_synth_music(music_file, duration_sec=total_duration + 0.5)

    # 4. Mix Synth Music at -22 dB Relative to Voice
    logger.info("Mixing background synth music at -22 dB below voice track...")
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(voice_norm),
            "-i", str(music_file),
            "-filter_complex",
            "[1:a]volume=-22dB[bg]; [0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "[aout]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_master_audio),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    final_duration = get_audio_duration(str(output_master_audio))
    logger.info("Master audio track ready: %s (Duration: %.2fs)", output_master_audio.name, final_duration)
    return final_duration


# ==============================================================================
# PHASE 4: VISUAL SCENE GENERATION (PIXABAY B-ROLL & APPLE LIQUID GLASS)
# ==============================================================================
def render_hook_dilemma_scene_clip(
    query: str,
    dilemma_title: str,
    subtitle: str,
    category_pill: str,
    duration_sec: float,
    output_clip_path: Path,
    temp_dir: Path,
) -> Path:
    """Downloads cinematic gameplay or silicon macro footage, applies 8px Gaussian blur,
    and overlays the floating Apple Glassmorphism dilemma card (0.0s - 3.0s opening hook).
    """
    output_clip_path.parent.mkdir(parents=True, exist_ok=True)
    raw_broll = temp_dir / "broll_raw_scene1_hook.mp4"

    downloaded = search_and_download_pixabay_video(query, raw_broll)
    if not downloaded or not raw_broll.exists():
        logger.warning("Pixabay footage query '%s' not found. Using fallback gameplay.", query)
        search_and_download_pixabay_video("gaming pc benchmark gameplay", raw_broll)

    card_png = temp_dir / "intro_dilemma_card.png"
    create_introductory_dilemma_card(
        dilemma_title=dilemma_title,
        subtitle=subtitle,
        output_path=card_png,
        category_pill=category_pill,
        vertical_format=True,
    )

    logger.info("Formatting Scene 1 Opening Hook (8px blur + Glassmorphism Dilemma Card, Duration: %.2fs)...", duration_sec)
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,gblur=sigma=8,setsar=1,fps=60[base];"
        "[1:v]format=rgba[card];"
        "[base][card]overlay=x=(W-w)/2:y=(H-h)/2-100[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(raw_broll),
        "-i", str(card_png),
        "-t", f"{duration_sec:.2f}",
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_clip_path),
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return output_clip_path


def render_broll_scene_clip(
    query: str,
    hud_text: str,
    duration_sec: float,
    output_clip_path: Path,
    temp_dir: Path,
    scene_num: int,
) -> Path:
    """Downloads cinematic Pixabay B-roll, scales to 1080x1920, and overlays Apple Vision Pro HUD."""
    output_clip_path.parent.mkdir(parents=True, exist_ok=True)
    raw_broll = temp_dir / f"broll_raw_scene{scene_num}.mp4"

    # 1. Download Pixabay footage
    downloaded = search_and_download_pixabay_video(query, raw_broll)
    if not downloaded or not raw_broll.exists():
        logger.warning("Pixabay footage query '%s' not found. Using fallback technology query.", query)
        search_and_download_pixabay_video("computer technology", raw_broll)

    # 2. Render Apple Vision Pro HUD glass pill
    hud_pill = temp_dir / f"hud_scene{scene_num}.png"
    create_vision_pro_hud_pill(hud_text, hud_pill, vertical_format=True)

    # 3. Format to 1080x1920 @ 60fps with HUD overlay positioned at Y=360 (Upper Third)
    logger.info("Formatting Scene %d B-roll to 1080x1920 @ 60fps (Duration: %.2fs)...", scene_num, duration_sec)
    filter_complex = (
        "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,setsar=1,fps=60[base];"
        "[1:v]format=rgba[hud];"
        "[base][hud]overlay=x=(W-w)/2:y=360[v]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1",
        "-i", str(raw_broll),
        "-i", str(hud_pill),
        "-t", f"{duration_sec:.2f}",
        "-filter_complex", filter_complex,
        "-map", "[v]",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-an",
        str(output_clip_path),
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return output_clip_path


def render_benchmark_scene_clip(
    chart_data: ChartData,
    duration_sec: float,
    output_clip_path: Path,
    temp_dir: Path,
) -> Path:
    """Renders 1080x1920 60 FPS animated Apple Liquid Glass benchmark scene."""
    output_clip_path.parent.mkdir(parents=True, exist_ok=True)
    dummy_silent = temp_dir / "bench_dummy_audio.mp3"

    # Silent reference audio for timing
    subprocess.run(
        [
            "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", f"{duration_sec:.2f}", "-c:a", "libmp3lame", str(dummy_silent)
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )

    logger.info("Rendering animated 1080x1920 Apple Liquid Glass benchmark (Duration: %.2fs)...", duration_sec)
    render_animated_benchmark_video(
        chart_data=chart_data,
        audio_path=dummy_silent,
        output_video_path=output_clip_path,
        duration_sec=duration_sec,
        fps=60,
        vertical_format=True,
        subtitles_ass_path=None,  # Subtitles burned continuously in final assembly
    )
    return output_clip_path


# ==============================================================================
# PHASE 5: CONCATENATION, SUBTITLE BURNING & YOUTUBE UPLOAD
# ==============================================================================
def assemble_final_short(
    scene_clips: List[Path],
    audio_master: Path,
    subtitles_ass: Path,
    output_final_short: Path,
) -> Path:
    """Concatenates all scene visual clips, muxes master audio, and burns synchronized ASS subtitles."""
    output_final_short.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Assembling final 1080x1920 Short and burning synchronized ASS subtitles...")

    inputs = []
    for sc in scene_clips:
        inputs.extend(["-i", str(sc)])
    inputs.extend(["-i", str(audio_master)])

    ass_path_str = str(subtitles_ass.resolve()).replace(":", r"\:")
    v_inputs = "".join(f"[{i}:v]" for i in range(len(scene_clips)))
    filter_complex = f"{v_inputs}concat=n={len(scene_clips)}:v=1:a=0,ass='{ass_path_str}'[vout]"

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", f"{len(scene_clips)}:a",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_final_short),
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    logger.info("Final YouTube Short successfully assembled: %s (Size: %.2f MB)", output_final_short.name, output_final_short.stat().st_size / (1024 * 1024))
    return output_final_short


# ==============================================================================
# MAIN AUTONOMOUS PIPELINE ENTRYPOINT
# ==============================================================================
def main():
    parser = argparse.ArgumentParser(description="Autonomous YouTube Short Production Pipeline for Silicon Verdict")
    parser.add_argument("--topic", type=str, help="Optional topic override. If omitted, Gemini discovers an unexploited topic.")
    parser.add_argument("--privacy", type=str, default="private", choices=["private", "unlisted", "public"], help="YouTube visibility (strictly default: private)")
    args = parser.parse_args()

    t_start = time.time()
    run_id = uuid.uuid4().hex[:8]
    work_dir = BASE_DIR / "temp" / f"run_short_{run_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    history_file = BASE_DIR / "history.json"

    logger.info("==================================================================")
    logger.info("=== STARTING AUTONOMOUS SHORT PRODUCTION [Run ID: %s] ===", run_id)
    logger.info(" Target Privacy Status: '%s' (Strictly Private)", args.privacy)
    logger.info(" Target Output Format:  1080x1920 @ 60 FPS (YouTube Short)")
    logger.info("==================================================================")

    try:
        # Step 1: Autonomous Thematic Pillar & Spec Selection
        current_weekday = datetime.now().weekday()
        daily_spec = select_daily_short_spec(weekday_index=current_weekday)
        logger.info(
            "Thematic Pillar: %s (%s) | %s: '%s' | Game: '%s' | Voice: %s",
            daily_spec.day_name,
            daily_spec.pillar_title,
            daily_spec.theme_key,
            daily_spec.theme_description,
            daily_spec.game_title,
            daily_spec.voice_label,
        )

        t_plan_start = time.time()
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        plan = generate_autonomous_short_plan(
            client=client,
            history_path=history_file,
            topic_override=args.topic,
            spec=daily_spec,
        )
        logger.info("Plan generated in %.2fs", time.time() - t_plan_start)

        # Step 2: Voice Narration & Audio Mixing (ElevenLabs)
        t_audio_start = time.time()
        logger.info("--- Step 2: Synthesizing Voiceover with ElevenLabs (%s) ---", daily_spec.voice_label)
        audio_s1 = work_dir / "voice_scene1.mp3"
        audio_s2 = work_dir / "voice_scene2.mp3"
        audio_cta = work_dir / "voice_scene_cta.mp3"
        audio_s3 = work_dir / "voice_scene3.mp3"

        d1 = synthesize_elevenlabs_narration(plan["scene1"]["voiceover"], audio_s1, voice_id=daily_spec.voice_id)
        d2 = synthesize_elevenlabs_narration(plan["scene2"]["voiceover"], audio_s2, voice_id=daily_spec.voice_id)
        d_cta_raw = synthesize_elevenlabs_narration(plan["scene_cta"]["voiceover"], audio_cta, voice_id=daily_spec.voice_id)
        d3 = synthesize_elevenlabs_narration(plan["scene3"]["voiceover"], audio_s3, voice_id=daily_spec.voice_id)

        # Enforce strict 2.5s - 3.0s duration on the CTA clip
        audio_cta_enforced = work_dir / "voice_scene_cta_timed.mp3"
        if d_cta_raw < 2.50:
            pad_len = 2.50 - d_cta_raw
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(audio_cta), "-af", f"apad=pad_dur={pad_len:.2f}", "-c:a", "libmp3lame", str(audio_cta_enforced)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            d_cta = 2.50
        elif d_cta_raw > 3.00:
            speed_factor = d_cta_raw / 2.80
            subprocess.run(
                ["ffmpeg", "-y", "-i", str(audio_cta), "-filter:a", f"atempo={speed_factor:.3f}", "-c:a", "libmp3lame", str(audio_cta_enforced)],
                check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
            )
            d_cta = 2.80
        else:
            shutil.copy2(audio_cta, audio_cta_enforced)
            d_cta = d_cta_raw

        logger.info("Mid-roll CTA duration calibrated: %.2fs (strict 2.5-3.0s window)", d_cta)

        # Generate crystalline glass whoosh SFX and mix at -18 dB during card emergence
        whoosh_sfx = work_dir / "cta_glass_whoosh.mp3"
        generate_glass_whoosh_sfx(whoosh_sfx, duration_sec=0.5)

        audio_cta_mixed = work_dir / "voice_scene_cta_mixed.mp3"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-i", str(audio_cta_enforced),
                "-i", str(whoosh_sfx),
                "-filter_complex",
                "[1:a]volume=-18dB[sfx]; [0:a][sfx]amix=inputs=2:duration=first:dropout_transition=0[aout]",
                "-map", "[aout]",
                "-c:a", "libmp3lame",
                "-b:a", "192k",
                str(audio_cta_mixed),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )

        audio_master = work_dir / "audio_master_mixed.mp3"
        total_audio_duration = create_mixed_audio_master(
            voice_files=[audio_s1, audio_s2, audio_cta_mixed, audio_s3],
            output_master_audio=audio_master,
            temp_dir=work_dir,
        )
        logger.info("Audio production completed in %.2fs", time.time() - t_audio_start)

        # Step 3: Kinetic Subtitles (faster-whisper)
        t_sub_start = time.time()
        logger.info("--- Step 3: Generating Kinetic Word-by-Word Subtitles with Whisper ---")
        subtitles_ass = work_dir / "subtitles_safezone.ass"
        generate_kinetic_subtitles(
            audio_path=audio_master,
            output_ass_path=subtitles_ass,
            model_size="base",
        )
        logger.info("Kinetic subtitles ready in %.2fs: %s", time.time() - t_sub_start, subtitles_ass.name)

        # Step 4: Visual Generation (Apple Liquid Glass & Pixabay B-roll)
        t_visual_start = time.time()
        logger.info("--- Step 4: Rendering Apple Liquid Glass & Pixabay Visuals (1080x1920) ---")

        # Scene 1: B-roll Hook (8px blur + floating Glassmorphism Dilemma Card)
        clip1 = work_dir / "clip1_hook.mp4"
        dilemma_t = plan["scene1"].get("dilemma_title") or plan["scene1"].get("hud_text") or "HARDWARE DILEMMA"
        dilemma_s = plan["scene1"].get("dilemma_subtitle") or plan["topic"]
        cat_p = plan["scene1"].get("category_pill") or "TELEMETRY SHOWDOWN"
        render_hook_dilemma_scene_clip(
            query=plan["scene1"]["pixabay_query"],
            dilemma_title=dilemma_t,
            subtitle=dilemma_s,
            category_pill=cat_p,
            duration_sec=d1,
            output_clip_path=clip1,
            temp_dir=work_dir,
        )

        # Scene 2: Benchmark Animation
        clip2 = work_dir / "clip2_benchmark.mp4"
        chart_data = ChartData(
            title=plan["scene2"]["chart_title"],
            subtitle=plan["scene2"]["chart_subtitle"],
            preset_pill=plan["scene2"]["preset_pill"],
            metric_unit=plan["scene2"]["metric_unit"],
            labels=[plan["scene2"]["winner_label"], plan["scene2"]["loser_label"]],
            values=[float(plan["scene2"]["winner_fps"]), float(plan["scene2"]["loser_fps"])],
            winner_badge=plan["scene2"]["winner_badge"],
        )
        render_benchmark_scene_clip(
            chart_data=chart_data,
            duration_sec=d2,
            output_clip_path=clip2,
            temp_dir=work_dir,
        )

        # Scene Mid-CTA: Apple Liquid Glass Call to Action (2.5s - 3.0s)
        clip_cta = work_dir / "clip_mid_cta.mp4"
        logger.info("Rendering animated 1080x1920 Apple Liquid Glass Mid-Roll CTA (Duration: %.2fs)...", d_cta)
        render_animated_cta_video(
            audio_path=None,
            output_video_path=clip_cta,
            duration_sec=d_cta,
            fps=60,
            vertical_format=True,
            subtitles_ass_path=None,
            headline_highlight=plan["scene_cta"].get("headline_highlight", "SUBSCRIBE"),
            headline_rest=plan["scene_cta"].get("headline_rest", "FOR DAILY VERDICTS"),
            sub_text=plan["scene_cta"].get("sub_text", "Unfiltered PC Hardware Telemetry & Benchmarks"),
        )

        # Scene 3: B-roll Verdict
        clip3 = work_dir / "clip3_verdict.mp4"
        render_broll_scene_clip(
            query=plan["scene3"]["pixabay_query"],
            hud_text=plan["scene3"]["hud_text"],
            duration_sec=d3,
            output_clip_path=clip3,
            temp_dir=work_dir,
            scene_num=3,
        )
        logger.info("Visual rendering completed in %.2fs", time.time() - t_visual_start)

        # Step 5: Concat, Subtitle Burning & YouTube Upload
        t_final_start = time.time()
        logger.info("--- Step 5: Assembling Final Short & Uploading to YouTube ---")
        final_short = work_dir / "final_short_1080x1920.mp4"
        assemble_final_short(
            scene_clips=[clip1, clip2, clip_cta, clip3],
            audio_master=audio_master,
            subtitles_ass=subtitles_ass,
            output_final_short=final_short,
        )

        logger.info("Uploading Short to YouTube (Channel: 'Silicon Verdict' | Status: %s)...", args.privacy)
        youtube_url = upload_video_resumable(
            file_path=str(final_short),
            title=plan["title"],
            description=plan["description"],
            tags=plan["tags"] + ["Shorts", "TechShorts", "SiliconVerdict", "Hardware"],
            privacy_status=args.privacy,
            is_short=True,
        )

        short_id = youtube_url.split("/")[-1].replace("youtu.be/", "")
        shorts_canonical_url = f"https://youtube.com/shorts/{short_id}"

        # Record to history (JSON and SQLite Database)
        record_topic_in_history(
            MarketTopic(
                topic=plan["topic"],
                hook_angle=plan["scene1"]["hud_text"],
                target_audience="PC Enthusiasts & Hardware Engineers",
                suggested_benchmarks=[f"{plan['scene2']['winner_label']} vs {plan['scene2']['loser_label']}"],
            ),
            history_file,
        )

        record_short_history(
            weekday_index=daily_spec.weekday_index,
            theme_key=daily_spec.theme_key,
            game_title=daily_spec.game_title,
            voice_id_used=daily_spec.voice_id,
            topic=plan["topic"],
            title=plan["title"],
            video_id=short_id,
        )

        total_elapsed = time.time() - t_start

        print("\n" + "=" * 76)
        print(" [✓] AUTONOMOUS YOUTUBE SHORT PRODUCTION COMPLETED SUCCESSFULLY!")
        print(f" Total Elapsed Time:   {total_elapsed:.2f} seconds")
        print("-" * 76)
        print(f" 📺 YouTube Shorts URL: {shorts_canonical_url}")
        print(f" 🔗 Direct Link:        {youtube_url}")
        print(f" 🏷️ Video Title:        {plan['title']}")
        print(f" 🔒 Visibility:         {args.privacy.upper()} (Strictly Private)")
        print(f" 📊 Telemetry Delta:    {plan['scene2']['winner_label']} ({plan['scene2']['winner_fps']} FPS) vs {plan['scene2']['loser_label']} ({plan['scene2']['loser_fps']} FPS) [{plan['scene2']['winner_badge']}]")
        print(f" 🎬 Local Master File:  {final_short.resolve()}")
        print(f" ⏱️ Video Duration:     {total_audio_duration:.2f} seconds (1080x1920 @ 60 FPS)")
        print("=" * 76 + "\n")

    except Exception as exc:
        logger.critical("Autonomous Short production failed: %s", exc, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
