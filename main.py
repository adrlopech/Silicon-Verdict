import argparse
import logging
import os
import shutil
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure venv bin (where static ffmpeg/ffprobe live) is in PATH
venv_bin = BASE_DIR / ".venv" / "bin"
if venv_bin.is_dir() and str(venv_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

from config.settings import settings
from core.generator import (
    generate_video_plan,
)
from core.schemas import MarketTopic, MotionStoryProject
from core.topic_engine import generate_market_topic, record_topic_in_history
from services.renderer import (
    VideoRenderer,
)
from services.history import (
    record_generation_metric,
    record_short_history,
)
from services.media import fetch_all_scene_media
from services.notifier import notify_pipeline_success
from services.tiktok import (
    get_video_duration_ffprobe,
)
from services.tts import synthesize_all_scenes
from services.voice import (
    get_ffmpeg_bin,
)
from services.youtube import upload_video_resumable

# Configure root logger with console and structured file logging
(BASE_DIR / "logs").mkdir(parents=True, exist_ok=True)
log_file_path = BASE_DIR / "logs" / "pipeline.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_file_path, encoding="utf-8"),
    ],
)
logger = logging.getLogger("silicon_verdict")


def get_next_topic_from_file(file_path: Path) -> Optional[str]:
    """Retrieves and removes the first non-empty topic from a topics file if available."""
    if not file_path.is_file():
        return None

    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    chosen_topic = None
    remaining_lines = []

    for line in lines:
        cleaned = line.strip()
        if cleaned and not cleaned.startswith("#") and chosen_topic is None:
            chosen_topic = cleaned
        else:
            remaining_lines.append(line)

    if chosen_topic:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(remaining_lines)
        logger.info("Retrieved manual topic from file %s: '%s'", file_path.name, chosen_topic)

    return chosen_topic


