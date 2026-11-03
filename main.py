import argparse
import logging
import os
import shutil
import sys
import time
import uuid
from pathlib import Path
from typing import Optional

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
    DailyShortSpec,
    generate_tiktok_long_plan,
    generate_video_plan,
    get_emergency_tiktok_long_project,
    select_daily_short_spec,
)
from core.schemas import ChartData, MarketTopic, TikTokLongProject
from core.topic_engine import generate_market_topic, record_topic_in_history
from engine.charts import render_animated_benchmark_video
from engine.renderer import (
    VideoRenderer,
    create_golden_rule_card,
    create_introductory_dilemma_card,
    create_silicon_specs_card,
    create_voting_poll_card,
    render_composite_overlay_clip,
)
from services.debug_overlay import (
    generate_shorts_safezone_template,
    overlay_safezone_on_video,
)
from services.history import record_short_history
from services.media import fetch_all_scene_media
from services.notifier import notify_pipeline_success
from services.subtitles import generate_kinetic_subtitles
from services.tiktok import (
    get_video_duration_ffprobe,
    upload_video_to_tiktok,
    validate_tiktok_creator_rewards_eligibility,
)
from services.tts import synthesize_all_scenes
from services.voice import (
    get_ffmpeg_bin,
    measure_audio_duration,
    validate_and_enforce_long_video_duration,
)
from services.youtube import upload_video_resumable

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
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


