#!/usr/bin/env python3
"""
record_local_demo.py - Silicon Verdict TikTok Integration Automated Demo Recorder.
Records an end-to-end demo video showcasing TikTok Login Kit (scopes: user.info.basic,
video.upload, video.publish) and Content Posting API direct publishing.
Outputs: assets/tiktok_integration_demo.mp4 (H.264, 1920x1080, < 45 MB, 40-50s).
"""

import os
import sys
import time
import shutil
import subprocess
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent.parent
SERVER_SCRIPT = BASE_DIR / "scripts" / "demo_server.py"
OUTPUT_DIR = BASE_DIR / "assets"
FINAL_VIDEO_PATH = OUTPUT_DIR / "tiktok_integration_demo.mp4"
RECORDING_TMP_DIR = BASE_DIR / "temp" / "playwright_recording"
VENV_BIN = BASE_DIR / ".venv" / "bin"
FFMPEG_BIN = VENV_BIN / "ffmpeg" if (VENV_BIN / "ffmpeg").exists() else Path(shutil.which("ffmpeg") or "ffmpeg")
FFPROBE_BIN = VENV_BIN / "ffprobe" if (VENV_BIN / "ffprobe").exists() else Path(shutil.which("ffprobe") or "ffprobe")

DEMO_URL = "http://localhost:8080/"