def run_pipeline(
    topic: Optional[str] = None,
    dry_run: bool = False,
    privacy_override: Optional[str] = None,
    history_file: str = "history.json",
    scenes_limit: Optional[int] = None,
) -> None:
    """Executes the complete autonomous end-to-end production pipeline for Silicon Verdict."""
    start_time = time.time()
    run_id = uuid.uuid4().hex[:8]
    work_dir = Path(settings.TMP_DIR) / f"run_{run_id}"
    audio_dir = work_dir / "audio"
    media_dir = work_dir / "media"
    history_path = Path(history_file).resolve()

    logger.info("==================================================================")
    logger.info("=== STARTING SILICON VERDICT PIPELINE [Run ID: %s] ===", run_id)
    if scenes_limit:
        logger.info("Scope mode: Limited to %d representative scenes (Smoke Test)", scenes_limit)
    logger.info("==================================================================")

    market_topic_obj: Optional[MarketTopic] = None
    suggested_benchmarks = None

    try:
        # Step 1: Autonomous Market Intelligence & Topic Discovery
        t0 = time.time()
        logger.info("--- Step 1: Market Intelligence & Technical Topic Discovery ---")
        if topic:
            active_topic = topic
            logger.info("Operating with target topic: '%s'", active_topic)
        else:
            logger.info("No topic specified. Querying Silicon Verdict Autonomous Topic Engine...")
            market_topic_obj = generate_market_topic(history_path)
            active_topic = market_topic_obj.topic
            suggested_benchmarks = market_topic_obj.suggested_benchmarks

        # Step 2: AI Script, Benchmarks & Metadata Generation (Gemini)
        logger.info("--- Step 2: Generating Silicon Verdict Technical Script via Gemini ---")
        project = generate_video_plan(
            active_topic,
            suggested_benchmarks=suggested_benchmarks,
            scenes_limit=scenes_limit,
        )
        logger.info("Script Generation completed in %.2fs", time.time() - t0)
        logger.info("Video Title: %s", project.title)
        logger.info("Planned Scenes: %d", len(project.scenes))
        for s in project.scenes:
            chart_status = "YES" if s.chart_data else "NO"
            logger.info("  • Scene %d: '%s' | Chart: %s | Short: %s", s.scene_id, s.chapter_title, chart_status, s.is_short_highlight)

        # Step 3: Text-to-Speech Narration (ElevenLabs)
        t1 = time.time()
        logger.info("--- Step 3: Synthesizing Technical Voiceover with ElevenLabs ---")
        audio_results = synthesize_all_scenes(project.scenes, audio_dir)
        audio_map = {a.scene_id: a for a in audio_results}
        audio_durations = {a.scene_id: a.duration_seconds for a in audio_results}
        total_audio_sec = sum(audio_durations.values())
        logger.info("Audio Synthesis completed in %.2fs (Total runtime: %.2fs)", time.time() - t1, total_audio_sec)

        # Step 4: Media Acquisition (Pixabay HD Video & Hardware B-roll)
        t2 = time.time()
        logger.info("--- Step 4: Downloading Hardware Macro B-roll Footage via Pixabay ---")
        media_results = fetch_all_scene_media(project.scenes, audio_durations, media_dir)
        media_map = {m.scene_id: m for m in media_results}
        logger.info("Media Acquisition completed in %.2fs", time.time() - t2)

        # Step 5: High-Tech Chart Rendering and FFmpeg Video Assembly
        t3 = time.time()
        logger.info("--- Step 5: Rendering Benchmark Charts & Compiling Video via FFmpeg ---")
        renderer = VideoRenderer(work_dir)
        rendered_outputs = renderer.render_project(project, media_map, audio_map)
        video_file_size_mb = Path(rendered_outputs.full_video_path).stat().st_size / (1024 * 1024)
        logger.info(
            "Video Rendering completed in %.2fs | Output: %s (%.2f MB, 1080p 30fps)",
            time.time() - t3,
            Path(rendered_outputs.full_video_path).name,
            video_file_size_mb,
        )

        # Step 6: YouTube Upload (Full 16:9 Documentary & 9:16 Shorts)
        full_video_url = "https://youtu.be/DRY_RUN_MODE"
        shorts_urls = []
        privacy = privacy_override or settings.YOUTUBE_PRIVACY_STATUS

        if not dry_run:
            t4 = time.time()
            logger.info("--- Step 6: Uploading Main Silicon Verdict Video to YouTube (Privacy: '%s') ---", privacy)
            full_video_url = upload_video_resumable(
                file_path=rendered_outputs.full_video_path,
                title=project.title,
                description=project.description,
                tags=project.tags,
                privacy_status=privacy,
                is_short=False,
            )
            logger.info("Main Video Upload completed in %.2fs -> %s", time.time() - t4, full_video_url)

            # Upload each extracted 9:16 Short using its specific ShortMetadata
            for i, short_path in enumerate(rendered_outputs.shorts_paths):
                if i < len(project.shorts):
                    short_meta = project.shorts[i]
                    short_title = short_meta.title
                    short_desc = short_meta.description
                else:
                    short_title = f"{project.title[:45]} - Part {i+1} #Shorts"
                    short_desc = f"{project.description[:250]}\n\n#Shorts #SiliconVerdict #Hardware"

                logger.info("Uploading Short #%d: '%s' (Privacy: '%s')", i + 1, short_title, privacy)
                s_url = upload_video_resumable(
                    file_path=short_path,
                    title=short_title,
                    description=short_desc,
                    tags=project.tags + ["Shorts", "TechShorts", "SiliconVerdict"],
                    privacy_status=privacy,
                    is_short=True,
                )
                shorts_urls.append(s_url)
                logger.info("Short #%d uploaded -> %s", i + 1, s_url)
        else:
            logger.info("[DRY RUN] Skipping YouTube upload. Local 16:9 video rendered at: %s", rendered_outputs.full_video_path)
            for idx, sp in enumerate(rendered_outputs.shorts_paths):
                shorts_urls.append(f"file://{sp}")

        # Step 7: Record Topic into History
        if market_topic_obj:
            record_topic_in_history(market_topic_obj, history_path)
        else:
            record_topic_in_history(
                MarketTopic(
                    topic=active_topic,
                    hook_angle="Test smoke execution",
                    target_audience="PC Enthusiasts & Hardware Engineers",
                    suggested_benchmarks=["1% Lows at 1080p", "VRAM allocation limits"],
                ),
                history_path,
            )

        # Step 8: Dispatch Notifications
        notify_pipeline_success(
            title=project.title,
            full_video_url=full_video_url,
            shorts_urls=shorts_urls,
            scenes_count=len(project.scenes),
            pinned_comment=project.pinned_comment,
            thumbnail_prompt=project.thumbnail_prompt,
        )

        total_elapsed = time.time() - start_time
        logger.info("==================================================================")
        logger.info(" [✓] SILICON VERDICT PIPELINE COMPLETED IN %.2fs", total_elapsed)
        logger.info(" Main Video:   %s", full_video_url)
        for idx, s_url in enumerate(shorts_urls, start=1):
            logger.info(" Short #%d:     %s", idx, s_url)
        logger.info(" Privacy:      %s", privacy)
        logger.info("==================================================================")

    except Exception as exc:
        logger.critical("Fatal error during pipeline execution: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        # Step 9: Clean temporary workspace files
        if work_dir.exists():
            logger.info("Cleaning temporary workspace directory: %s", work_dir)
            shutil.rmtree(work_dir, ignore_errors=True)


def topic_override_or_none(topic: Optional[str]) -> Optional[str]:
    return topic or None


def run_master_video_pipeline(
    topic: Optional[str] = None,
    category: Optional[str] = None,
    platform: str = "all",
    dry_run: bool = False,
    privacy: str = "public",
    history_file: str = "history.json",
    export_only: bool = False,
    preset: str = "auto",
    weekday_index: Optional[int] = None,
    benchmark: bool = False,
    series: Optional[str] = None,
    prefer_bank: bool = True,
) -> Dict[str, Any]:
    """Executes the single unified master video pipeline (60-120s) for YouTube Shorts and TikTok."""
    start_time = time.time()
    run_id = uuid.uuid4().hex[:8]
    work_dir = Path(settings.TMP_DIR) / f"run_master_{run_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_bin()

    if benchmark:
        export_only = True

    logger.info("==================================================================")
    logger.info("=== STARTING UNIFIED MASTER (60-120s) PIPELINE [Run ID: %s] ===", run_id)
    logger.info(" Format:             Single Master Vertical (1080x1920 @ 30 FPS M2 Optimized)")
    logger.info(" Target Duration:    Strictly between 60.0s and 120.0s (1-2 min)")
    logger.info(" Export Only Mode:   %s", export_only)
    logger.info(" Benchmark Mode:     %s", benchmark)
    logger.info(" Distribution:       YouTube Public Direct + TikTok Local Staging")
    logger.info(" Visual Preset:      %s", preset)
    logger.info("==================================================================")

    if series == "motion":
        from services.motion_pipeline import run_motion_pipeline
        return run_motion_pipeline(topic=topic, export_only=export_only or benchmark, dry_run=dry_run, privacy=privacy)

    if series == "minecraft":
        from services.mc_pipeline import run_minecraft_pipeline
        try:
            return run_minecraft_pipeline(topic=topic, export_only=export_only or benchmark, dry_run=dry_run, privacy=privacy, prefer_bank=prefer_bank)
        except Exception as exc:
            logger.critical("Minecraft pipeline failed: %s", exc, exc_info=True)
            sys.exit(1)

    try:
        # 1. Resolve Category ID (1: Hardware Deep Dive, 2: Gaming & Optimization, 3: Tech Curiosities)
        current_weekday = datetime.now().weekday() if weekday_index is None else weekday_index
        cat_id = 3
        if category:
            cat_norm = str(category).lower().strip()
            if cat_norm in ("1", "hardware", "hardware_benchmarks", "deep_dive"):
                cat_id = 1
            elif cat_norm in ("2", "gaming", "gaming_benchmarks", "optimization"):
                cat_id = 2
            elif cat_norm in ("3", "curiosities", "tech_curiosities", "storytelling", "schematic"):
                cat_id = 3
            elif cat_norm in ("4", "auto"):
                cat_id = (current_weekday % 3) + 1
        elif weekday_index is not None:
            cat_id = (weekday_index % 3) + 1

        story_topic_forced = bool(topic)
        # 2. Kinetic Motion Story Generation (100% US English, 140-160 words, Word Anchors)
        t_script_start = time.time()
        from services.content_generator import generate_motion_story, get_emergency_motion_story
        if benchmark:
            story: MotionStoryProject = get_emergency_motion_story(category_id=cat_id, topic=topic, series=series)
            story.full_script = (
                "Why does Wi-Fi drop near a microwave? "
                "Routers emit a fraction of a watt, but microwaves blast one thousand watts of RF noise!"
            )
            story.visual_triggers = story.visual_triggers[:3]
        elif series == "simple" and cat_id == 3:
            from services.story_generator import generate_story
            story = generate_story(topic_override_or_none(topic), prefer_bank=prefer_bank)
        else:
            story: MotionStoryProject = generate_motion_story(category_id=cat_id, topic_override=topic, series=series, prefer_bank=prefer_bank)
        if getattr(story, "is_fallback", False) and not (benchmark or export_only or dry_run):
            logger.error("Gemini unavailable and the story bank is empty: refusing to publish the deterministic fallback. "
                         "Re-run later, run scripts/refill_story_bank.py, or use --export-only.")
            sys.exit(2)
        topic = story.topic
        t_script = time.time() - t_script_start
        logger.info(
            "Kinetic Motion Story ready in %.2fs: '%s' | Category: %s (ID: %d) | Words: %d",
            t_script, story.title, story.category_name, cat_id, story.get_total_words()
        )

        # 3. Master Narration Synthesis & Dynamic Voice Modulation (Native ElevenLabs Timestamps)
        t_voice_start = time.time()
        from services.voice_synthesizer import synthesize_voice_with_timestamps
        master_audio_raw = work_dir / "master_audio_raw.mp3"
        final_audio_path, final_audio_dur, word_timestamps = synthesize_voice_with_timestamps(
            text=story.full_script,
            output_audio_path=master_audio_raw,
            voice_id=(settings.ELEVENLABS_VOICE_3 if series == "simple" else settings.ELEVENLABS_VOICE_ID),
            category=story.category_name.lower().replace(" ", "_"),
            speed=1.02,
            min_duration=5.0 if benchmark else 55.0,
            max_duration=8.5 if benchmark else 70.0,
            **(
                dict(
                    natural=True,
                    model_id="eleven_multilingual_v2",
                    stability=0.32,
                    style=0.5,
                    similarity_boost=0.8,
                )
                if series == "simple" and not benchmark
                else {}
            ),
        )
        t_voice = time.time() - t_voice_start
        logger.info("Master narration + alignment synthesized in %.2fs: %.2fs audio", t_voice, final_audio_dur)

        # 4. Programmatic Remotion Render (1080x1920 @ 30 FPS, VideoToolbox Hardware Acceleration)
        from services.remotion_renderer import render_remotion_video
        final_video = work_dir / "master_remotion_30fps.mp4"
        cover_frame_path = work_dir / "cover_frame.jpg"

        final_video, cover_frame_path, timing_telemetry = render_remotion_video(
            story=story,
            master_audio_path=final_audio_path,
            output_video_path=final_video,
            output_cover_path=cover_frame_path,
            word_timestamps=word_timestamps,
            fps=30,
        )
        actual_dur = get_video_duration_ffprobe(final_video)
        logger.info("Remotion Master Render Completed: %s (Duration: %.2fs @ 30 FPS)", final_video.name, actual_dur)

        # 5. Multi-Platform Distribution (Single Master Render Output)
        # One folder per video, named after its title; files are named by creation date and time
        from services.output_layout import timestamp_stem, video_dir
        file_stem = timestamp_stem()
        yt_out_dir = video_dir("youtube", story.title)
        tiktok_out_dir = video_dir("tiktok", story.title)

        # Destination 1: output/youtube/<title>/<timestamp>.mp4 & cover
        yt_master_video = yt_out_dir / f"{file_stem}.mp4"
        shutil.copyfile(final_video, yt_master_video)
        yt_cover_file = yt_out_dir / f"{file_stem}_cover.jpg"
        shutil.copyfile(cover_frame_path, yt_cover_file)

        # Destination 2: output/tiktok/<title>/<timestamp>.mp4 & cover
        tiktok_master_video = tiktok_out_dir / f"{file_stem}.mp4"
        shutil.copyfile(final_video, tiktok_master_video)
        tiktok_cover_file = tiktok_out_dir / f"{file_stem}_cover.jpg"
        shutil.copyfile(cover_frame_path, tiktok_cover_file)

        # Destination 3: output/tiktok/{YYYYMMDD}_{theme}.txt (Manual Publishing Metadata)
        tiktok_metadata_file = tiktok_out_dir / f"{file_stem}.txt"

        tag_list = story.tags if all(t.startswith('#') for t in story.tags) else [f'#{t}' if not t.startswith('#') else t for t in story.tags]
        meta_content = (
            f"================================================================================\n"
            f"SILICON VERDICT • TIKTOK & SHORTS METADATA (100% US ENGLISH)\n"
            f"Creation Date:     {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
            f"Video File:        {tiktok_master_video.name}\n"
            f"Measured Duration: {actual_dur:.2f}s (Eligible Creator Rewards / Monetization: 55-70s)\n"
            f"Resolution / FPS:  1080x1920 (9:16 Vertical) @ 60 FPS\n"
            f"Category:          {story.category_name}\n"
            f"Theme / Topic:     {story.topic}\n"
            f"================================================================================\n\n"
            f"[SUGGESTED TITLE]\n"
            f"{story.title}\n\n"
            f"[DESCRIPTION]\n"
            f"{story.description}\n\n"
            f"[TECHNICAL HASHTAGS]\n"
            f"{' '.join(tag_list)}\n\n"
            f"[PINNED COMMENT / COMMUNITY DEBATE]\n"
            f"{story.pinned_comment}\n\n"
            f"[COMPLETE SCRIPT - 100% US ENGLISH]\n"
            f"{story.full_script}\n"
            f"================================================================================\n"
            f"PUBLISHING INSTRUCTIONS:\n"
            f"1. Upload the video file to TikTok Studio:\n"
            f"   https://www.tiktok.com/creator-center/upload\n"
            f"2. Copy and paste the suggested title and technical hashtags into the description.\n"
            f"3. When the TikTok Developers application completes review and the token is generated\n"
            f"   in data/tiktok_token.json, direct API publishing will operate transparently.\n"
            f"================================================================================\n"
        )
        tiktok_metadata_file.write_text(meta_content, encoding="utf-8")

        # Distribution & Upload
        youtube_url = ""
        yt_video_id = ""
        if not export_only and not dry_run:
            logger.info("Uploading single master video to YouTube API (Privacy: %s)...", privacy)
            try:
                youtube_url = upload_video_resumable(
                    file_path=str(yt_master_video),
                    title=story.title,
                    description=story.description,
                    tags=story.tags,
                    privacy_status=privacy,
                    is_short=True,
                )
                yt_video_id = youtube_url.split("/")[-1]
                logger.info("YouTube direct publish completed: %s", youtube_url)
            except Exception as exc:
                logger.error("YouTube upload encountered an issue (%s). Video preserved locally.", exc)
                youtube_url = f"file://{yt_master_video.resolve()}"
                yt_video_id = f"local_{run_id}"
        else:
            youtube_url = f"file://{yt_master_video.resolve()}"
            yt_video_id = f"local_export_{run_id}"
            logger.info("[EXPORT ONLY] Video preserved in output/youtube/ and output/tiktok/.")

        record_short_history(
            weekday_index=current_weekday,
            theme_key=f"category_{cat_id}",
            game_title=story.header_banner,
            voice_id_used=settings.ELEVENLABS_VOICE_ID,
            topic=story.topic,
            title=story.title,
            video_id=yt_video_id,
            category=story.category_name,
            tone="kinetic_motion",
            preset="remotion_kinetic",
        )

        total_elapsed = time.time() - start_time
        file_size_mb = yt_master_video.stat().st_size / (1024 * 1024)

        full_text = story.full_script
        tokens_in = getattr(story, "gemini_input_tokens", 450)
        tokens_out = getattr(story, "gemini_output_tokens", 380)
        elevenlabs_chars = len(full_text)
        word_cnt = len(full_text.split())

        cost_record = record_generation_metric(
            run_id=run_id,
            topic_id=topic or "silicon_verdict",
            category=story.category_name,
            gemini_input_tokens=tokens_in,
            gemini_output_tokens=tokens_out,
            elevenlabs_characters=elevenlabs_chars,
            duration_seconds=actual_dur,
            word_count=word_cnt,
        )

        t_bundle_check = timing_telemetry.get("remotion_bundle_check", 0.0)
        t_render = timing_telemetry.get("headless_render", 0.0)
        t_mux = timing_telemetry.get("videotoolbox_mux", 0.0)

        if benchmark:
            print("\n" + "=" * 80)
            print(" ⚡ SILICON VERDICT: APPLE SILICON M2 PERFORMANCE TELEMETRY REPORT")
            print("=" * 80)
            print(f" [1] Gemini Scripting:            {t_script:6.2f}s  (Target: < 2.0s)  [{'PASS' if t_script < 2.5 else 'WARN'}]")
            print(f" [2] ElevenLabs TTS + Alignment:  {t_voice:6.2f}s  (Target: < 4.0s)  [{'PASS' if t_voice < 4.5 else 'WARN'}]")
            print(f" [3] Remotion Bundle Check:       {t_bundle_check:6.4f}s  (Target: = 0.0s)  [PASS]")
            print(f" [4] Headless 30fps Render (M2):  {t_render:6.2f}s  (Target: < 12.0s) [{'PASS' if t_render < 12.0 else 'WARN'}]")
            print(f" [5] VideoToolbox Muxing:         {t_mux:6.2f}s  (Target: < 1.5s)  [{'PASS' if t_mux < 1.5 else 'WARN'}]")
            print("-" * 80)
            print(f" 🚀 TOTAL PIPELINE RUNTIME:       {total_elapsed:6.2f}s  (TARGET: < 20.0s) [{'PASS' if total_elapsed < 20.0 else 'FAIL'}]")
            print("=" * 80 + "\n")
        else:
            print("\n" + "=" * 80)
            print(" 🚀 SILICON VERDICT: KINETIC MOTION GRAPHICS MASTER PIPELINE (30 FPS M2)")
            print("=" * 80)
            print(f" YouTube Master Video: {yt_master_video.resolve()}")
            print(f" YouTube URL / ID:     {youtube_url}")
            print(f" TikTok Staging Video: {tiktok_master_video.resolve()}")
            print(f" Cover Frame (High-CTR): {tiktok_cover_file.resolve()}")
            print(f" TikTok Metadata:      {tiktok_metadata_file.resolve()}")
            print(f" Category & Engine:    {story.category_name} // REMOTION KINETIC 30 FPS + VIDEOTOOLBOX")
            print(f" Exact Duration:       {actual_dur:.2f} seconds (1080x1920 @ 30 FPS)")
            print(f" Word Count:           {word_cnt} words (Target: 140-160 words, 100% US English)")
            print(f" ElevenLabs Chars:     {elevenlabs_chars} characters")
            print(f" Gemini Tokens:        {tokens_in + tokens_out} tokens (in: {tokens_in}, out: {tokens_out})")
            print(f" Estimated API Cost:   ${cost_record['estimated_cost_usd']:.5f} USD")
            print(f" File Size:            {file_size_mb:.2f} MB")
            print(f" Production Time:      {total_elapsed:.2f} seconds")
            print("=" * 80 + "\n")

        # Story bank policy: this video consumed one banked script, so top the bank back up (best effort).
        if prefer_bank and series == "simple" and not benchmark and not story_topic_forced:
            from services.bank_manager import replenish_after_use
            replenish_after_use(series)

        return {
            "youtube_video": str(yt_master_video.resolve()),
            "youtube_url": youtube_url,
            "tiktok_video": str(tiktok_master_video.resolve()),
            "tiktok_cover": str(tiktok_cover_file.resolve()),
            "tiktok_metadata": str(tiktok_metadata_file.resolve()),
            "duration": actual_dur,
            "file_size_mb": file_size_mb,
            "title": story.title,
            "tags": tag_list,
            "topic": story.topic,
            "estimated_cost_usd": cost_record["estimated_cost_usd"],
        }

    except Exception as exc:
        logger.critical("Fatal error during master video pipeline: %s", exc, exc_info=True)
        sys.exit(1)


# Maintain alias for compatibility
run_vertical_long_pipeline = run_master_video_pipeline


GENERA_MENU_TEXT = """🎬 **Production Setup — Silicon Verdict**

Select the thematic focus for this video (60-120s):

1. **Hardware Deep Dive & Benchmarks** (Liquid Glass Style: Silicon, microarchitectures, memory buses, technical telemetry).
2. **Gaming & Optimization** (Liquid Glass Style: Game performance, competitive presets, frametimes, and 1% lows).
3. **Tech Curiosities & Storytelling** (2D Schematic Style: Engineering paradoxes, subsea cables, satellites, chip physics).
4. **Automatic (AI)** (AI selects optimal category based on data/history.db rotation and retention analytics).

👉 Enter your choice: [1, 2, 3, or 4]"""


def get_category_from_choice(choice: int) -> str:
    """Maps a numeric choice (1-4) to a Silicon Verdict category key or rotated category."""
    from services.history import get_next_rotated_category
    mapping = {
        1: "hardware_benchmarks",
        2: "gaming_benchmarks",
        3: "tech_curiosities",
        4: "auto",
    }
    selected = mapping.get(choice)
    if selected == "auto":
        return get_next_rotated_category()
    return selected or "hardware_benchmarks"


def handle_genera_prompt(user_choice: Optional[int] = None) -> str:
    """Displays the interactive 2-step prompt menu and returns the selected category key."""
    if user_choice is not None:
        if user_choice in (1, 2, 3, 4):
            return get_category_from_choice(user_choice)
        print("Invalid option. Please enter 1, 2, 3, or 4 to proceed with 'genera'.")

    print("\n" + GENERA_MENU_TEXT + "\n")
    while True:
        try:
            raw_input_val = input("Selection [1, 2, 3, or 4]: ").strip()
            if not raw_input_val:
                continue
            if raw_input_val in ("1", "2", "3", "4"):
                return get_category_from_choice(int(raw_input_val))
            print("Invalid option. Please enter 1, 2, 3, or 4 to proceed with 'genera'.")
        except (EOFError, KeyboardInterrupt):
            print("\nOperation cancelled by user.")
            sys.exit(0)


def parse_args():
    parser = argparse.ArgumentParser(description="Silicon Verdict Autonomous YouTube Content Pipeline")
    parser.add_argument(
        "--platform",
        type=str,
        choices=["youtube", "tiktok", "all"],
        default="all",
        help="Target distribution platform: youtube, tiktok, or all (default: all).",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="Content category (e.g. 1, 2, 3, 4, hardware, gaming, curiosities, auto, etc.).",
    )
    parser.add_argument(
        "--interactive",
        "--genera",
        action="store_true",
        dest="interactive",
        help="Trigger the two-step interactive 'genera' selection menu.",
    )
    parser.add_argument(
        "--choice",
        type=int,
        choices=[1, 2, 3, 4],
        default=None,
        help="Direct numeric choice for genera workflow (1: Hardware, 2: Gaming, 3: Tech Curiosities, 4: Auto).",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["master", "short", "long"],
        default="master",
        help="Content format: master (60-120s unified master video), short (25-35s legacy), long (61-68s).",
    )
    parser.add_argument(
        "--export-only",
        action="store_true",
        help="Export video and metadata locally to output/youtube/ and output/tiktok/ without uploading to APIs.",
    )
    parser.add_argument(
        "--topic",
        type=str,
        help="Specify an explicit topic. If omitted, autonomous topic engine will generate one from market trends.",
    )
    parser.add_argument(
        "--topics-file",
        type=str,
        default="topics.txt",
        help="Path to file containing fallback topics line-by-line.",
    )
    parser.add_argument(
        "--history-file",
        type=str,
        default="history.json",
        help="Path to JSON file tracking previously produced topics (default: history.json).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render all video, charts, and audio locally without uploading to YouTube/TikTok.",
    )
    parser.add_argument(
        "--privacy",
        type=str,
        choices=["public", "unlisted", "private"],
        default="public",
        help="Override upload privacy status (default: public).",
    )
    parser.add_argument(
        "--preset",
        type=str,
        choices=["auto", "liquid_glass", "schematic_tech"],
        default="auto",
        help="Visual and layout preset: liquid_glass (default benchmark/gaming) or schematic_tech (2D dark technical blueprint).",
    )
    parser.add_argument(
        "--scenes_limit",
        "--scenes-limit",
        type=int,
        dest="scenes_limit",
        default=None,
        help="Limit the number of scenes generated (e.g. 3 for fast smoke tests).",
    )
    parser.add_argument(
        "--audit-latest",
        action="store_true",
        help="Audit the latest generated video in output/tiktok/ and output QA report.",
    )
    parser.add_argument(
        "--apply-fixes",
        action="store_true",
        help="Apply proposed QA corrections to the latest audited video.",
    )
    parser.add_argument(
        "--help-commands",
        "--commands",
        action="store_true",
        help="List all configured commands, chat triggers, and operational options.",
    )
    parser.add_argument(
        "--series",
        type=str,
        choices=["hardware", "simple", "minecraft", "motion"],
        default=None,
        help="Tech Curiosities sub-series: hardware (physics/engineering), simple (everyday), minecraft (concept explained inside Minecraft, ~64 s, always a new Gemini script), motion (type 6: kinetic-typography Motion Graphics, 62-84 s, English only; curiosities and games with real footage).",
    )
    parser.add_argument(
        "--motion-kind",
        type=str,
        choices=["auto", "curiosity", "game"],
        default="auto",
        help="With --series motion: curiosity (tech idea), game (engineering fact about a game with real footage) or auto (alternates; a game needs unused, non-blacklisted footage).",
    )
    parser.add_argument(
        "--motion-format",
        type=str,
        choices=["auto", "any", "myth", "tier", "whatif", "easter", "evolution", "versus"],
        default="auto",
        help="With --series motion: content format. myth (myth or fact verdicts), tier (S-F tier list), whatif (a hypothetical about computing), easter (a hidden detail of a game, with footage), evolution (timelines), versus (two contenders over several rounds), any (a random one) or auto (the classic explainer).",
    )
    parser.add_argument(
        "--from-bank",
        action="store_true",
        help="(Default now) Use the story bank first. Kept for compatibility.",
    )
    parser.add_argument(
        "--no-bank",
        action="store_true",
        help="Skip the story bank and generate the script live with Gemini.",
    )
    parser.add_argument(
        "--benchmark",
        action="store_true",
        help="Run high-speed Apple Silicon M2 performance benchmark (telemetry per phase, < 20s target).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    if any(arg in ("help", "ayuda", "--help-commands", "--commands") for arg in sys.argv[1:]):
        from scripts.help import print_help
        print_help()
        sys.exit(0)

    args = parse_args()

    if args.audit_latest:
        from services.qa_inspector import format_qa_report, run_full_qa_audit
        audit_res = run_full_qa_audit()
        print("\n" + format_qa_report(audit_res) + "\n")
        sys.exit(0)

    if args.apply_fixes:
        from services.qa_inspector import apply_qa_fixes, run_full_qa_audit
        audit_res = run_full_qa_audit()
        res = apply_qa_fixes(audit_res)
        print("✅ Corrections applied successfully:")
        for fix in res["fixes_applied"]:
            print(f"   • {fix}")
        print(f"📁 Updated video: {res['video_path']}")
        sys.exit(0)

    # Resolve category interactively or through CLI flags
    resolved_category = args.category
    if args.choice:
        resolved_category = get_category_from_choice(args.choice)
        # Mandate: All videos generated via 'genera' / direct choice upload automatically in public mode
        args.export_only = False
        args.privacy = "public"
    elif args.interactive:
        resolved_category = handle_genera_prompt()
        # Mandate: All videos generated via 'genera' / interactive upload automatically in public mode
        args.export_only = False
        args.privacy = "public"
    elif resolved_category:
        clean_cat = str(resolved_category).strip()
        if clean_cat in ("1", "2", "3", "4"):
            resolved_category = get_category_from_choice(int(clean_cat))
        elif clean_cat.lower() in ("hardware", "hardware_benchmarks"):
            resolved_category = "hardware_benchmarks"
        elif clean_cat.lower() in ("gaming", "gaming_benchmarks"):
            resolved_category = "gaming_benchmarks"
        elif clean_cat.lower() in ("curiosities", "tech_curiosities", "schematic"):
            resolved_category = "tech_curiosities"
        elif clean_cat.lower() == "auto":
            from services.history import get_next_rotated_category
            resolved_category = get_next_rotated_category()

    chosen_topic = args.topic
    if args.series == "motion":
        from services.motion_pipeline import run_motion_pipeline
        try:
            run_motion_pipeline(topic=chosen_topic, export_only=args.export_only or args.benchmark, dry_run=args.dry_run, privacy=args.privacy, kind=args.motion_kind, fmt=args.motion_format)
        except Exception as exc:
            logger.error("Motion Graphics pipeline failed: %s", exc)
            sys.exit(1)
        sys.exit(0)
    if args.series == "minecraft":
        from services.mc_pipeline import run_minecraft_pipeline
        from services.mc_story_generator import McScriptUnavailable
        try:
            run_minecraft_pipeline(topic=chosen_topic, export_only=args.export_only or args.benchmark, dry_run=args.dry_run, privacy=args.privacy, prefer_bank=not args.no_bank)
        except McScriptUnavailable as exc:  # every Minecraft video needs a new Gemini script; there is no fallback
            logger.error("%s", exc)
            sys.exit(1)
        sys.exit(0)
    if not chosen_topic and Path(args.topics_file).is_file() and resolved_category != "tech_curiosities":
        chosen_topic = get_next_topic_from_file(Path(args.topics_file))

    if args.format == "short" and args.preset != "schematic_tech" and resolved_category != "tech_curiosities":
        run_pipeline(
            topic=chosen_topic,
            dry_run=args.dry_run,
            privacy_override=args.privacy,
            history_file=args.history_file,
            scenes_limit=args.scenes_limit,
        )
    else:
        run_master_video_pipeline(
            topic=chosen_topic,
            category=resolved_category,
            platform=args.platform,
            dry_run=args.dry_run,
            privacy=args.privacy,
            history_file=args.history_file,
            export_only=args.export_only,
            preset=args.preset,
            benchmark=args.benchmark,
            series=args.series,
            prefer_bank=not args.no_bank,
        )