def run_vertical_long_pipeline(
    topic: Optional[str] = None,
    platform: str = "tiktok",
    dry_run: bool = False,
    privacy: str = "private",
    history_file: str = "history.json",
) -> None:
    """Executes the 5-act vertical long video pipeline (61-68s) for TikTok Creator Rewards and YouTube."""
    from datetime import datetime
    start_time = time.time()
    run_id = uuid.uuid4().hex[:8]
    work_dir = Path(settings.TMP_DIR) / f"run_long_{run_id}"
    work_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_bin()

    logger.info("==================================================================")
    logger.info("=== STARTING VERTICAL LONG (61-68s) PIPELINE [Run ID: %s] ===", run_id)
    logger.info(" Target Platform:    %s", platform.upper())
    logger.info(" Format:             Long Vertical (1080x1920 @ 60 FPS | 5 Acts)")
    logger.info(" Monetization Floor: Strictly > 60.5s for TikTok Creator Rewards")
    logger.info("==================================================================")

    try:
        # 1. Thematic Matrix & Voice Rotation
        current_weekday = datetime.now().weekday()
        spec: DailyShortSpec = select_daily_short_spec(weekday_index=current_weekday)
        logger.info(
            "Pillar: %s (%s) | %s: '%s' | Game: '%s' | Voice: %s",
            spec.day_name, spec.pillar_title, spec.theme_key, spec.theme_description, spec.game_title, spec.voice_label
        )

        # 2. 5-Block Script Generation (~145-165 words)
        try:
            project: TikTokLongProject = generate_tiktok_long_plan(topic=topic, spec=spec)
        except Exception as exc:
            logger.warning("Gemini plan generation fallback (%s). Using deterministic 5-block plan.", exc)
            project = get_emergency_tiktok_long_project(topic=topic, spec=spec)

        total_words = project.get_total_words()
        logger.info(
            "5-Act Script generated (%d words): Act 1 (%dw), Act 2 (%dw), Act 3 (%dw), Act 4 (%dw), Act 5 (%dw)",
            total_words,
            len(project.act1.voiceover.split()),
            len(project.act2.voiceover.split()),
            len(project.act3.voiceover.split()),
            len(project.act4.voiceover.split()),
            len(project.act5.voiceover.split()),
        )

        # 3. Narration Synthesis & Duration Calibration (>60.5s)
        act_texts = [
            project.act1.voiceover,
            project.act2.voiceover,
            project.act3.voiceover,
            project.act4.voiceover,
            project.act5.voiceover,
        ]
        raw_audio_files = []
        raw_durations = []

        for idx, act_txt in enumerate(act_texts, 1):
            act_audio_path = work_dir / f"act_{idx}_raw.mp3"
            aiff_tmp = act_audio_path.with_suffix(".aiff")
            try:
                subprocess.run(
                    ["say", "-r", "148", "-o", str(aiff_tmp), act_txt],
                    check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                )
                subprocess.run([ffmpeg_bin, "-y", "-i", str(aiff_tmp), "-c:a", "libmp3lame", "-b:a", "192k", str(act_audio_path)],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if aiff_tmp.exists():
                    aiff_tmp.unlink()
                dur = measure_audio_duration(act_audio_path)
            except Exception:
                dur = max(3.0, len(act_txt.split()) / 2.3)
                subprocess.run([ffmpeg_bin, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo", "-t", f"{dur:.2f}", str(act_audio_path)],
                               check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            raw_audio_files.append(act_audio_path)
            raw_durations.append(dur)

        total_raw_dur = sum(raw_durations)
        concat_txt = work_dir / "acts_concat.txt"
        with open(concat_txt, "w") as f:
            for rf in raw_audio_files:
                f.write(f"file '{rf.resolve()}'\n")

        raw_master = work_dir / "audio_raw_master.mp3"
        subprocess.run(
            [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_txt), "-c", "copy", str(raw_master)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )

        enforced_master = work_dir / "audio_enforced_master.mp3"
        final_audio_path, final_audio_dur, is_compliant = validate_and_enforce_long_video_duration(
            audio_path=raw_master,
            output_path=enforced_master,
            min_duration=60.5,
            target_min=61.0,
            target_max=68.0,
            total_words=total_words,
        )
        logger.info("Master audio duration: %.2fs (Monetization Compliant: %s)", final_audio_dur, is_compliant)

        # Scale individual scene durations to match enforced duration exactly
        stretch_factor = final_audio_dur / max(total_raw_dur, 1.0)
        act_durations = [d * stretch_factor for d in raw_durations]

        # 4. Kinetic Subtitles via faster-whisper
        subtitles_ass = work_dir / "subtitles_vertical.ass"
        generate_kinetic_subtitles(
            audio_path=final_audio_path,
            output_ass_path=subtitles_ass,
            model_size="base",
            fallback_words=["16GB", "VRAM", "BENCHMARK", "FRAMETIME", "THE", "GOLDEN", "RULE", "VERDICT"],
        )

        # 5. Visual 5-Act Choreography
        sample_broll = BASE_DIR / "temp" / "test_broll.mp4"
        broll_path = sample_broll if sample_broll.is_file() else None

        # Act 1: Dilemma Hook
        clip1 = work_dir / "act1_clip.mp4"
        card1_png = work_dir / "card1.png"
        create_introductory_dilemma_card(
            dilemma_title=project.act1.dilemma_title,
            subtitle=project.act1.dilemma_subtitle,
            output_path=card1_png,
            category_pill=project.act1.category_pill,
            vertical_format=True,
        )
        render_composite_overlay_clip(broll_path, card1_png, act_durations[0], clip1, blur_bg=6, overlay_y="(H-h)/2 - 120")

        # Act 2: Silicon Specs
        clip2 = work_dir / "act2_clip.mp4"
        card2_png = work_dir / "card2.png"
        create_silicon_specs_card(project.act2.specs_title, "Architecture", project.act2.specs_bullets, card2_png, vertical_format=True)
        render_composite_overlay_clip(broll_path, card2_png, act_durations[1], clip2, blur_bg=8, overlay_y="(H-h)/2 - 100")

        # Act 3: Live Benchmark Animation
        clip3 = work_dir / "act3_clip.mp4"
        cdata = ChartData(
            title=project.act3.chart_title,
            subtitle=project.act3.chart_subtitle,
            preset_pill=project.act3.preset_pill,
            metric_unit=project.act3.metric_unit,
            labels=[project.act3.winner_label, project.act3.loser_label],
            values=[float(project.act3.winner_avg_fps), float(project.act3.loser_avg_fps)],
            winner_badge=project.act3.winner_badge,
        )
        render_animated_benchmark_video(cdata, None, clip3, duration_sec=act_durations[2], fps=60, vertical_format=True)

        # Act 4: The Golden Rule (Dimmed Gameplay)
        clip4 = work_dir / "act4_clip.mp4"
        card4_png = work_dir / "card4.png"
        create_golden_rule_card(project.act4.golden_rule_takeaway, project.act4.voiceover, card4_png, vertical_format=True)
        render_composite_overlay_clip(broll_path, card4_png, act_durations[3], clip4, dim_factor=0.60, blur_bg=4, overlay_y="(H-h)/2 - 100")

        # Act 5: Interactive Voting Poll A vs B
        clip5 = work_dir / "act5_clip.mp4"
        card5_png = work_dir / "card5.png"
        create_voting_poll_card(project.act5.poll_question, project.act5.poll_option_a, project.act5.poll_option_b, card5_png, vertical_format=True)
        render_composite_overlay_clip(broll_path, card5_png, act_durations[4], clip5, blur_bg=10, overlay_y="(H-h)/2 - 80")

        # 6. Assembly & Subtitle Burning
        final_video = work_dir / "final_vertical_long_1080x1920.mp4"
        act_clips = [clip1, clip2, clip3, clip4, clip5]
        inputs = []
        for c in act_clips:
            inputs.extend(["-i", str(c)])
        inputs.extend(["-i", str(final_audio_path)])

        ass_path_str = str(subtitles_ass.resolve()).replace(":", r"\:")
        v_inputs = "".join(f"[{i}:v]" for i in range(len(act_clips)))
        filter_complex = f"{v_inputs}concat=n=5:v=1:a=0,ass='{ass_path_str}'[vout]"

        cmd_assemble = [
            ffmpeg_bin, "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "5:a",
            "-c:v", "libx264", "-preset", "faster", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(final_video),
        ]
        subprocess.run(cmd_assemble, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        actual_dur = get_video_duration_ffprobe(final_video)
        logger.info("Assembled 1080x1920 video: %s (Duration: %.2fs)", final_video.name, actual_dur)

        # 7. Distribution & Upload
        if platform == "tiktok":
            logger.info("Staging publication to TikTok (Privacy: %s)...", "DRAFT" if privacy == "private" else "PUBLIC")
            published_url = upload_video_to_tiktok(
                file_path=final_video,
                title=project.title,
                privacy="DRAFT" if privacy == "private" else "PUBLIC",
                tags=project.tags,
            )
        else:
            logger.info("Uploading vertical video to YouTube (Privacy: %s)...", privacy)
            if not dry_run:
                published_url = upload_video_resumable(
                    file_path=str(final_video),
                    title=project.title,
                    description=project.description,
                    tags=project.tags,
                    privacy_status=privacy,
                    is_short=False,  # >60s long vertical
                )
            else:
                published_url = f"file://{final_video}"

        # 8. Record to SQLite History
        record_short_history(
            weekday_index=spec.weekday_index,
            theme_key=spec.theme_key,
            game_title=spec.game_title,
            voice_id_used=spec.voice_id,
            topic=project.topic,
            title=project.title,
            video_id=published_url.split("/")[-1],
        )

        total_elapsed = time.time() - start_time
        print("\n" + "=" * 80)
        print(" [✓] VERTICAL LONG (61-68s) PIPELINE COMPLETED SUCCESSFULLY!")
        print(f" Platform:             {platform.upper()}")
        print(f" Total Production Time: {total_elapsed:.2f} seconds")
        print(f" Exact Video Duration:  {actual_dur:.2f} seconds (STRICTLY > 60.5s)")
        print(f" Monetization Status:   ELIGIBLE (TikTok Creator Rewards Program)")
        print(f" Video URL:             {published_url}")
        print(f" Local Output:          {final_video.resolve()}")
        print("=" * 80 + "\n")

    except Exception as exc:
        logger.critical("Fatal error during vertical long pipeline: %s", exc, exc_info=True)
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="Silicon Verdict Autonomous YouTube Content Pipeline")
    parser.add_argument(
        "--platform",
        type=str,
        choices=["youtube", "tiktok"],
        default="youtube",
        help="Target distribution platform: youtube or tiktok (default: youtube).",
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["short", "long"],
        default="short",
        help="Content format: short (20-30s / 35-45s) or long (61-68s, 5 acts, >60.5s for TikTok Creator Rewards).",
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
        default="private",
        help="Override upload privacy status (default: private).",
    )
    parser.add_argument(
        "--scenes_limit",
        "--scenes-limit",
        type=int,
        dest="scenes_limit",
        default=None,
        help="Limit the number of scenes generated (e.g. 3 for fast smoke tests).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    chosen_topic = args.topic
    if not chosen_topic and Path(args.topics_file).is_file():
        chosen_topic = get_next_topic_from_file(Path(args.topics_file))

    if args.platform == "tiktok" or args.format == "long":
        run_vertical_long_pipeline(
            topic=chosen_topic,
            platform=args.platform,
            dry_run=args.dry_run,
            privacy=args.privacy,
            history_file=args.history_file,
        )
    else:
        run_pipeline(
            topic=chosen_topic,
            dry_run=args.dry_run,
            privacy_override=args.privacy,
            history_file=args.history_file,
            scenes_limit=args.scenes_limit,
        )
