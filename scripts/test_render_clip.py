#!/usr/bin/env python3
"""Offline visual & unit test script for the Apple Liquid Glass motion graphics & Shorts Safe Zone.

Usage:
    # Standard 16:9 Master Preview
    python scripts/test_render_clip.py

    # 9:16 Shorts Safe Zone Visual Debugging Test
    python scripts/test_render_clip.py --safezone
"""
import argparse
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure local venv binaries (FFmpeg/FFprobe) are prioritized in PATH
venv_bin = BASE_DIR / ".venv" / "bin"
if venv_bin.is_dir() and str(venv_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

from core.schemas import ChartData
from engine.charts import (
    generate_glass_whoosh_sfx,
    render_animated_benchmark_video,
    render_animated_cta_video,
    render_apple_liquid_glass_cta_frame,
    render_benchmark_chart,
)
from services.debug_overlay import (
    generate_shorts_safezone_template,
    overlay_safezone_on_video,
)
from services.subtitles import generate_kinetic_subtitles

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_render_clip")


def get_ffmpeg_bin() -> str:
    import shutil
    return shutil.which("ffmpeg") or str(Path(sys.executable).parent / "ffmpeg") or "ffmpeg"


def generate_dummy_audio(output_path: Path, duration_sec: float = 4.0) -> Path:
    """Generates an offline synthetic silent audio file with FFmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Generating %.1fs dummy silence audio at: %s", duration_sec, output_path)

    cmd = [
        get_ffmpeg_bin(), "-y",
        "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", f"{duration_sec:.2f}",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        str(output_path),
    ]

    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logger.error("FFmpeg error creating dummy audio:\n%s", result.stderr)
        raise RuntimeError(f"FFmpeg dummy audio generation failed: {result.stderr[-300:]}")

    return output_path


def generate_spoken_audio(
    output_path: Path,
    text: str = "Why 8GB VRAM is officially dead for modern gaming.",
) -> Path:
    """Generates offline spoken English audio via macOS speech engine + FFmpeg."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    aiff_tmp = output_path.with_suffix(".aiff")
    ffmpeg_bin = get_ffmpeg_bin()
    try:
        subprocess.run(
            ["say", "-o", str(aiff_tmp), text],
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
        logger.info("Spoken audio synthesized offline via macOS speech engine: %s", output_path)
        return output_path
    except Exception as e:
        logger.warning("Spoken voice synthesis fallback to dummy audio: %s", e)
        return generate_dummy_audio(output_path, duration_sec=4.0)


def main():
    parser = argparse.ArgumentParser(description="Apple Liquid Glass & Safe Zone Test Renderer")
    parser.add_argument(
        "--safezone",
        action="store_true",
        help="Render 9:16 vertical Short (1080x1920) with kinetic subtitles and safe zone debug mask",
    )
    args = parser.parse_args()

    t_start = time.time()
    logger.info("==================================================================")
    if args.safezone:
        logger.info("=== STARTING SHORTS SAFE ZONE & KINETIC SUBTITLES TEST (9:16) ===")
    else:
        logger.info("=== STARTING APPLE LIQUID GLASS MOTION GRAPHICS TEST (16:9) ======")
    logger.info("==================================================================")

    temp_dir = BASE_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Mock Benchmark Specification matching Apple UI guidelines
    # Winner: 16GB VRAM (112 FPS, +38% FASTER)
    # Runner-up: 8GB VRAM (81 FPS)
    mock_chart_data = ChartData(
        title="GAMING PERFORMANCE",
        subtitle="8GB vs 16GB VRAM",
        preset_pill="1080p ULTRA • CYBERPUNK 2077",
        metric_unit="FPS",
        labels=["16GB VRAM", "8GB VRAM"],
        values=[112.0, 81.0],
        winner_badge="+38% FASTER",
    )

    if args.safezone:
        # -------------------------------------------------------------
        # 9:16 VERTICAL SHORTS SAFE ZONE & MID-ROLL CTA PIPELINE
        # -------------------------------------------------------------
        audio_bench = temp_dir / "test_audio_bench.mp3"
        audio_cta = temp_dir / "test_audio_cta.mp3"
        sfx_whoosh = temp_dir / "test_cta_whoosh.mp3"
        audio_cta_mixed = temp_dir / "test_audio_cta_mixed.mp3"
        audio_master = temp_dir / "test_audio_master.mp3"
        subtitles_file = temp_dir / "subtitles_multi.ass"
        clip_bench = temp_dir / "test_clip1_bench.mp4"
        clip_cta = temp_dir / "test_clip2_cta.mp4"
        clean_video_file = temp_dir / "test_liquid_glass_vertical.mp4"
        safezone_video_file = temp_dir / "test_preview_safezone.mp4"
        test_frame_file = temp_dir / "test_frame_vertical.png"
        test_cta_frame_file = temp_dir / "test_cta_frame.png"
        template_file = BASE_DIR / "assets" / "shorts_safezone_template.png"
        ffmpeg_bin = get_ffmpeg_bin()

        # 1. Synthesize Audio for Benchmark and Mid-roll CTA
        t_audio = time.time()
        generate_spoken_audio(audio_bench, text="Sixteen gigabytes delivers thirty eight percent higher frame pacing over eight gigabytes.")
        generate_spoken_audio(audio_cta, text="If you are enjoying this breakdown and want daily hardware insights, subscribe to Silicon Verdict.")

        # Measure duration of benchmark audio
        cmd_dur = [
            ffmpeg_bin, "-i", str(audio_bench),
            "-show_entries", "format=duration", "-v", "quiet", "-of", "csv=p=0"
        ]
        res_dur = subprocess.run(cmd_dur, stdout=subprocess.PIPE, text=True)
        try:
            d_bench = float(res_dur.stdout.strip())
        except Exception:
            d_bench = 3.50

        # Calibrate CTA audio to strict 2.50s duration
        d_cta = 2.50
        audio_cta_timed = temp_dir / "test_audio_cta_timed.mp3"
        subprocess.run(
            [ffmpeg_bin, "-y", "-i", str(audio_cta), "-t", "2.50", "-c:a", "libmp3lame", str(audio_cta_timed)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )

        # Generate crystalline glass whoosh SFX and mix at -18 dB during card emergence
        generate_glass_whoosh_sfx(sfx_whoosh, duration_sec=0.5)
        subprocess.run(
            [
                ffmpeg_bin, "-y",
                "-i", str(audio_cta_timed),
                "-i", str(sfx_whoosh),
                "-filter_complex",
                "[1:a]volume=-18dB[sfx]; [0:a][sfx]amix=inputs=2:duration=first:dropout_transition=0[aout]",
                "-map", "[aout]",
                "-c:a", "libmp3lame",
                str(audio_cta_mixed),
            ],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )

        # Concat audio tracks
        concat_list = temp_dir / "test_audio_concat.txt"
        with open(concat_list, "w") as f:
            f.write(f"file '{audio_bench.resolve()}'\nfile '{audio_cta_mixed.resolve()}'\n")

        subprocess.run(
            [ffmpeg_bin, "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(audio_master)],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
        )
        logger.info("Spoken multi-scene audio ready in %.2fs (Bench: %.2fs | CTA: %.2fs)", time.time() - t_audio, d_bench, d_cta)

        # 2. Transcribe word-by-word with faster-whisper & generate ASS subtitles
        t_sub = time.time()
        generate_kinetic_subtitles(
            audio_path=audio_master,
            output_ass_path=subtitles_file,
            model_size="base",
            fallback_words=["16GB", "DELIVERS", "HIGHER", "FRAME", "PACING", "SUBSCRIBE", "TO", "SILICON", "VERDICT"],
        )
        logger.info("Kinetic subtitles generated in %.2fs: %s", time.time() - t_sub, subtitles_file.name)

        # 3. Render 1080x1920 Static Frames (Benchmark & CTA)
        render_benchmark_chart(
            chart_data=mock_chart_data,
            output_path=test_frame_file,
            vertical_format=True,
        )
        cta_frame = render_apple_liquid_glass_cta_frame(
            card_alpha=1.0, card_scale=1.0, pulse_glow=0.5, time_sec=1.0,
            headline_highlight="SUBSCRIBE", headline_rest="FOR DAILY VERDICTS",
            sub_text="Unfiltered PC Hardware Telemetry & Benchmarks", vertical_format=True,
        )
        cta_frame.convert("RGB").save(test_cta_frame_file)

        # 4. Render 1080x1920 60fps Motion Video Clips
        t_vid = time.time()
        logger.info("Encoding Scene 1: Apple Liquid Glass Benchmark (%.2fs)...", d_bench)
        render_animated_benchmark_video(
            chart_data=mock_chart_data,
            audio_path=None,
            output_video_path=clip_bench,
            duration_sec=d_bench,
            fps=60,
            vertical_format=True,
            subtitles_ass_path=None,
        )

        logger.info("Encoding Scene 2: Apple Liquid Glass Mid-Roll CTA (%.2fs)...", d_cta)
        render_animated_cta_video(
            audio_path=None,
            output_video_path=clip_cta,
            duration_sec=d_cta,
            fps=60,
            vertical_format=True,
            subtitles_ass_path=None,
            headline_highlight="SUBSCRIBE",
            headline_rest="FOR DAILY VERDICTS",
            sub_text="Unfiltered PC Hardware Telemetry & Benchmarks",
        )

        # 5. Assemble Multi-scene Video with Subtitles Burned In
        logger.info("Assembling multi-scene sequence & burning ASS kinetic subtitles...")
        ass_path_str = str(subtitles_file.resolve()).replace(":", r"\:")
        filter_complex = f"[0:v][1:v]concat=n=2:v=1:a=0,ass='{ass_path_str}'[vout]"
        cmd_assemble = [
            ffmpeg_bin, "-y",
            "-i", str(clip_bench),
            "-i", str(clip_cta),
            "-i", str(audio_master),
            "-filter_complex", filter_complex,
            "-map", "[vout]",
            "-map", "2:a",
            "-c:v", "libx264", "-preset", "faster", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-shortest",
            str(clean_video_file),
        ]
        subprocess.run(cmd_assemble, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        logger.info("Clean multi-scene video encoded in %.2fs (Size: %.2f MB)", time.time() - t_vid, clean_video_file.stat().st_size / (1024 * 1024))

        # 6. Generate Safe Zone Template & Overlay Mask onto Video
        t_overlay = time.time()
        generate_shorts_safezone_template(template_file)
        overlay_safezone_on_video(
            input_video_path=clean_video_file,
            output_video_path=safezone_video_file,
            template_path=template_file,
        )
        logger.info("Safe zone overlay merged in %.2fs: %s", time.time() - t_overlay, safezone_video_file.name)

        total_time = time.time() - t_start
        total_clip_duration = d_bench + d_cta

        print("\n" + "=" * 76)
        print(" [✓] SHORTS SAFE ZONE & MID-ROLL CTA TEST COMPLETED SUCCESSFULLY!")
        print(f" Total Elapsed Time:     {total_time:.2f} seconds")
        print("-" * 76)
        print(f" 🎯 Safezone Video:      {safezone_video_file.resolve()}")
        print(f" 🎬 Clean 9:16 Video:     {clean_video_file.resolve()}")
        print(f" 📝 Kinetic ASS Track:   {subtitles_file.resolve()}")
        print(f" 🖼️ Benchmark Frame:     {test_frame_file.resolve()}")
        print(f" 🔔 CTA Glass Master:    {test_cta_frame_file.resolve()}")
        print(f" 🛡️ Safezone Mask:       {template_file.resolve()}")
        print(f" ⏱️ Benchmark Duration:  {d_bench:.2f}s")
        print(f" 🔔 Mid-Roll CTA Length: {d_cta:.2f}s (Strict 2.50s)")
        print(f" 📊 Full Video Duration: {total_clip_duration:.2f}s (1080x1920 @ 60fps | {int(total_clip_duration * 60)} Frames)")
        print("=" * 76 + "\n")

    else:
        # -------------------------------------------------------------
        # 16:9 HORIZONTAL BENCHMARK PIPELINE
        # -------------------------------------------------------------
        dummy_audio_file = temp_dir / "dummy_silence.mp3"
        test_frame_file = temp_dir / "test_frame.png"
        test_video_file = temp_dir / "test_liquid_glass_preview.mp4"

        # 1. Generate Synthetic 4.0s Audio Dummy
        t_audio_start = time.time()
        generate_dummy_audio(dummy_audio_file, duration_sec=4.0)

        # 2. Render High-Resolution Static Glass Master Frame (1920x1080)
        t_frame_start = time.time()
        render_benchmark_chart(
            chart_data=mock_chart_data,
            output_path=test_frame_file,
            vertical_format=False,
        )

        # 3. Render 1080p 60fps Motion Graphics Video (4.0s, 240 frames animated)
        t_video_start = time.time()
        render_animated_benchmark_video(
            chart_data=mock_chart_data,
            audio_path=dummy_audio_file,
            output_video_path=test_video_file,
            duration_sec=4.0,
            fps=60,
            vertical_format=False,
        )

        total_time = time.time() - t_start

        print("\n" + "=" * 76)
        print(" [✓] APPLE LIQUID GLASS MOTION TEST COMPLETED SUCCESSFULLY!")
        print(f" Total Elapsed Time:  {total_time:.2f} seconds")
        print("-" * 76)
        print(f" 🖼️ Static Frame:    {test_frame_file.resolve()}")
        print(f" 🎬 1080p60 Video:    {test_video_file.resolve()}")
        print(" 📊 Video Resolution: 1920x1080 @ 60fps (Duration: 4.0s | 240 Animated Frames)")
        print("=" * 76 + "\n")


if __name__ == "__main__":
    main()
