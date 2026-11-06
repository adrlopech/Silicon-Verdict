import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, ImageDraw, ImageFilter

from config.settings import settings
from core.schemas import Scene, VideoProject
from engine.charts import (
    COLOR_TEXT_WHITE,
    fit_text,
    render_animated_benchmark_video,
    resolve_system_font,
)
from services.media import SceneMedia
from services.subtitles import generate_kinetic_subtitles
from services.tts import SceneAudio

logger = logging.getLogger(__name__)


@dataclass
class RenderedOutputs:
    """Paths to all generated video artifacts."""
    full_video_path: str
    shorts_paths: List[str]


def create_vision_pro_hud_pill(
    text: str,
    output_path: Path,
    vertical_format: bool = False,
) -> Path:
    """Renders a floating Apple Vision Pro-style HUD glass pill overlay."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    clean_text = text.strip().upper()

    font_size = 26 if vertical_format else 30
    font = resolve_system_font(font_size, weight="bold")

    bbox = font.getbbox(clean_text)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    dot_space = 28
    pad_x = 34
    pad_y = 15

    pill_w = text_w + dot_space + (pad_x * 2)
    pill_h = text_h + (pad_y * 2)
    radius = pill_h // 2

    # Canvas with drop shadow padding
    shadow_pad = 28
    canvas_w = pill_w + (shadow_pad * 2)
    canvas_h = pill_h + (shadow_pad * 2)

    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 1. Soft Drop Shadow
    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle(
        [shadow_pad, shadow_pad + 6, shadow_pad + pill_w, shadow_pad + pill_h + 6],
        radius=radius,
        fill=(0, 0, 0, 150),
    )
    s_blurred = shadow_img.filter(ImageFilter.GaussianBlur(radius=16))
    img.alpha_composite(s_blurred, (0, 0))

    # 2. Glass Pill Body (Apple Vision Pro translucent glass)
    pill_img = Image.new("RGBA", (pill_w, pill_h), (0, 0, 0, 0))
    p_draw = ImageDraw.Draw(pill_img)

    p_draw.rounded_rectangle(
        [0, 0, pill_w, pill_h],
        radius=radius,
        fill=(14, 22, 38, 185),  # Obsidian glass ~72% opacity
        outline=(0, 242, 255, 140), # Glowing Cyan Glass rim
        width=2,
    )

    p_draw.rounded_rectangle(
        [1, 1, pill_w - 1, pill_h // 2],
        radius=radius,
        outline=(255, 255, 255, 55),
        width=1,
    )

    # 3. Telemetry Indicator Dot
    dot_y = (pill_h // 2)
    p_draw.ellipse([pad_x - 6, dot_y - 6, pad_x + 6, dot_y + 6], fill=(0, 242, 255, 255))

    # 4. Typography
    p_draw.text(
        (pad_x + dot_space - 6, pad_y - bbox[1]),
        clean_text,
        font=font,
        fill=COLOR_TEXT_WHITE,
    )

    img.alpha_composite(pill_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


def create_introductory_dilemma_card(
    dilemma_title: str,
    subtitle: str,
    output_path: Path,
    category_pill: str = "TELEMETRY SHOWDOWN",
    vertical_format: bool = True,
) -> Path:
    """Renders a floating Apple Glassmorphism dilemma card for the opening hook."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_w = 880 if vertical_format else 1100
    card_h = 440 if vertical_format else 420
    radius = 38
    shadow_pad = 40

    canvas_w = card_w + (shadow_pad * 2)
    canvas_h = card_h + (shadow_pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 1. Soft Drop Shadow
    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle(
        [shadow_pad + 4, shadow_pad + 12, shadow_pad + card_w + 4, shadow_pad + card_h + 12],
        radius=radius,
        fill=(0, 5, 20, 180),
    )
    s_blurred = shadow_img.filter(ImageFilter.GaussianBlur(radius=24))
    img.alpha_composite(s_blurred, (0, 0))

    # 2. Glass Card Body (Apple Liquid Glass translucent obsidian tint ~82% opacity)
    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_img)

    c_draw.rounded_rectangle(
        [0, 0, card_w, card_h],
        radius=radius,
        fill=(12, 19, 34, 210),
        outline=(0, 242, 255, 160),
        width=2,
    )

    c_draw.rounded_rectangle(
        [1, 1, card_w - 1, card_h // 2],
        radius=radius,
        outline=(255, 255, 255, 60),
        width=1,
    )

    pad_x = 48
    content_y = 44

    # 3. Top Category Pill: e.g. "TELEMETRY SHOWDOWN"
    f_cat = resolve_system_font(16 if vertical_format else 18, weight="bold")
    cat_text = category_pill.upper()
    cat_bb = f_cat.getbbox(cat_text)
    cp_w = (cat_bb[2] - cat_bb[0]) + 52
    cp_h = 32
    c_draw.rounded_rectangle(
        [pad_x, content_y, pad_x + cp_w, content_y + cp_h],
        radius=cp_h // 2,
        fill=(255, 255, 255, 30),
        outline=(0, 242, 255, 120),
        width=1,
    )
    c_draw.ellipse(
        [pad_x + 14, content_y + cp_h // 2 - 4, pad_x + 22, content_y + cp_h // 2 + 4],
        fill=(0, 242, 255, 255),
    )
    c_draw.text(
        (pad_x + 30, content_y + cp_h // 2),
        cat_text,
        font=f_cat,
        fill=(255, 255, 255, 240),
        anchor="lm",
    )

    # 4. Main Dilemma Title
    y_title = content_y + cp_h + 24
    max_text_w = card_w - (pad_x * 2)
    title_lines, f_title, title_sz = fit_text(
        dilemma_title.upper(),
        max_width=max_text_w,
        max_lines=2,
        start_size=40 if vertical_format else 48,
        min_size=24,
        weight="heavy",
    )

    # Text Bloom for Title
    title_glow = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    tg_draw = ImageDraw.Draw(title_glow)
    cur_yt = y_title
    for tl in title_lines:
        tg_draw.text((pad_x, cur_yt), tl, font=f_title, fill=(0, 242, 255, 130), anchor="lt")
        cur_yt += title_sz + 6
    card_img = Image.alpha_composite(card_img, title_glow.filter(ImageFilter.GaussianBlur(radius=10)))

    # Sharp Foreground Title
    c_draw = ImageDraw.Draw(card_img)
    cur_yt = y_title
    for tl in title_lines:
        c_draw.text((pad_x, cur_yt), tl, font=f_title, fill=(255, 255, 255, 255), anchor="lt")
        cur_yt += title_sz + 6

    # 5. Subtitle / Dilemma Query
    y_sub = cur_yt + 16
    sub_lines, f_sub, sub_sz = fit_text(
        subtitle,
        max_width=max_text_w,
        max_lines=3,
        start_size=24 if vertical_format else 28,
        min_size=16,
        weight="medium",
    )
    cur_ys = y_sub
    for sl in sub_lines:
        c_draw.text((pad_x, cur_ys), sl, font=f_sub, fill=(200, 225, 245, 220), anchor="lt")
        cur_ys += sub_sz + 4

    # 6. Bottom Technical Badge
    f_bot = resolve_system_font(13 if vertical_format else 15, weight="bold")
    c_draw.text(
        (pad_x, card_h - 38),
        "SILICON VERDICT • EMPIRICAL TELEMETRY",
        font=f_bot,
        fill=(0, 242, 255, 180),
        anchor="lt",
    )

    img.alpha_composite(card_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


def create_silicon_specs_card(
    title: str,
    subtitle: str,
    bullets: List[str],
    output_path: Path,
    vertical_format: bool = True,
) -> Path:
    """Renders a floating Apple Liquid Glass card displaying architectural telemetry specs (Act 2)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_w = 900 if vertical_format else 1150
    card_h = 460 if vertical_format else 430
    radius = 38
    shadow_pad = 40

    canvas_w = card_w + (shadow_pad * 2)
    canvas_h = card_h + (shadow_pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 1. Soft Drop Shadow
    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle(
        [shadow_pad + 4, shadow_pad + 12, shadow_pad + card_w + 4, shadow_pad + card_h + 12],
        radius=radius,
        fill=(0, 5, 20, 180),
    )
    img.alpha_composite(shadow_img.filter(ImageFilter.GaussianBlur(radius=24)), (0, 0))

    # 2. Glass Body
    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_img)
    c_draw.rounded_rectangle([0, 0, card_w, card_h], radius=radius, fill=(10, 18, 35, 205), outline=(0, 245, 255, 160), width=2)
    c_draw.rounded_rectangle([1, 1, card_w - 1, card_h // 2], radius=radius, outline=(255, 255, 255, 60), width=1)

    pad_x = 48
    # Top Category Pill
    f_pill = resolve_system_font(13 if vertical_format else 15, weight="bold")
    pill_txt = "SILICON ARCHITECTURE • TELEMETRY"
    bb_pt = f_pill.getbbox(pill_txt)
    pw = (bb_pt[2] - bb_pt[0]) + 36
    ph = 30
    c_draw.rounded_rectangle([pad_x, 32, pad_x + pw, 32 + ph], radius=ph // 2, fill=(0, 245, 255, 28), outline=(0, 245, 255, 160), width=1)
    c_draw.text((pad_x + pw // 2, 32 + ph // 2), pill_txt, font=f_pill, fill=(0, 245, 255, 255), anchor="mm")

    # Title
    f_title = resolve_system_font(28 if vertical_format else 32, weight="heavy")
    c_draw.text((pad_x, 82), title.upper(), font=f_title, fill=(255, 255, 255, 255))

    # Bullets
    f_bullet = resolve_system_font(21 if vertical_format else 23, weight="bold")
    y_b = 146
    for bullet in bullets[:3]:
        c_draw.ellipse([pad_x, y_b + 5, pad_x + 12, y_b + 17], fill=(0, 245, 255, 255))
        c_draw.text((pad_x + 24, y_b), bullet, font=f_bullet, fill=(230, 240, 255, 245))
        y_b += 56

    # Footer
    f_bot = resolve_system_font(13 if vertical_format else 15, weight="bold")
    c_draw.text((pad_x, card_h - 38), "SILICON VERDICT • EMPIRICAL DEEP DIVE", font=f_bot, fill=(0, 242, 255, 180), anchor="lt")

    img.alpha_composite(card_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


def create_golden_rule_card(
    title: str,
    takeaway: str,
    output_path: Path,
    vertical_format: bool = True,
) -> Path:
    """Renders the definitive golden rule purchasing takeaway card (Act 4)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_w = 900 if vertical_format else 1150
    card_h = 440 if vertical_format else 420
    radius = 38
    shadow_pad = 40

    canvas_w = card_w + (shadow_pad * 2)
    canvas_h = card_h + (shadow_pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 1. Soft Drop Shadow
    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle(
        [shadow_pad + 4, shadow_pad + 12, shadow_pad + card_w + 4, shadow_pad + card_h + 12],
        radius=radius,
        fill=(0, 5, 20, 180),
    )
    img.alpha_composite(shadow_img.filter(ImageFilter.GaussianBlur(radius=24)), (0, 0))

    # 2. Glass Body with Gold Rim Accent
    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_img)
    c_draw.rounded_rectangle([0, 0, card_w, card_h], radius=radius, fill=(10, 18, 35, 210), outline=(255, 215, 0, 180), width=2)
    c_draw.rounded_rectangle([1, 1, card_w - 1, card_h // 2], radius=radius, outline=(255, 235, 140, 60), width=1)

    pad_x = 48
    # Top Gold Badge
    f_badge = resolve_system_font(13 if vertical_format else 15, weight="bold")
    badge_txt = "★ SILICON VERDICT • THE GOLDEN RULE ★"
    bb_bg = f_badge.getbbox(badge_txt)
    pw = (bb_bg[2] - bb_bg[0]) + 36
    ph = 30
    c_draw.rounded_rectangle([pad_x, 32, pad_x + pw, 32 + ph], radius=ph // 2, fill=(255, 215, 0, 35), outline=(255, 215, 0, 200), width=1)
    c_draw.text((pad_x + pw // 2, 32 + ph // 2), badge_txt, font=f_badge, fill=(255, 225, 80, 255), anchor="mm")

    # Headline
    f_t = resolve_system_font(28 if vertical_format else 32, weight="heavy")
    c_draw.text((pad_x, 84), title.upper(), font=f_t, fill=(255, 255, 255, 255))

    # Takeaway Body
    f_body = resolve_system_font(21 if vertical_format else 23, weight="medium")
    body_lines, _, _ = fit_text(takeaway, max_width=card_w - (pad_x * 2), max_lines=4, start_size=21, min_size=16, weight="medium")
    y_b = 144
    for bl in body_lines:
        c_draw.text((pad_x, y_b), bl, font=f_body, fill=(210, 235, 255, 230))
        y_b += 34

    # Footer
    f_bot = resolve_system_font(12 if vertical_format else 14, weight="bold")
    c_draw.text((pad_x, card_h - 38), "EMPIRICAL HARDWARE RECOMMENDATION • 2026", font=f_bot, fill=(255, 215, 0, 190), anchor="lt")

    img.alpha_composite(card_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


def create_voting_poll_card(
    question: str,
    option_a: str,
    option_b: str,
    output_path: Path,
    vertical_format: bool = True,
) -> Path:
    """Renders the interactive community debate voting card (Act 5)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_w = 920 if vertical_format else 1180
    card_h = 480 if vertical_format else 450
    radius = 38
    shadow_pad = 40

    canvas_w = card_w + (shadow_pad * 2)
    canvas_h = card_h + (shadow_pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    # 1. Soft Drop Shadow
    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle(
        [shadow_pad + 4, shadow_pad + 12, shadow_pad + card_w + 4, shadow_pad + card_h + 12],
        radius=radius,
        fill=(0, 5, 20, 180),
    )
    img.alpha_composite(shadow_img.filter(ImageFilter.GaussianBlur(radius=24)), (0, 0))

    # 2. Glass Body
    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_img)
    c_draw.rounded_rectangle([0, 0, card_w, card_h], radius=radius, fill=(10, 18, 35, 215), outline=(0, 245, 255, 180), width=2)
    c_draw.rounded_rectangle([1, 1, card_w - 1, card_h // 2], radius=radius, outline=(255, 255, 255, 60), width=1)

    pad_x = 44
    # Top Community Pill
    f_pill = resolve_system_font(13 if vertical_format else 15, weight="bold")
    pill_txt = "COMMUNITY DEBATE • DROP YOUR VOTE"
    bb_pt = f_pill.getbbox(pill_txt)
    pw = (bb_pt[2] - bb_pt[0]) + 36
    ph = 30
    c_draw.rounded_rectangle([pad_x, 26, pad_x + pw, 26 + ph], radius=ph // 2, fill=(0, 245, 255, 28), outline=(0, 245, 255, 180), width=1)
    c_draw.text((pad_x + pw // 2, 26 + ph // 2), pill_txt, font=f_pill, fill=(0, 245, 255, 255), anchor="mm")

    # Question
    f_q = resolve_system_font(24 if vertical_format else 28, weight="bold")
    q_lines, _, _ = fit_text(question, max_width=card_w - (pad_x * 2), max_lines=2, start_size=24, min_size=18, weight="bold")
    y_q = 72
    for ql in q_lines:
        c_draw.text((pad_x, y_q), ql, font=f_q, fill=(255, 255, 255, 255))
        y_q += 30

    # Option A Box (Cyan Theme)
    opt_y = y_q + 16
    opt_h = 76
    c_draw.rounded_rectangle([pad_x, opt_y, card_w - pad_x, opt_y + opt_h], radius=18, fill=(0, 245, 255, 24), outline=(0, 245, 255, 180), width=2)
    c_draw.text((pad_x + 24, opt_y + opt_h // 2), "A", font=resolve_system_font(30, weight="heavy"), fill=(0, 245, 255, 255), anchor="lm")
    c_draw.text((pad_x + 64, opt_y + opt_h // 2), option_a, font=resolve_system_font(19, weight="bold"), fill=(255, 255, 255, 255), anchor="lm")

    # Option B Box (Purple/Violet Theme)
    opt_y2 = opt_y + opt_h + 16
    c_draw.rounded_rectangle([pad_x, opt_y2, card_w - pad_x, opt_y2 + opt_h], radius=18, fill=(121, 40, 202, 28), outline=(180, 80, 255, 180), width=2)
    c_draw.text((pad_x + 24, opt_y2 + opt_h // 2), "B", font=resolve_system_font(30, weight="heavy"), fill=(180, 100, 255, 255), anchor="lm")
    c_draw.text((pad_x + 64, opt_y2 + opt_h // 2), option_b, font=resolve_system_font(19, weight="bold"), fill=(255, 255, 255, 255), anchor="lm")

    # Call to Action at Bottom
    f_cta = resolve_system_font(17 if vertical_format else 19, weight="heavy")
    c_draw.text((card_w // 2, card_h - 34), "💬 TYPE 'A' OR 'B' IN THE COMMENTS BELOW ⬇", font=f_cta, fill=(0, 245, 255, 255), anchor="mm")

    img.alpha_composite(card_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


def render_composite_overlay_clip(
    bg_video_path: Optional[Path],
    overlay_png_path: Path,
    duration_sec: float,
    output_clip_path: Path,
    dim_factor: float = 1.0,
    blur_bg: int = 0,
    overlay_y: str = "(H-h)/2 - 100",
) -> Path:
    """Renders a 1080x1920 60 FPS video clip overlaying an Apple Liquid Glass card on video or high-tech background.

    - If bg_video_path exists: loops, scales and center-crops to 1080x1920.
    - If bg_video_path is None or missing: generates an elegant dark obsidian tech canvas.
    - Optionally applies dimming (e.g. eq=brightness=-0.15 for Act 4 dimmed gameplay).
    - Overlays the card and cuts strictly to duration_sec without audio (-an).
    """
    output_clip_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = shutil.which("ffmpeg") or str(Path(sys.executable).parent / "ffmpeg") or "ffmpeg"

    if bg_video_path and Path(bg_video_path).is_file():
        bg_input = ["-stream_loop", "-1", "-i", str(bg_video_path)]
        base_filter = "[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=60"
    else:
        bg_input = ["-f", "lavfi", "-i", f"color=c=#070b14:s=1080x1920:r=60:d={duration_sec:.2f}"]
        base_filter = "[0:v]setsar=1,fps=60"

    filters = [base_filter]
    if blur_bg > 0:
        filters.append(f"gblur=sigma={blur_bg}")
    if dim_factor < 0.99:
        brightness_val = (dim_factor - 1.0) * 0.35
        filters.append(f"eq=brightness={brightness_val:.2f}:contrast=1.1")

    bg_chain = ",".join(filters) + "[bg];"
    filter_complex = f"{bg_chain}[1:v]format=rgba[card];[bg][card]overlay=x=(W-w)/2:y={overlay_y}[v]"

    cmd = [
        ffmpeg_bin, "-y",
        *bg_input,
        "-i", str(overlay_png_path),
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


class VideoRenderer:
    """Assembles audio, stock video, and animated Apple Liquid Glass benchmarks via FFmpeg."""

    def __init__(self, work_dir: Path):
        self.work_dir = work_dir
        self.segments_dir = work_dir / "segments"
        self.shorts_dir = work_dir / "shorts"
        self.charts_dir = work_dir / "charts"
        self.overlays_dir = work_dir / "overlays"
        self.segments_dir.mkdir(parents=True, exist_ok=True)
        self.shorts_dir.mkdir(parents=True, exist_ok=True)
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        self.overlays_dir.mkdir(parents=True, exist_ok=True)

    def render_scene_clip(
        self,
        scene: Scene,
        media: SceneMedia,
        audio: SceneAudio,
    ) -> Path:
        """Generates a 1080p 16:9 MP4 segment.

        If scene has chart_data, renders the live animated Apple Liquid Glass benchmark.
        Otherwise, renders B-roll footage with an Apple Vision Pro HUD glass pill overlay.
        """
        output_clip = self.segments_dir / f"clip_{scene.scene_id:03d}.mp4"
        duration_str = f"{audio.duration_seconds:.3f}"
        fps = settings.VIDEO_FPS

        if scene.chart_data:
            logger.info("Rendering animated Apple Liquid Glass benchmark motion for scene %d", scene.scene_id)
            render_animated_benchmark_video(
                chart_data=scene.chart_data,
                audio_path=Path(audio.audio_path),
                output_video_path=output_clip,
                duration_sec=audio.duration_seconds,
                fps=fps,
                vertical_format=False,
            )
            return output_clip

        # Stock B-roll with Vision Pro HUD glass pill overlay
        hud_pill_path = self.overlays_dir / f"hud_pill_{scene.scene_id:03d}_16x9.png"
        create_vision_pro_hud_pill(scene.on_screen_text, hud_pill_path, vertical_format=False)

        filter_complex = (
            f"[0:v]scale={settings.VIDEO_WIDTH}:{settings.VIDEO_HEIGHT}:force_original_aspect_ratio=increase,"
            f"crop={settings.VIDEO_WIDTH}:{settings.VIDEO_HEIGHT},setsar=1,fps={fps}[base];"
            f"[1:v]format=rgba,fade=t=in:st=0.2:d=0.4:alpha=1[hud];"
            f"[base][hud]overlay=x=(W-w)/2:y=H-h-90:format=auto[v]"
        )

        input_flags = ["-stream_loop", "-1", "-i", media.media_path] if media.media_type == "video" else ["-loop", "1", "-i", media.media_path]

        cmd = [
            "ffmpeg", "-y",
            *input_flags,
            "-i", str(hud_pill_path),
            "-i", audio.audio_path,
            "-t", duration_str,
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "2:a",
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "21",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-ac", "2",
            "-shortest",
            str(output_clip),
        ]

        logger.debug("Rendering scene clip %d command: %s", scene.scene_id, " ".join(cmd))
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error("FFmpeg error rendering scene %d:\n%s", scene.scene_id, result.stderr)
            raise RuntimeError(f"FFmpeg failed rendering clip {scene.scene_id}: {result.stderr[-400:]}")

        return output_clip

    def render_short_highlight(
        self,
        scene: Scene,
        clip_path: Path,
        audio: SceneAudio,
    ) -> Path:
        """Produces a 9:16 vertical Short (1080x1920) with synchronized subtitles & Apple Glass UI."""
        output_short = self.shorts_dir / f"short_{scene.scene_id:03d}.mp4"
        fps = settings.VIDEO_FPS

        # 1. Generate kinetic word-by-word synchronized subtitles
        subtitles_ass_path = self.work_dir / f"subtitles_short_{scene.scene_id:03d}.ass"
        try:
            generate_kinetic_subtitles(
                audio_path=Path(audio.audio_path),
                output_ass_path=subtitles_ass_path,
                model_size="base",
            )
        except Exception as e:
            logger.warning("Whisper subtitle generation failed for Short %d: %s", scene.scene_id, e)
            subtitles_ass_path = None

        if scene.chart_data:
            # Render dedicated vertical animated liquid glass benchmark with kinetic subtitles
            logger.info("Rendering animated 9:16 Apple Liquid Glass benchmark for Short %d", scene.scene_id)
            render_animated_benchmark_video(
                chart_data=scene.chart_data,
                audio_path=Path(audio.audio_path),
                output_video_path=output_short,
                duration_sec=audio.duration_seconds,
                fps=fps,
                vertical_format=True,
                subtitles_ass_path=subtitles_ass_path,
            )
            return output_short

        # Vertical B-roll with Vision Pro HUD (Upper Third Y=360) and Subtitles (Y=1260..1420)
        hud_pill_path = self.overlays_dir / f"hud_pill_{scene.scene_id:03d}_9x16.png"
        create_vision_pro_hud_pill(scene.on_screen_text, hud_pill_path, vertical_format=True)

        if subtitles_ass_path and subtitles_ass_path.exists():
            filter_complex = (
                f"[0:v]scale={settings.SHORT_WIDTH}:{settings.SHORT_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={settings.SHORT_WIDTH}:{settings.SHORT_HEIGHT},"
                f"setsar=1,fps={fps}[base];"
                f"[1:v]format=rgba,fade=t=in:st=0.2:d=0.4:alpha=1[hud];"
                f"[base][hud]overlay=x=(W-w)/2:y=360:format=auto,ass={subtitles_ass_path}[v]"
            )
        else:
            filter_complex = (
                f"[0:v]scale={settings.SHORT_WIDTH}:{settings.SHORT_HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={settings.SHORT_WIDTH}:{settings.SHORT_HEIGHT},"
                f"setsar=1,fps={fps}[base];"
                f"[1:v]format=rgba,fade=t=in:st=0.2:d=0.4:alpha=1[hud];"
                f"[base][hud]overlay=x=(W-w)/2:y=360:format=auto[v]"
            )
        cmd = [
            "ffmpeg", "-y",
            "-i", str(clip_path),
            "-i", str(hud_pill_path),
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "faster",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            str(output_short),
        ]

        logger.info("Rendering 9:16 Short with Apple Glass HUD for scene %d", scene.scene_id)
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error("FFmpeg error rendering Short for scene %d:\n%s", scene.scene_id, result.stderr)
            raise RuntimeError(f"FFmpeg failed rendering Short {scene.scene_id}: {result.stderr[-400:]}")

        return output_short

    def concatenate_clips(self, clip_paths: List[Path], final_output: Path) -> Path:
        """Concatenates all normalized scene clips into the complete full-length video."""
        concat_list_file = self.work_dir / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for clip in clip_paths:
                f.write(f"file '{clip.resolve()}'\n")

        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(final_output),
        ]

        logger.info("Concatenating %d scenes into full video: %s", len(clip_paths), final_output.name)
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            logger.error("FFmpeg concat demuxer failed:\n%s", result.stderr)
            raise RuntimeError(f"FFmpeg concat failed: {result.stderr[-400:]}")

        return final_output

    def render_project(
        self,
        project: VideoProject,
        media_map: Dict[int, SceneMedia],
        audio_map: Dict[int, SceneAudio],
    ) -> RenderedOutputs:
        """Executes full Apple Liquid Glass rendering pipeline."""
        logger.info("Starting Apple Liquid Glass render pipeline for: '%s'", project.title)
        rendered_clips: List[Path] = []
        clip_by_scene: Dict[int, Path] = {}

        # 1. Render clips for each scene
        for scene in project.scenes:
            media = media_map[scene.scene_id]
            audio = audio_map[scene.scene_id]
            clip = self.render_scene_clip(scene, media, audio)
            rendered_clips.append(clip)
            clip_by_scene[scene.scene_id] = clip

        # 2. Concatenate into full 1080p video
        full_video_path = self.work_dir / "final_video_1080p.mp4"
        self.concatenate_clips(rendered_clips, full_video_path)

        # 3. Render 9:16 Shorts
        shorts_paths: List[str] = []
        for scene in project.scenes:
            if scene.is_short_highlight:
                clip = clip_by_scene[scene.scene_id]
                audio = audio_map[scene.scene_id]
                short_path = self.render_short_highlight(
                    scene=scene,
                    clip_path=clip,
                    audio=audio,
                )
                shorts_paths.append(str(short_path))

        logger.info(
            "Apple Liquid Glass rendering completed: Full video (%s), %d Shorts generated",
            full_video_path.name,
            len(shorts_paths),
        )

        return RenderedOutputs(
            full_video_path=str(full_video_path),
            shorts_paths=shorts_paths,
        )
