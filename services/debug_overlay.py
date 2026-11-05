"""YouTube Shorts Safe Zone visual debugging overlay generator.

Generates an RGBA overlay template (1080x1920) mapping YouTube Shorts UI collision zones:
- Top Header Block: Y=0..200 (Profile, Search, Camera)
- Right Action Rail Block: X=900..1080, Y=850..1700 (Like, Dislike, Comments, Share, Remix)
- Bottom Metadata Block: Y=1440..1920 (Channel Name, Subscribe, Video Title, Audio Track)
- Usable Safe Zone: X=60..880, Y=220..1420 (Outlined in Electric Cyan)
"""
import logging
import subprocess
from pathlib import Path
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from engine.charts import resolve_system_font

logger = logging.getLogger(__name__)

DEFAULT_ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
DEFAULT_TEMPLATE_PATH = DEFAULT_ASSETS_DIR / "shorts_safezone_template.png"


def generate_shorts_safezone_template(output_path: Optional[Path] = None) -> Path:
    """Generates the 1080x1920 RGBA YouTube Shorts Safe Zone debug overlay template."""
    dest = Path(output_path) if output_path else DEFAULT_TEMPLATE_PATH
    dest.parent.mkdir(parents=True, exist_ok=True)

    W, H = 1080, 1920
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. Blocked Red Translucent Zones (rgba(255, 0, 0, 0.25) -> alpha 64)
    red_blocked_fill = (255, 0, 0, 64)
    red_border_stroke = (255, 50, 50, 180)

    # A) Top Header Zone (Y=0..200)
    draw.rectangle([0, 0, W, 200], fill=red_blocked_fill, outline=red_border_stroke, width=2)

    # B) Right Action Rail Zone (X=900..1080, Y=850..1700)
    draw.rectangle([900, 850, 1080, 1700], fill=red_blocked_fill, outline=red_border_stroke, width=2)

    # C) Bottom Metadata & UI Zone (Y=1440..1920)
    draw.rectangle([0, 1440, W, 1920], fill=red_blocked_fill, outline=red_border_stroke, width=2)

    # 2. Usable Safe Zone Outline (rgba(0, 242, 255, 0.8) -> alpha 204)
    # [X: 60..880, Y: 220..1420]
    cyan_safe_stroke = (0, 242, 255, 204)
    draw.rectangle([60, 220, 880, 1420], outline=cyan_safe_stroke, width=3)

    # 3. Informational HUD Labels for Quality Assurance
    try:
        font_hud = resolve_system_font(22, weight="bold")
        font_sub = resolve_system_font(18, weight="regular")
    except Exception:
        font_hud = ImageFont.load_default()
        font_sub = font_hud

    # Top zone label
    draw.text((W // 2, 100), "SHORTS UI • TOP HEADER (Y: 0 - 200)", font=font_hud, fill=(255, 120, 120, 230), anchor="mm")

    # Right rail label (vertical / stacked)
    draw.text((990, 880), "SHORTS", font=font_hud, fill=(255, 120, 120, 230), anchor="mm")
    draw.text((990, 915), "RIGHT", font=font_hud, fill=(255, 120, 120, 230), anchor="mm")
    draw.text((990, 950), "RAIL", font=font_hud, fill=(255, 120, 120, 230), anchor="mm")
    draw.text((990, 995), "(LIKE /", font=font_sub, fill=(255, 160, 160, 200), anchor="mm")
    draw.text((990, 1025), "COMMENT /", font=font_sub, fill=(255, 160, 160, 200), anchor="mm")
    draw.text((990, 1055), "SHARE)", font=font_sub, fill=(255, 160, 160, 200), anchor="mm")

    # Bottom zone label
    draw.text((W // 2, 1680), "SHORTS UI • TITLE / CHANNEL / AUDIO (Y: 1440 - 1920)", font=font_hud, fill=(255, 120, 120, 230), anchor="mm")

    # Safe zone corner labels
    draw.text((70, 230), "SAFE ZONE [60..880, 220..1420]", font=font_sub, fill=(0, 242, 255, 230), anchor="lt")
    draw.text((70, 370), "CARD REGION [Y: 360..1120]", font=font_sub, fill=(0, 200, 255, 180), anchor="lt")
    draw.text((70, 1270), "SUBTITLE REGION [Y: 1260..1420]", font=font_sub, fill=(0, 200, 255, 180), anchor="lt")

    img.save(dest, format="PNG")
    logger.info("Generated YouTube Shorts safe zone template: %s", dest)
    return dest


def overlay_safezone_on_video(
    input_video_path: Path,
    output_video_path: Path,
    template_path: Optional[Path] = None,
) -> Path:
    """Overlays the Shorts Safe Zone mask onto a vertical video via FFmpeg."""
    if template_path is None or not Path(template_path).exists():
        template_path = generate_shorts_safezone_template(template_path)

    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-i", str(input_video_path),
        "-i", str(template_path),
        "-filter_complex", "[0:v][1:v]overlay=0:0[v]",
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        str(output_video_path),
    ]

    logger.info("Applying Safe Zone overlay mask: %s -> %s", input_video_path.name, output_video_path.name)
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        logger.error("FFmpeg safezone overlay failed:\n%s", result.stderr)
        raise RuntimeError(f"FFmpeg safezone overlay failed: {result.stderr[-400:]}")

    return output_video_path
