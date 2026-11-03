#!/usr/bin/env python3
"""Standalone test script to validate YouTube Data API v3 authentication and video upload.

Generates a synthetic 5-second test video with FFmpeg and uploads it as 'private'
to confirm that OAuth credentials and auto-refresh mechanisms function properly.
"""
import logging
import os
import subprocess
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.youtube import YouTubeService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("test_upload")


def generate_synthetic_test_video(output_path: Path) -> Path:
    """Creates a 5-second 1080p synthetic MP4 video using FFmpeg lavfi filters."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    logger.info("Generating 5-second synthetic test video via FFmpeg: %s", output_path)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "color=c=0x0a0d12:s=1920x1080:r=30",
        "-f", "lavfi", "-i", "sine=frequency=1000:sample_rate=48000",
        "-t", "5",
        "-vf", "drawtext=text='SILICON VERDICT TEST':fontcolor=0x00f0ff:fontsize=72:x=(w-text_w)/2:y=(h-text_h)/2",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(output_path),
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        logger.info("Synthetic video generated successfully (size: %.2f KB)", output_path.stat().st_size / 1024)
        return output_path
    except subprocess.CalledProcessError as exc:
        logger.error("FFmpeg error generating test video: %s", exc.stderr)
        raise RuntimeError(f"FFmpeg failed: {exc.stderr[-300:]}") from exc


def run_test():
    logger.info("=== Starting YouTube Data API v3 Upload Verification ===")

    test_video_path = Path("/tmp/silicon_test_5s.mp4")

    try:
        # Step 1: Generate small sample clip
        generate_synthetic_test_video(test_video_path)

        # Step 2: Initialize YouTube Service & verify authentication
        yt_service = YouTubeService()
        logger.info("Testing client authentication and token refresh...")
        client = yt_service.get_authenticated_client()
        logger.info("Successfully established connection to YouTube API service.")

        # Step 3: Execute resumable upload in 'private' state
        logger.info("Dispatching test video upload (privacy: 'private')...")
        video_url = yt_service.upload_video(
            file_path=str(test_video_path),
            title="[TEST] Silicon Verdict Pipeline Check",
            description=(
                "Autonomous verification upload for the Silicon Verdict rendering and upload pipeline.\n"
                "This video is private and used purely to validate API quota and OAuth credentials."
            ),
            tags=["SiliconVerdict", "Test", "BenchmarkTelemetry", "Hardware"],
            privacy_status="private",
            is_short=False,
        )

        video_id = video_url.split("/")[-1]

        logger.info("==================================================================")
        logger.info(" [✓] YOUTUBE UPLOAD TEST COMPLETED SUCCESSFULLY!")
        logger.info(" Video ID:   %s", video_id)
        logger.info(" Video URL:  %s", video_url)
        logger.info(" Privacy:    private (Safe - invisible to public audience)")
        logger.info(" Token File: %s", yt_service.token_file.resolve())
        logger.info("==================================================================")

    except FileNotFoundError as fnf:
        logger.error("Missing token error: %s", fnf)
        sys.exit(1)
    except PermissionError as pe:
        logger.error("OAuth permission error: %s", pe)
        sys.exit(1)
    except Exception as exc:
        logger.critical("Unexpected error during test upload: %s", exc, exc_info=True)
        sys.exit(1)
    finally:
        if test_video_path.exists():
            test_video_path.unlink()
            logger.info("Temporary test clip cleaned from %s", test_video_path)


if __name__ == "__main__":
    run_test()
