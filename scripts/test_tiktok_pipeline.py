#!/usr/bin/env python3
"""End-to-End Test and Validation Pipeline for TikTok Creator Rewards Long Videos (>60s: 61-68s).

Validates the full 5-act vertical production workflow:
1. Thematic matrix & game pool selection (core/pillars.py)
2. Round-Robin ElevenLabs voice rotation (services/voice.py)
3. 5-block script specification (~145-165 words, core/generator.py)
4. Strict >60.5s duration calibration & audio mastering (services/voice.py)
5. Word-by-word synchronized kinetic subtitles (faster-whisper, services/subtitles.py)
6. 5-act visual timeline choreography (1080x1920 @ 60 FPS, engine/renderer.py & engine/charts.py):
   - Act 1 (00:00-00:05): Real gameplay + Apple Liquid Glass Dilemma Card
   - Act 2 (00:05-00:20): Silicon macro B-roll + Architectural Specs Card
   - Act 3 (00:20-00:45): Fluid mesh + Live animated Apple Liquid Glass benchmark chart
   - Act 4 (00:45-00:58): Dimmed gameplay + 'THE GOLDEN RULE' purchasing card
   - Act 5 (00:58-00:65): Interactive Community Voting Poll Card (A vs B)
7. Safe Zone verification & automated monetization assertions
8. TikTok staging via services/tiktok.py
"""
import argparse
import logging
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure local venv binaries (FFmpeg/FFprobe) are prioritized in PATH
venv_bin = BASE_DIR / ".venv" / "bin"
if venv_bin.is_dir() and str(venv_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

from core.generator import (
    DailyShortSpec,
    generate_tiktok_long_plan,
    get_emergency_tiktok_long_project,
    select_daily_short_spec,
)
from core.schemas import ChartData, TikTokLongProject
from engine.charts import (
    render_animated_benchmark_video,
)
from engine.renderer import (
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
from services.subtitles import generate_kinetic_subtitles
from services.tiktok import (
    get_video_duration_ffprobe,
    upload_video_to_tiktok,
    validate_tiktok_creator_rewards_eligibility,
)
from services.voice import (
    get_ffmpeg_bin,
    measure_audio_duration,
    validate_and_enforce_long_video_duration,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("test_tiktok_pipeline")


def synthesize_spoken_act(text: str, output_path: Path, words_per_minute: int = 150) -> float:
    """Synthesizes speech for an act via macOS 'say' (calibrated rate) or ElevenLabs if online."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    aiff_tmp = output_path.with_suffix(".aiff")
    ffmpeg_bin = get_ffmpeg_bin()

    try:
        subprocess.run(
            ["say", "-r", str(words_per_minute), "-o", str(aiff_tmp), text],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        cmd = [
            ffmpeg_bin, "-y",
            "-i", str(aiff_tmp),
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if aiff_tmp.exists():
            aiff_tmp.unlink()
        dur = measure_audio_duration(output_path)
        return dur
    except Exception as exc:
        logger.warning("Spoken synthesis fallback to silence for text: %s (%s)", text[:30], exc)
        duration_est = max(3.0, len(text.split()) / 2.3)
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
            "-t", f"{duration_est:.2f}",
            "-c:a", "libmp3lame",
            str(output_path),
        ]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return duration_est


def generate_dark_tech_synth_music(output_path: Path, duration_sec: float) -> Path:
    """Generates an atmospheric dark tech synth ambient backing track via FFmpeg audio synthesis."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_bin()
    filter_graph = (
        f"anoisesrc=c=pink:r=44100:a=0.012,lowpass=f=200[noise];"
        f"sine=f=55:r=44100:d={duration_sec:.2f}[sub];"
        f"sine=f=110:r=44100:d={duration_sec:.2f}[mid];"
        f"[sub][mid]amix=inputs=2:dropout_transition=2[syn];"
        f"[syn]volume=0.07,chorus=0.7:0.9:55:0.4:0.25:2[pad];"
        f"[noise][pad]amix=inputs=2:dropout_transition=2,volume=0.14[out]"
    )
    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi",
        "-i", filter_graph,
        "-t", f"{duration_sec:.2f}",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Test and Verify TikTok Creator Rewards 61-68s Long Video Pipeline")
    parser.add_argument("--topic", type=str, default=None, help="Optional topic override")
    parser.add_argument("--safezone", action="store_true", default=True, help="Apply Safe Zone template overlay mask")
    parser.add_argument("--dry-run", action="store_true", help="Skip remote API calls")
    args = parser.parse_args()

    t_start = time.time()
    logger.info("==================================================================")
    logger.info("=== STARTING TIKTOK CREATOR REWARDS (61-68s) VERIFICATION PIPELINE ===")
    logger.info(" Target Format:        1080x1920 @ 60 FPS")
    logger.info(" Monetization Floor:   Strictly > 60.5 seconds (Target: 61.0s - 68.0s)")
    logger.info(" Narrative Blueprint:  5-Act Empirical Technical Timeline")
    logger.info("==================================================================")

    temp_dir = BASE_DIR / "temp" / "test_tiktok_run"
    temp_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = get_ffmpeg_bin()

    # -------------------------------------------------------------
    # STEP 1: Thematic Matrix & Voice Rotation
    # -------------------------------------------------------------
    t1 = time.time()
    current_weekday = datetime.now().weekday()
    spec: DailyShortSpec = select_daily_short_spec(weekday_index=current_weekday)
    logger.info(
        "Pillar: %s (%s) | %s: '%s' | Benchmark Game: '%s' | Voice: %s",
        spec.day_name, spec.pillar_title, spec.theme_key, spec.theme_description, spec.game_title, spec.voice_label
    )

    # -------------------------------------------------------------
    # STEP 2: 5-Block Script Generation (~145-165 words)
    # -------------------------------------------------------------
    try:
        project: TikTokLongProject = generate_tiktok_long_plan(topic=args.topic, spec=spec)
    except Exception as exc:
        logger.warning("Gemini plan generation unavailable (%s). Deploying deterministic 5-block plan.", exc)
        project = get_emergency_tiktok_long_project(topic=args.topic, spec=spec)

    total_words = project.get_total_words()
    logger.info(
        "Script Blueprint validated: %d total words (Act 1: %dw | Act 2: %dw | Act 3: %dw | Act 4: %dw | Act 5: %dw)",
        total_words,
        len(project.act1.voiceover.split()),
        len(project.act2.voiceover.split()),
        len(project.act3.voiceover.split()),
        len(project.act4.voiceover.split()),
        len(project.act5.voiceover.split()),
    )
    assert total_words >= 140, f"Total word count ({total_words}) is below 140 threshold for >60s monetization!"

    # -------------------------------------------------------------
    # STEP 3: Voice Narration & Strict Duration Calibration (>60.5s)
    # -------------------------------------------------------------
    t_audio = time.time()
    logger.info("--- Step 3: Synthesizing 5-Act Narration & Calibrating Duration ---")
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
        act_audio_path = temp_dir / f"act_{idx}_raw.mp3"
        # Natural technical narration pace ~145-155 WPM
        dur = synthesize_spoken_act(act_txt, act_audio_path, words_per_minute=148)
        raw_audio_files.append(act_audio_path)
        raw_durations.append(dur)
        logger.info("  • Act %d Audio: %.2fs (%d words)", idx, dur, len(act_txt.split()))

    total_raw_dur = sum(raw_durations)
    logger.info("Raw aggregate narration duration: %.2fs", total_raw_dur)

    # Concat raw acts
    raw_concat_txt = temp_dir / "acts_concat_raw.txt"
    with open(raw_concat_txt, "w") as f:
        for rf in raw_audio_files:
            f.write(f"file '{rf.resolve()}'\n")

    raw_master_audio = temp_dir / "audio_master_raw.mp3"
    subprocess.run(
        [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(raw_concat_txt), "-c", "copy", str(raw_master_audio)],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )

    # Enforce strict >60.5s duration using services/voice.py
    enforced_master_audio = temp_dir / "audio_master_enforced.mp3"
    final_audio_path, final_audio_dur, is_compliant = validate_and_enforce_long_video_duration(
        audio_path=raw_master_audio,
        output_path=enforced_master_audio,
        min_duration=60.5,
        target_min=61.0,
        target_max=68.0,
        total_words=total_words,
    )
    assert is_compliant, f"Audio duration {final_audio_dur:.2f}s failed >60.5s TikTok threshold!"
    assert final_audio_dur >= 60.5, f"Audio duration {final_audio_dur:.2f}s strictly below 60.5s!"
    logger.info("Audio duration strictly calibrated: %.2fs (Monetization Compliant: %s)", final_audio_dur, is_compliant)

    # Ratio factor to align visual scene durations
    stretch_factor = final_audio_dur / max(total_raw_dur, 1.0)
    act_durations = [d * stretch_factor for d in raw_durations]
    logger.info("Calibrated scene durations: %s", [f"{d:.2f}s" for d in act_durations])

    # Mix dark tech synth background music at -22 dB
    music_file = temp_dir / "dark_tech_synth_music.mp3"
    generate_dark_tech_synth_music(music_file, duration_sec=final_audio_dur + 0.5)

    mixed_master_audio = temp_dir / "audio_master_mixed.mp3"
    subprocess.run(
        [
            ffmpeg_bin, "-y",
            "-i", str(final_audio_path),
            "-i", str(music_file),
            "-filter_complex",
            "[1:a]volume=-22dB[bg]; [0:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map", "[aout]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            str(mixed_master_audio),
        ],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )
    logger.info("Audio mastering complete with background synth music: %s", mixed_master_audio.name)

    # -------------------------------------------------------------
    # STEP 4: Kinetic Word-by-Word Subtitles (faster-whisper)
    # -------------------------------------------------------------
    t_sub = time.time()
    logger.info("--- Step 4: Generating Synchronized Kinetic Subtitles with Whisper ---")
    subtitles_ass = temp_dir / "subtitles_tiktok_safezone.ass"
    generate_kinetic_subtitles(
        audio_path=mixed_master_audio,
        output_ass_path=subtitles_ass,
        model_size="base",
        fallback_words=["16GB", "VRAM", "BENCHMARK", "FRAMETIME", "THE", "GOLDEN", "RULE", "VERDICT"],
    )
    logger.info("Kinetic ASS subtitles ready in %.2fs: %s", time.time() - t_sub, subtitles_ass.name)

    # -------------------------------------------------------------
    # STEP 5: Visual Timeline Choreography (5 Acts, 1080x1920 @ 60 FPS)
    # -------------------------------------------------------------
    t_vis = time.time()
    logger.info("--- Step 5: Rendering 5-Act Visual Choreography (1080x1920 @ 60 FPS) ---")

    # Locate available sample B-roll or generate dynamic dark tech canvas
    sample_broll = BASE_DIR / "temp" / "test_broll.mp4"
    broll_path = sample_broll if sample_broll.is_file() else None

    # Act 1: Dilemma Card on full-screen gameplay
    clip1 = temp_dir / "act1_gameplay_dilemma.mp4"
    card1_png = temp_dir / "card1_dilemma.png"
    create_introductory_dilemma_card(
        dilemma_title=project.act1.dilemma_title,
        subtitle=project.act1.dilemma_subtitle,
        output_path=card1_png,
        category_pill=project.act1.category_pill,
        vertical_format=True,
    )
    render_composite_overlay_clip(
        bg_video_path=broll_path,
        overlay_png_path=card1_png,
        duration_sec=act_durations[0],
        output_clip_path=clip1,
        dim_factor=1.0,
        blur_bg=6,
        overlay_y="(H-h)/2 - 120",
    )
    logger.info("  • Act 1 Rendered: Dilemma Hook (%.2fs)", act_durations[0])

    # Act 2: Silicon Specs Card on macro silicon video
    clip2 = temp_dir / "act2_silicon_specs.mp4"
    card2_png = temp_dir / "card2_specs.png"
    create_silicon_specs_card(
        title=project.act2.specs_title,
        subtitle="Low-Level Architecture",
        bullets=project.act2.specs_bullets,
        output_path=card2_png,
        vertical_format=True,
    )
    render_composite_overlay_clip(
        bg_video_path=broll_path,
        overlay_png_path=card2_png,
        duration_sec=act_durations[1],
        output_clip_path=clip2,
        dim_factor=1.0,
        blur_bg=8,
        overlay_y="(H-h)/2 - 100",
    )
    logger.info("  • Act 2 Rendered: Silicon Specs (%.2fs)", act_durations[1])

    # Act 3: Live Animated Apple Liquid Glass Benchmark Chart (60 FPS)
    clip3 = temp_dir / "act3_benchmark_chart.mp4"
    chart_data = ChartData(
        title=project.act3.chart_title,
        subtitle=project.act3.chart_subtitle,
        preset_pill=project.act3.preset_pill,
        metric_unit=project.act3.metric_unit,
        labels=[project.act3.winner_label, project.act3.loser_label],
        values=[float(project.act3.winner_avg_fps), float(project.act3.loser_avg_fps)],
        winner_badge=project.act3.winner_badge,
    )
    render_animated_benchmark_video(
        chart_data=chart_data,
        audio_path=None,
        output_video_path=clip3,
        duration_sec=act_durations[2],
        fps=60,
        vertical_format=True,
        subtitles_ass_path=None,
    )
    logger.info("  • Act 3 Rendered: Animated Liquid Glass Benchmark (%.2fs)", act_durations[2])

    # Act 4: Dimmed gameplay + 'THE GOLDEN RULE' Purchasing Card
    clip4 = temp_dir / "act4_golden_rule.mp4"
    card4_png = temp_dir / "card4_golden_rule.png"
    create_golden_rule_card(
        title=project.act4.golden_rule_takeaway,
        takeaway=project.act4.voiceover,
        output_path=card4_png,
        vertical_format=True,
    )
    render_composite_overlay_clip(
        bg_video_path=broll_path,
        overlay_png_path=card4_png,
        duration_sec=act_durations[3],
        output_clip_path=clip4,
        dim_factor=0.60,  # 40% dimmed gameplay
        blur_bg=4,
        overlay_y="(H-h)/2 - 100",
    )
    logger.info("  • Act 4 Rendered: The Golden Rule (%.2fs)", act_durations[3])

    # Act 5: Interactive Voting Poll Card (A vs B)
    clip5 = temp_dir / "act5_voting_poll.mp4"
    card5_png = temp_dir / "card5_poll.png"
    create_voting_poll_card(
        question=project.act5.poll_question,
        option_a=project.act5.poll_option_a,
        option_b=project.act5.poll_option_b,
        output_path=card5_png,
        vertical_format=True,
    )
    render_composite_overlay_clip(
        bg_video_path=broll_path,
        overlay_png_path=card5_png,
        duration_sec=act_durations[4],
        output_clip_path=clip5,
        dim_factor=1.0,
        blur_bg=10,
        overlay_y="(H-h)/2 - 80",
    )
    logger.info("  • Act 5 Rendered: Community Voting Poll (%.2fs)", act_durations[4])
    logger.info("Visual rendering completed in %.2fs", time.time() - t_vis)

    # -------------------------------------------------------------
    # STEP 6: Assembly & Continuous Subtitle Burning
    # -------------------------------------------------------------
    t_asm = time.time()
    clean_tiktok_output = BASE_DIR / "temp" / "test_tiktok_65s.mp4"
    clean_tiktok_output.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Assembling 5-act sequence into %s...", clean_tiktok_output.name)

    act_clips = [clip1, clip2, clip3, clip4, clip5]
    inputs = []
    for c in act_clips:
        inputs.extend(["-i", str(c)])
    inputs.extend(["-i", str(mixed_master_audio)])

    ass_path_str = str(subtitles_ass.resolve()).replace(":", r"\:")
    v_inputs = "".join(f"[{i}:v]" for i in range(len(act_clips)))
    filter_complex = f"{v_inputs}concat=n=5:v=1:a=0,ass='{ass_path_str}'[vout]"

    cmd_assemble = [
        ffmpeg_bin, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[vout]",
        "-map", "5:a",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(clean_tiktok_output),
    ]
    subprocess.run(cmd_assemble, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    logger.info("Clean 5-act TikTok video assembled in %.2fs (Size: %.2f MB)", time.time() - t_asm, clean_tiktok_output.stat().st_size / (1024 * 1024))

    # -------------------------------------------------------------
    # STEP 7: Safe Zone Overlay Mask
    # -------------------------------------------------------------
    safezone_tiktok_output = BASE_DIR / "temp" / "test_tiktok_65s_safezone.mp4"
    template_file = BASE_DIR / "assets" / "shorts_safezone_template.png"
    generate_shorts_safezone_template(template_file)
    overlay_safezone_on_video(
        input_video_path=clean_tiktok_output,
        output_video_path=safezone_tiktok_output,
        template_path=template_file,
    )
    logger.info("Safe Zone debug mask applied: %s", safezone_tiktok_output.name)

    # -------------------------------------------------------------
    # STEP 8: Rigorous Verification Assertions
    # -------------------------------------------------------------
    actual_duration = get_video_duration_ffprobe(clean_tiktok_output)
    logger.info("Final Video Duration: %.2f seconds", actual_duration)

    # Strict monetization assertion
    assert actual_duration >= 60.5, f"CRITICAL: Final video duration ({actual_duration:.2f}s) is < 60.5s! Disqualified for Creator Rewards."
    assert clean_tiktok_output.stat().st_size > 1024 * 1024, "CRITICAL: Video file size is unexpectedly small!"
    assert safezone_tiktok_output.is_file(), "Safezone output file missing!"

    # Verify eligibility and stage TikTok upload
    eligible = validate_tiktok_creator_rewards_eligibility(clean_tiktok_output, min_duration=60.5)
    assert eligible, "TikTok Creator Rewards validation returned False!"

    tiktok_url = upload_video_to_tiktok(
        file_path=clean_tiktok_output,
        title=project.title,
        privacy="DRAFT",
        tags=project.tags,
    )

    total_time = time.time() - t_start
    print("\n" + "=" * 80)
    print(" [✓] TIKTOK CREATOR REWARDS 5-ACT PIPELINE COMPLETED SUCCESSFULLY!")
    print(f" Total Production Time:     {total_time:.2f} seconds")
    print("-" * 80)
    print(f" 🎬 Master Clean Video:     {clean_tiktok_output.resolve()}")
    print(f" 🎯 Safezone Debug Video:   {safezone_tiktok_output.resolve()}")
    print(f" 📝 Kinetic ASS Subtitles:  {subtitles_ass.resolve()}")
    print(f" ⏱️ Exact Video Duration:   {actual_duration:.2f} seconds (STRICTLY > 60.5s)")
    print(" 💰 Monetization Status:    ELIGIBLE (TikTok Creator Rewards Program)")
    print(f" 📱 Staged TikTok URL:      {tiktok_url}")
    print(f" 🏷️ Title:                  {project.title}")
    print(f" 📊 Act 1: Dilemma Hook     {act_durations[0]:.2f}s | {project.act1.dilemma_title}")
    print(f" 📊 Act 2: Silicon Specs    {act_durations[1]:.2f}s | {project.act2.specs_title}")
    print(f" 📊 Act 3: Live Benchmark   {act_durations[2]:.2f}s | {project.act3.winner_label} ({project.act3.winner_avg_fps} FPS)")
    print(f" 📊 Act 4: The Golden Rule  {act_durations[3]:.2f}s | {project.act4.golden_rule_takeaway}")
    print(f" 📊 Act 5: Community Poll   {act_durations[4]:.2f}s | {project.act5.poll_question}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