def ensure_server_running():
    """Checks if demo_server is running on port 8080. If not, starts it."""
    try:
        with urllib.request.urlopen(DEMO_URL, timeout=1) as resp:
            if resp.status == 200:
                print("[*] Demo server is already running on http://localhost:8080/")
                return None
    except Exception:
        pass

    print("[*] Starting demo_server.py on http://localhost:8080/...")
    python_bin = sys.executable
    proc = subprocess.Popen([python_bin, str(SERVER_SCRIPT)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait for server to be responsive
    for _ in range(30):
        time.sleep(0.3)
        try:
            with urllib.request.urlopen(DEMO_URL, timeout=1) as resp:
                if resp.status == 200:
                    print("[✓] Demo server successfully started and responsive.")
                    return proc
        except Exception:
            continue
            
    raise RuntimeError("Failed to start demo_server.py on http://localhost:8080/")

def human_move_mouse(page, target_x, target_y, start_x=None, start_y=None, steps=30, duration=0.8):
    """Smoothly interpolates mouse movement across multiple points to trigger UI cursor."""
    page.mouse.move(target_x, target_y, steps=steps)
    time.sleep(duration)

def record_demo():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if RECORDING_TMP_DIR.exists():
        shutil.rmtree(RECORDING_TMP_DIR)
    RECORDING_TMP_DIR.mkdir(parents=True, exist_ok=True)

    server_proc = ensure_server_running()

    print("[*] Initializing Playwright Chromium browser recording at 1920x1080 30FPS...")
    t_start = time.time()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--hide-scrollbars",
                    "--force-device-scale-factor=1",
                    "--autoplay-policy=no-user-gesture-required"
                ]
            )

            context = browser.new_context(
                record_video_dir=str(RECORDING_TMP_DIR),
                record_video_size={"width": 1920, "height": 1080},
                viewport={"width": 1920, "height": 1080},
                device_scale_factor=1
            )

            page = context.new_page()
            t_record_start = time.time()
            
            # --- [00:00 - 00:08] Open Dashboard & Click "Connect with TikTok" ---
            print("[00:00 - 00:08] Navigating to dashboard and moving towards Connect button...")
            page.goto(DEMO_URL, wait_until="networkidle")
            time.sleep(1.2)

            # Move mouse smoothly to the "Connect with TikTok" button
            connect_btn = page.locator("#btn-connect-tiktok")
            box_connect = connect_btn.bounding_box()
            target_x = box_connect["x"] + box_connect["width"] / 2
            target_y = box_connect["y"] + box_connect["height"] / 2

            page.mouse.move(target_x, target_y, steps=35)
            time.sleep(1.2)  # Hover state visible to TikTok reviewer

            print("[*] Clicking 'Connect with TikTok' to trigger Login Kit consent...")
            connect_btn.click()
            time.sleep(1.0)

            # --- [00:08 - 00:18] TikTok OAuth Consent Screen & Scopes Inspection ---
            print("[00:08 - 00:18] Inspecting requested TikTok permissions in OAuth consent modal...")
            
            # Highlight Scope 1: user.info.basic
            scope1 = page.locator("#scope-card-1")
            box_s1 = scope1.bounding_box()
            page.mouse.move(box_s1["x"] + box_s1["width"] / 2, box_s1["y"] + box_s1["height"] / 2, steps=25)
            time.sleep(1.4)

            # Highlight Scope 2: video.upload
            scope2 = page.locator("#scope-card-2")
            box_s2 = scope2.bounding_box()
            page.mouse.move(box_s2["x"] + box_s2["width"] / 2, box_s2["y"] + box_s2["height"] / 2, steps=20)
            time.sleep(1.4)

            # Highlight Scope 3: video.publish
            scope3 = page.locator("#scope-card-3")
            box_s3 = scope3.bounding_box()
            page.mouse.move(box_s3["x"] + box_s3["width"] / 2, box_s3["y"] + box_s3["height"] / 2, steps=20)
            time.sleep(1.4)

            # Move to "Authorize / Grant Permissions" button
            auth_btn = page.locator("#btn-modal-authorize")
            box_auth = auth_btn.bounding_box()
            page.mouse.move(box_auth["x"] + box_auth["width"] / 2, box_auth["y"] + box_auth["height"] / 2, steps=20)
            time.sleep(1.0)

            print("[*] Clicking 'Authorize / Grant Permissions'...")
            auth_btn.click()
            time.sleep(1.0)

            # --- [00:18 - 00:28] Return to Dashboard, Connected State & Preview Playback ---
            print("[00:18 - 00:28] Account connected. Playing benchmark clip and filling title...")
            time.sleep(1.0)

            # Play video clip in preview player
            page.evaluate("() => document.getElementById('preview-video').play()")
            time.sleep(2.5)

            # Move to Title Input Field
            title_input = page.locator("#video-title-input")
            box_title = title_input.bounding_box()
            page.mouse.move(box_title["x"] + 150, box_title["y"] + box_title["height"] / 2, steps=25)
            time.sleep(0.4)
            title_input.click()

            # Clear and type text smoothly
            title_text = "PCIe 4.0 vs 5.0: The Benchmark Truth #hardware #techtok"
            title_input.fill("")
            title_input.type(title_text, delay=20)
            time.sleep(0.8)

            # Move to Privacy Select dropdown
            privacy_select = page.locator("#privacy-select")
            box_priv = privacy_select.bounding_box()
            page.mouse.move(box_priv["x"] + box_priv["width"] / 2, box_priv["y"] + box_priv["height"] / 2, steps=20)
            time.sleep(0.8)

            # --- [00:28 - 00:40] Trigger Direct Publish & Telemetry Console ---
            print("[00:28 - 00:40] Initiating Content Posting API dispatch and progress tracking...")
            publish_btn = page.locator("#btn-publish-tiktok")
            box_pub = publish_btn.bounding_box()
            page.mouse.move(box_pub["x"] + box_pub["width"] / 2, box_pub["y"] + box_pub["height"] / 2, steps=25)
            time.sleep(0.8)

            publish_btn.click()

            # Wait for upload progress and API telemetry to complete
            time.sleep(2.5)
            
            # Move mouse towards telemetry console to direct reviewer attention
            console_box = page.locator("#console-logs").bounding_box()
            page.mouse.move(console_box["x"] + 300, console_box["y"] + 80, steps=25)
            time.sleep(2.0)

            # Wait for the green success badge to be fully visible
            page.wait_for_selector("#success-alert.show", timeout=10000)
            success_box = page.locator("#success-alert").bounding_box()
            page.mouse.move(success_box["x"] + success_box["width"] / 2, success_box["y"] + success_box["height"] / 2, steps=20)

            # --- [00:40 - 00:45] Dynamic Verification Pause to target strictly 44-45 seconds ---
            elapsed_so_far = time.time() - t_record_start
            target_duration = 44.5
            final_pause = max(3.0, target_duration - elapsed_so_far)
            print(f"[00:40 - 00:45] Verification pause on published state ({final_pause:.2f}s, elapsed so far {elapsed_so_far:.2f}s)...")
            time.sleep(final_pause)

            # Close context to flush video to disk
            context.close()
            browser.close()

    finally:
        if server_proc:
            print("[*] Terminating background demo server...")
            server_proc.terminate()
            server_proc.wait()

    t_total = time.time() - t_start
    print(f"[*] Total session recording elapsed time: {t_total:.2f} seconds.")

    # Locate recorded video file
    recorded_files = list(RECORDING_TMP_DIR.glob("*.webm"))
    if not recorded_files:
        raise FileNotFoundError(f"No recorded .webm video found in {RECORDING_TMP_DIR}")
    
    raw_video = recorded_files[0]
    print(f"[✓] Playwright raw recording captured at: {raw_video}")

    # Process and compress with FFmpeg
    print(f"[*] Processing with FFmpeg ({FFMPEG_BIN})...")
    
    # We include a silent stereo audio stream (AAC 128k) to ensure the MP4 has both compliant H.264 video and AAC audio
    cmd = [
        str(FFMPEG_BIN),
        "-y",
        "-i", str(raw_video),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
        "-c:v", "libx264",
        "-preset", "slow",
        "-crf", "22",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        "-shortest",
        str(FINAL_VIDEO_PATH)
    ]

    print("[*] Running command:\n" + " ".join(cmd))
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        print("[!] FFmpeg error:", result.stderr)
        raise RuntimeError("FFmpeg encoding failed.")

    # Validate output file
    if not FINAL_VIDEO_PATH.exists():
        raise FileNotFoundError(f"Exported video not found at {FINAL_VIDEO_PATH}")

    file_size_bytes = FINAL_VIDEO_PATH.stat().st_size
    file_size_mb = file_size_bytes / (1024 * 1024)

    # Check duration with ffprobe
    probe_cmd = [
        str(FFPROBE_BIN),
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(FINAL_VIDEO_PATH)
    ]
    probe_res = subprocess.run(probe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    duration_str = probe_res.stdout.strip()
    duration_sec = float(duration_str) if duration_str else 0.0

    print("\n" + "="*60)
    print("DEMO VIDEO GENERATION RESULT:")
    print(f"  Path:     {FINAL_VIDEO_PATH}")
    print(f"  Duration: {duration_sec:.2f} seconds (Target: 40 - 50 seconds)")
    print(f"  Size:     {file_size_mb:.2f} MB (Limit: < 45 MB)")
    print(f"  Codecs:   H.264 (High) / AAC Stereo")
    print("="*60 + "\n")

    assert 40.0 <= duration_sec <= 50.0, f"Duration {duration_sec:.2f}s is outside 40-50s requirement!"
    assert file_size_mb < 45.0, f"File size {file_size_mb:.2f}MB exceeds 45 MB limit!"

    print("[✓] ALL TIKTOK DEVELOPER DEMO VIDEO REQUIREMENTS FULLY MET!")
    return str(FINAL_VIDEO_PATH), file_size_mb, duration_sec

if __name__ == "__main__":
    record_demo()
