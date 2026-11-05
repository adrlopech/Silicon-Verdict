import logging
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from core.schemas import ChartData

logger = logging.getLogger(__name__)

# Premium Apple Liquid Glass Color Tokens
COLOR_OBSIDIAN_SPACE = (6, 9, 16)         # Deep Obsidian Space (#060910)
COLOR_ELECTRIC_CYAN = (0, 245, 255)       # #00F5FF Glacial Cyan
COLOR_COBALT_BLUE = (0, 102, 255)         # #0066FF Electric Cobalt / Sapphire
COLOR_PURPLE_VIBRANT = (121, 40, 202)     # #7928CA Electric Purple
COLOR_DEEP_NAVY = (15, 26, 54)
COLOR_TEXT_WHITE = (255, 255, 255)


def resolve_system_font(size: int, weight: str = "regular") -> ImageFont.FreeTypeFont:
    """Selects the cleanest available Apple/sans-serif font on the current host with strict weight mapping."""
    weight = weight.lower()
    helvetica_ttc = "/System/Library/Fonts/HelveticaNeue.ttc"
    arial_black = "/System/Library/Fonts/Supplemental/Arial Black.ttf"

    if weight in ("black", "heavy", "extrabold"):
        if os.path.isfile(arial_black):
            try:
                return ImageFont.truetype(arial_black, size=size)
            except Exception:
                pass

    if os.path.isfile(helvetica_ttc):
        idx_map = {"light": 7, "thin": 12, "medium": 10, "bold": 1, "regular": 0}
        idx = idx_map.get(weight, 0)
        try:
            return ImageFont.truetype(helvetica_ttc, size=size, index=idx)
        except Exception:
            pass

    bold_candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/usr/share/fonts/truetype/custom/Inter-Bold.ttf",
        "/usr/share/fonts/truetype/custom/Inter-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    regular_candidates = [
        "/System/Library/Fonts/SFNS.ttf",
        "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/custom/Inter-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]

    candidates = bold_candidates if weight in ("bold", "black", "heavy", "extrabold") else regular_candidates

    for font_path in candidates:
        if os.path.isfile(font_path):
            try:
                return ImageFont.truetype(font_path, size=size)
            except Exception:
                continue

    return ImageFont.load_default()


def fit_text(
    text: str,
    max_width: int,
    max_lines: int = 2,
    start_size: int = 38,
    min_size: int = 20,
    weight: str = "bold",
) -> Tuple[List[str], ImageFont.FreeTypeFont, int]:
    """Universal text wrapping, progressive scaling, and ellipsis truncation algorithm.

    - Progressively reduces font size by 2px steps from start_size down to min_size.
    - Automatically wraps up to max_lines if width exceeds max_width.
    - If min_size is reached and text still exceeds max_width, truncates with '...'.

    Returns:
        (lines, font, final_font_size)
    """
    clean_text = text.strip()
    words = clean_text.split()
    if not words:
        return ([""], resolve_system_font(start_size, weight=weight), start_size)

    # 1. Attempt single-line or multi-line fit stepping down by 2px
    for size in range(start_size, min_size - 1, -2):
        font = resolve_system_font(size, weight=weight)
        tb = font.getbbox(clean_text)
        if (tb[2] - tb[0]) <= max_width:
            return ([clean_text], font, size)

        if max_lines > 1:
            lines = []
            cur_line = []
            possible = True
            for word in words:
                test_str = " ".join(cur_line + [word])
                wb = font.getbbox(test_str)
                if (wb[2] - wb[0]) <= max_width:
                    cur_line.append(word)
                else:
                    if cur_line:
                        lines.append(" ".join(cur_line))
                        cur_line = [word]
                        wb_word = font.getbbox(word)
                        if (wb_word[2] - wb_word[0]) > max_width:
                            possible = False
                            break
                    else:
                        possible = False
                        break
            if possible:
                if cur_line:
                    lines.append(" ".join(cur_line))
                if len(lines) <= max_lines:
                    return (lines, font, size)

    # 2. Reached min_size: construct max_lines with ellipsis truncation
    font = resolve_system_font(min_size, weight=weight)
    ell = "..."
    lines = []
    idx = 0

    for _ in range(max_lines - 1):
        cur_line = []
        while idx < len(words):
            word = words[idx]
            test_str = " ".join(cur_line + [word])
            if (font.getbbox(test_str)[2] - font.getbbox(test_str)[0]) <= max_width:
                cur_line.append(word)
                idx += 1
            else:
                break
        if cur_line:
            lines.append(" ".join(cur_line))

    # Last line with ellipsis truncation if needed
    rem_text = " ".join(words[idx:])
    if not rem_text and lines:
        return (lines, font, min_size)

    if (font.getbbox(rem_text)[2] - font.getbbox(rem_text)[0]) <= max_width:
        lines.append(rem_text)
    else:
        while rem_text and (font.getbbox(rem_text + ell)[2] - font.getbbox(rem_text + ell)[0]) > max_width:
            rem_text = rem_text[:-1].rstrip()
        lines.append((rem_text + ell) if rem_text else ell)

    return (lines[:max_lines], font, min_size)


def create_dynamic_liquid_mesh(width: int, height: int, t: float = 0.0) -> Image.Image:
    """Generates an atmospheric dark canvas with continuously floating and deforming liquid light orbs.
    
    Uses harmonic multi-frequency oscillation to simulate fluid, organic 3D metaballs with directional
    rim lighting and volumetric gradients. Returns an RGBA canvas with alpha=255.
    """
    canvas = Image.new("RGBA", (width, height), (*COLOR_OBSIDIAN_SPACE, 255))
    orbs = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(orbs)

    # Orb 1 (Top-Left / Edge): Vibrant Electric Cyan with Cobalt Core
    cx1 = int(-60 + 45 * math.sin(t * 1.25))
    cy1 = int(-40 + 35 * math.cos(t * 1.05))
    rx1 = int(460 + 30 * math.sin(t * 1.8))
    ry1 = int(430 + 30 * math.cos(t * 1.6))
    draw.ellipse([cx1 - rx1, cy1 - ry1, cx1 + rx1, cy1 + ry1], fill=(0, 245, 255, 205))
    draw.ellipse([cx1 - int(rx1 * 0.58), cy1 - int(ry1 * 0.58), cx1 + int(rx1 * 0.58), cy1 + int(ry1 * 0.58)], fill=(0, 102, 255, 185))

    # Orb 2 (Top-Right / Upper Flank): Brilliant Glacial Cyan & Sapphire Cobalt
    cx2 = int(1720 + 45 * math.cos(t * 1.15))
    cy2 = int(190 + 38 * math.sin(t * 1.35))
    rx2 = int(520 + 35 * math.cos(t * 1.7))
    ry2 = int(480 + 35 * math.sin(t * 1.5))
    draw.ellipse([cx2 - rx2, cy2 - ry2, cx2 + rx2, cy2 + ry2], fill=(0, 245, 255, 225))
    draw.ellipse([cx2 - int(rx2 * 0.60), cy2 - int(ry2 * 0.60), cx2 + int(rx2 * 0.60), cy2 + int(ry2 * 0.60)], fill=(0, 102, 255, 195))

    # Orb 3 (Bottom-Left / Deep Indigo): Vibrant Electric Purple Aura
    cx3 = int(140 + 35 * math.cos(t * 1.30))
    cy3 = int(960 + 32 * math.sin(t * 1.10))
    rx3 = int(450 + 28 * math.sin(t * 1.9))
    ry3 = int(420 + 28 * math.cos(t * 1.6))
    draw.ellipse([cx3 - rx3, cy3 - ry3, cx3 + rx3, cy3 + ry3], fill=(121, 40, 202, 195))
    draw.ellipse([cx3 - int(rx3 * 0.58), cy3 - int(ry3 * 0.58), cx3 + int(rx3 * 0.58), cy3 + int(ry3 * 0.58)], fill=(0, 102, 255, 165))

    # Orb 4 (Bottom-Right / Far Edge): Deep Cobalt with Cyan Halo
    cx4 = int(1680 + 40 * math.sin(t * 1.20))
    cy4 = int(890 + 32 * math.cos(t * 1.30))
    rx4 = int(490 + 32 * math.cos(t * 1.5))
    ry4 = int(440 + 32 * math.sin(t * 2.0))
    draw.ellipse([cx4 - rx4, cy4 - ry4, cx4 + rx4, cy4 + ry4], fill=(0, 102, 255, 205))
    draw.ellipse([cx4 - int(rx4 * 0.52), cy4 - int(ry4 * 0.52), cx4 + int(rx4 * 0.52), cy4 + int(ry4 * 0.52)], fill=(0, 245, 255, 155))

    blurred_orbs = orbs.filter(ImageFilter.GaussianBlur(radius=65))
    canvas = Image.alpha_composite(canvas, blurred_orbs)
    return canvas


def draw_true_liquid_glass_card(
    canvas: Image.Image,
    box: Tuple[int, int, int, int],
    radius: int = 48,
    card_alpha: float = 1.0,
) -> Image.Image:
    """Renders an authentic Apple Liquid Glass floating card with 14% tint, 1.15 brightness boost, inner rim glow and multi-pass bloom."""
    x0, y0, x1, y1 = box
    w = x1 - x0
    h = y1 - y0

    if card_alpha <= 0.01:
        return canvas

    # 1. Soft Layered Drop Shadow
    shadow_layer = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_layer)
    s_alpha = int(160 * card_alpha)
    s_draw.rounded_rectangle(
        [x0, y0 + 18, x1, y1 + 18],
        radius=radius,
        fill=(0, 0, 0, s_alpha),
    )
    shadow_blurred = shadow_layer.filter(ImageFilter.GaussianBlur(radius=35))
    canvas = Image.alpha_composite(canvas, shadow_blurred)

    # 2. True Optical Backdrop Blur (30px blur + 1.15 brightness boost)
    bg_crop = canvas.crop((x0, y0, x1, y1))
    blurred_crop = bg_crop.filter(ImageFilter.GaussianBlur(radius=30))
    brightened_crop = ImageEnhance.Brightness(blurred_crop).enhance(1.15)

    # Dark glass tint: strictly 14% opacity (10, 18, 35, 36) allowing background orbs to clearly shine through
    tint_layer = Image.new("RGBA", (w, h), (10, 18, 35, int(36 * card_alpha)))
    frosted = Image.alpha_composite(brightened_crop, tint_layer)

    # Diagonal Specular Veil: rgba(200, 235, 255, 0.14) in upper-left and center
    x_grid = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
    y_grid = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None]
    diag_t = np.clip((x_grid + y_grid) * 0.5, 0.0, 1.0)
    veil_alpha = np.clip((1.0 - diag_t * 1.4) * (0.14 * 255.0), 0.0, 0.14 * 255.0).astype(np.float32) * card_alpha

    diag_veil = np.zeros((h, w, 4), dtype=np.uint8)
    diag_veil[:, :, 0] = 200
    diag_veil[:, :, 1] = 235
    diag_veil[:, :, 2] = 255
    diag_veil[:, :, 3] = np.clip(veil_alpha, 0, 255).astype(np.uint8)
    veil_img = Image.fromarray(diag_veil, mode="RGBA")
    frosted = Image.alpha_composite(frosted, veil_img)

    # Inner Rim Glow (15px radius along top and left inside card)
    card_mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(card_mask).rounded_rectangle([0, 0, w, h], radius=radius, fill=255)

    inner_rim = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ir_draw = ImageDraw.Draw(inner_rim)
    ir_col = (180, 245, 255, int(150 * card_alpha))
    ir_draw.line([(radius, 2), (w - radius, 2)], fill=ir_col, width=4)
    ir_draw.line([(2, radius), (2, h - radius)], fill=ir_col, width=4)
    inner_rim_blurred = inner_rim.filter(ImageFilter.GaussianBlur(radius=15))
    inner_rim_blurred.putalpha(Image.fromarray(
        (np.array(inner_rim_blurred.getchannel("A"), dtype=np.float32) * (np.array(card_mask, dtype=np.float32) / 255.0)).astype(np.uint8)
    ))
    frosted = Image.alpha_composite(frosted, inner_rim_blurred)

    canvas.paste(frosted, (x0, y0), card_mask)

    # 3. Multi-Pass Rim Bloom (Top-Left, Top-Center, Bottom-Center, Bottom-Right)
    # Pass 1: Outer Glow (8px, #00F2FF, blur 25, opacity 75%)
    p1_layer = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
    d1 = ImageDraw.Draw(p1_layer)
    c_cyan = (0, 242, 255, int(191 * card_alpha))

    # Pass 2: Core Glow (4px, #B0FFFF, blur 8, opacity 90%)
    p2_layer = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(p2_layer)
    c_core = (176, 255, 255, int(230 * card_alpha))

    # Pass 3: Hotspot (2px, #FFFFFF, opacity 100%)
    p3_layer = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
    d3 = ImageDraw.Draw(p3_layer)
    c_white = (255, 255, 255, int(255 * card_alpha))

    for (d, col, w_stroke) in [(d1, c_cyan, 8), (d2, c_core, 4), (d3, c_white, 2)]:
        # Top-Left Corner
        d.arc([x0, y0, x0 + radius * 2, y0 + radius * 2], start=180, end=270, fill=col, width=w_stroke)
        d.line([(x0 + radius, y0), (x0 + radius + 80, y0)], fill=col, width=w_stroke)
        d.line([(x0, y0 + radius), (x0, y0 + radius + 60)], fill=col, width=w_stroke)
        # Top Edge Segment
        d.line([(x1 - 260, y0), (x1 - 60, y0)], fill=col, width=w_stroke)
        # Bottom Edge Segment
        d.line([(x0 + int(w * 0.45), y1), (x0 + int(w * 0.70), y1)], fill=col, width=w_stroke)
        # Bottom-Right Corner
        d.arc([x1 - radius * 2, y1 - radius * 2, x1, y1], start=0, end=90, fill=col, width=w_stroke)
        d.line([(x1 - radius - 80, y1), (x1 - radius, y1)], fill=col, width=w_stroke)
        d.line([(x1, y1 - radius - 60), (x1, y1 - radius)], fill=col, width=w_stroke)

    canvas = Image.alpha_composite(canvas, p1_layer.filter(ImageFilter.GaussianBlur(radius=25)))
    canvas = Image.alpha_composite(canvas, p2_layer.filter(ImageFilter.GaussianBlur(radius=8)))
    canvas = Image.alpha_composite(canvas, p3_layer)

    # 4. Clean Baseline Perimeter Border (1.0px: rgba(255, 255, 255, 0.28))
    rim_layer = Image.new("RGBA", (canvas.width, canvas.height), (0, 0, 0, 0))
    r_draw = ImageDraw.Draw(rim_layer)
    r_draw.rounded_rectangle(
        [x0, y0, x1, y1],
        radius=radius,
        outline=(255, 255, 255, int(70 * card_alpha)),
        width=1,
    )
    canvas = Image.alpha_composite(canvas, rim_layer)
    return canvas


def build_winner_bar(w: int, h: int, radius: int) -> Image.Image:
    """Builds an Apple Liquid Glass winner pill with cylindrical volume (top specular highlight + bottom inner shadow)."""
    arr = np.zeros((h, w, 4), dtype=np.float32)

    # 1. Horizontal gradient: Left #00F2FF (0, 242, 255) to Right #0066FF (0, 102, 255)
    t_x = np.linspace(0.0, 1.0, w, dtype=np.float32)[None, :]
    arr[:, :, 0] = 0.0
    arr[:, :, 1] = 242.0 * (1.0 - t_x) + 102.0 * t_x
    arr[:, :, 2] = 255.0
    arr[:, :, 3] = 235.0  # Translucency to feel the glass

    # 2. Specular highlight in upper 35%: rgba(255, 255, 255, 0.40) at top to 0.0 at h*0.35
    sheen_h = int(h * 0.35)
    sheen_alpha = np.zeros((h, 1), dtype=np.float32)
    y_coords = np.arange(sheen_h, dtype=np.float32)
    sheen_alpha[:sheen_h, 0] = (255.0 * 0.40) * ((1.0 - (y_coords / sheen_h)) ** 1.5)
    a_s = sheen_alpha / 255.0
    for c in range(3):
        arr[:, :, c] = arr[:, :, c] * (1.0 - a_s) + 255.0 * a_s

    # 3. Inner shadow in bottom 15% to accentuate 3D cylindrical curvature
    shadow_h = int(h * 0.15)
    bot_y = np.arange(shadow_h, dtype=np.float32)
    shadow_darkness = (0.32 * (bot_y / shadow_h) ** 1.2)[:, None, None]
    start_y = h - shadow_h
    arr[start_y:, :, :3] = arr[start_y:, :, :3] * (1.0 - shadow_darkness)

    # 4. Pill mask
    mask_img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask_img).rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    mask_arr = np.array(mask_img, dtype=np.float32)[:, :, None] / 255.0
    arr[:, :, 3:4] = arr[:, :, 3:4] * mask_arr

    pill_img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGBA")

    # 5. Perimeter border 1.5px in rgba(180, 245, 255, 0.7)
    b_draw = ImageDraw.Draw(pill_img)
    b_draw.rounded_rectangle([0, 0, w, h], radius=radius, outline=(180, 245, 255, 178), width=1)
    b_draw.rounded_rectangle([1, 1, w - 1, h - 1], radius=radius, outline=(180, 245, 255, 90), width=1)
    return pill_img


def build_runner_up_bar(w: int, h: int, radius: int) -> Image.Image:
    """Builds a translucent smoky blue-gray glass pill with subtle vertical gradient and fine border."""
    arr = np.zeros((h, w, 4), dtype=np.float32)
    t_y = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    top_rgb = np.array([255.0, 255.0, 255.0], dtype=np.float32)[None, None, :]
    bot_rgb = np.array([20.0, 30.0, 48.0], dtype=np.float32)[None, None, :]
    top_a = 0.12
    bot_a = 0.25
    base_rgb = np.array([140.0, 170.0, 210.0], dtype=np.float32)[None, None, :]
    base_a = 0.18

    grad_rgb = top_rgb * (1.0 - t_y) + bot_rgb * t_y
    grad_a = top_a * (1.0 - t_y) + bot_a * t_y

    out_a = base_a + grad_a * (1.0 - base_a)
    out_rgb = (base_rgb * base_a + grad_rgb * grad_a * (1.0 - base_a)) / np.maximum(out_a, 1e-5)

    arr[:, :, :3] = out_rgb
    arr[:, :, 3:4] = out_a * 255.0

    mask_img = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask_img).rounded_rectangle([0, 0, w, h], radius=radius, fill=255)
    mask_arr = np.array(mask_img, dtype=np.float32)[:, :, None] / 255.0
    arr[:, :, 3:4] = arr[:, :, 3:4] * mask_arr

    pill_img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), mode="RGBA")
    ImageDraw.Draw(pill_img).rounded_rectangle([0, 0, w, h], radius=radius, outline=(255, 255, 255, 56), width=1)
    return pill_img


def render_liquid_glass_benchmark_frame(
    chart_data: ChartData,
    card_alpha: float = 1.0,
    bar_growth: float = 1.0,
    badge_scale: float = 1.0,
    badge_alpha: float = 1.0,
    pulse_glow: float = 0.0,
    time_sec: float = 0.0,
    vertical_format: bool = False,
    cached_bg: Optional[Image.Image] = None,
) -> Image.Image:
    """Renders a single frame matching the exact Apple Liquid Glass reference architecture with perfect alignment."""
    if vertical_format:
        W, H = 1080, 1920
        # Safe Zone: X: 60..880, Y: 220..1420. Liquid Glass Card strictly in Y: 360..1120
        card_x0, card_y0 = 60, 360
        card_x1, card_y1 = 880, 1120
        radius = 44
        bar_h = 88
        row_gap = 130
    else:
        W, H = 1920, 1080
        # Reference layout: 1260x700 centered
        card_x0, card_y0 = 330, 190
        card_x1, card_y1 = 1590, 890
        radius = 48
        bar_h = 104
        row_gap = 145

    # 1. Base Canvas with Dynamic Liquid Mesh
    if cached_bg is not None:
        canvas = cached_bg.copy()
    else:
        canvas = create_dynamic_liquid_mesh(W, H, t=time_sec)

    # 2. Glass Card Geometry & Entrance Animation
    card_w = card_x1 - card_x0
    card_h = card_y1 - card_y0
    center_x = (card_x0 + card_x1) // 2
    center_y = (card_y0 + card_y1) // 2

    cur_scale = 0.96 + 0.04 * card_alpha
    y_slide = int(24 * (1.0 - card_alpha))
    scaled_w = int(card_w * cur_scale)
    scaled_h = int(card_h * cur_scale)
    cur_x0 = center_x - scaled_w // 2
    cur_x1 = cur_x0 + scaled_w
    cur_y0 = center_y - scaled_h // 2 + y_slide
    cur_y1 = cur_y0 + scaled_h

    # Render True Liquid Glass Card (Backdrop Blur + 14% Tint + Diagonal Specular + Inner Rim Glow + Multi-Pass Rim Bloom)
    canvas = draw_true_liquid_glass_card(canvas, (cur_x0, cur_y0, cur_x1, cur_y1), radius=radius, card_alpha=card_alpha)

    pad_x = 44 if vertical_format else 72
    pad_y = 44 if vertical_format else 64
    content_x = cur_x0 + pad_x
    content_y = cur_y0 + pad_y
    inner_w = scaled_w - (pad_x * 2)

    labels = chart_data.labels
    values = chart_data.values
    max_val = max(values) if values else 1.0
    unit_str = chart_data.metric_unit or "FPS"

    # Title fit to card_w - 120, max 2 lines
    sub_text = chart_data.subtitle or "8GB vs 16GB VRAM"
    max_title_w = scaled_w - 120
    title_lines, f_title_fit, title_sz = fit_text(
        sub_text,
        max_width=max_title_w,
        max_lines=2,
        start_size=36 if vertical_format else 46,
        min_size=20,
        weight="black",
    )
    is_two_line_title = len(title_lines) > 1
    title_offset = 22 if is_two_line_title else 0

    grid_top = cur_y0 + (185 if vertical_format else 205) + title_offset
    grid_bottom = cur_y0 + (580 if vertical_format else 620) + title_offset
    track_radius = bar_h // 2
    bars_start_y = cur_y0 + (235 if vertical_format else 255) + title_offset

    c1_w = int(inner_w * (0.94 if vertical_format else 0.92))
    W_track = c1_w

    # =========================================================================
    # DEFENSIVE LAYOUT: RIGID THREE-ZONE BAR PARTITIONING (Zero-Collision)
    # Zone 1 (0%..38%): Name & technical specs (split into 2 lines if parens)
    # Zone 2 (38%..62%): Badge centered at 50% (anchor="mm"), alpha=0 if growth<=0.55
    # Zone 3 (75%..96%): Numeric FPS Metric anchored to right edge (anchor="rm")
    # =========================================================================
    zone1_w = int(W_track * 0.38)
    lbl_pad_l = 20 if vertical_format else 32
    max_label_w = zone1_w - lbl_pad_l - 4

    zone2_center_x = content_x + int(W_track * 0.50)
    zone2_w = int(W_track * 0.24)

    zone3_right_x = content_x + int(W_track * 0.96)
    zone3_col_center_x = content_x + int(W_track * 0.855)

    target_pill1_w = int(W_track * (0.74 if vertical_format else 0.74))
    cur_pill1_w = max(int(target_pill1_w * bar_growth), 1)

    c2_ratio = max(values[1] / max_val if len(values) > 1 else 0.72, 0.40)
    target_pill2_w = int(W_track * min(c2_ratio * 0.65, 0.52))
    cur_pill2_w = max(int(target_pill2_w * bar_growth), 1)

    f_fps = resolve_system_font(28 if vertical_format else 34, weight="bold")
    disp_val1 = int(round(values[0] * bar_growth)) if len(values) > 0 else 112
    disp_val2 = int(round(values[1] * bar_growth)) if len(values) > 1 else 81

    # -------------------------------------------------------------
    # 3. Z-INDEX LOWEST IN CARD: Telemetry Grid Lines (ALWAYS BEHIND BARS)
    # Opacity rgba(255, 255, 255, 0.04) -> alpha 10
    # Aligned to column centers: zone2_center_x, zone3_col_center_x, content_x + W_track
    # -------------------------------------------------------------
    grid_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(grid_layer)
    grid_alpha = int(10 * card_alpha)
    for x_g in [zone2_center_x, zone3_col_center_x, content_x + W_track]:
        g_draw.line([(x_g, grid_top), (x_g, grid_bottom)], fill=(255, 255, 255, grid_alpha), width=1)
    g_draw.line([(content_x, grid_bottom), (content_x + inner_w, grid_bottom)], fill=(255, 255, 255, grid_alpha), width=1)
    canvas = Image.alpha_composite(canvas, grid_layer)

    # -------------------------------------------------------------
    # 4. HEADER SECTION & TEXT BLOOM
    # -------------------------------------------------------------
    f_sub = resolve_system_font(22 if vertical_format else 34, weight="light")
    f_title_vs = resolve_system_font(24 if vertical_format else 36, weight="regular")
    f_pill = resolve_system_font(14 if vertical_format else 18, weight="bold")
    f_col = resolve_system_font(14 if vertical_format else 16, weight="light")

    # A) Text Glow / Bloom for Title (GaussianBlur radius=12, opacity 45%)
    y_hl = content_y + (38 if vertical_format else 44)
    title_glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tg_draw = ImageDraw.Draw(title_glow_layer)
    glow_title_alpha = int(255 * 0.45 * card_alpha)

    if not is_two_line_title and " vs " in sub_text:
        part_left, part_right = sub_text.split(" vs ", 1)
        tg_draw.text((content_x, y_hl), part_left, font=f_title_fit, fill=(200, 230, 255, glow_title_alpha), anchor="lt")
        bb_l = f_title_fit.getbbox(part_left)
        wl = bb_l[2] - bb_l[0]
        x_vs = content_x + wl + 16
        tg_draw.text((x_vs, y_hl + (6 if vertical_format else 10)), "vs", font=f_title_vs, fill=(200, 230, 255, int(glow_title_alpha * 0.6)), anchor="lt")
        bb_vs = f_title_vs.getbbox("vs")
        w_vs = bb_vs[2] - bb_vs[0]
        x_r = x_vs + w_vs + 16
        tg_draw.text((x_r, y_hl), part_right, font=f_title_fit, fill=(200, 230, 255, glow_title_alpha), anchor="lt")
    elif is_two_line_title:
        line_spacing = title_sz + 4
        for idx, tl in enumerate(title_lines):
            tg_draw.text((content_x, y_hl + idx * line_spacing), tl, font=f_title_fit, fill=(200, 230, 255, glow_title_alpha), anchor="lt")
    else:
        tg_draw.text((content_x, y_hl), title_lines[0], font=f_title_fit, fill=(200, 230, 255, glow_title_alpha), anchor="lt")

    canvas = Image.alpha_composite(canvas, title_glow_layer.filter(ImageFilter.GaussianBlur(radius=12)))

    # B) Crisp Header Typography
    header_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    h_draw = ImageDraw.Draw(header_layer)

    # Subtitle: GAMING PERFORMANCE with spaced tracking (rgba(255, 255, 255, 0.55))
    subtitle_text = (chart_data.title or "GAMING PERFORMANCE").upper()
    x_track = content_x
    for ch in subtitle_text:
        h_draw.text((x_track, content_y), ch, font=f_sub, fill=(255, 255, 255, int(140 * card_alpha)), anchor="lt")
        bb_ch = f_sub.getbbox(ch)
        x_track += (bb_ch[2] - bb_ch[0]) + 4

    # Crisp Headline
    if not is_two_line_title and " vs " in sub_text:
        h_draw.text((content_x, y_hl), part_left, font=f_title_fit, fill=(255, 255, 255, int(255 * card_alpha)), anchor="lt")
        h_draw.text((x_vs, y_hl + (6 if vertical_format else 10)), "vs", font=f_title_vs, fill=(255, 255, 255, int(153 * card_alpha)), anchor="lt")
        h_draw.text((x_r, y_hl), part_right, font=f_title_fit, fill=(255, 255, 255, int(255 * card_alpha)), anchor="lt")
    elif is_two_line_title:
        line_spacing = title_sz + 4
        for idx, tl in enumerate(title_lines):
            h_draw.text((content_x, y_hl + idx * line_spacing), tl, font=f_title_fit, fill=(255, 255, 255, int(255 * card_alpha)), anchor="lt")
    else:
        h_draw.text((content_x, y_hl), title_lines[0], font=f_title_fit, fill=(255, 255, 255, int(255 * card_alpha)), anchor="lt")

    # Preset Pill (1080p ULTRA • CYBERPUNK 2077) - rgba(255, 255, 255, 0.14) + border rgba(255, 255, 255, 0.3)
    preset_label = chart_data.preset_pill or "1080p ULTRA • CYBERPUNK 2077"
    bb_p = f_pill.getbbox(preset_label)
    pw = (bb_p[2] - bb_p[0]) + (26 if vertical_format else 38)
    ph = 34 if vertical_format else 40
    px = cur_x1 - pad_x - pw
    py = content_y if vertical_format else (content_y + 12)
    h_draw.rounded_rectangle(
        [px, py, px + pw, py + ph],
        radius=ph // 2,
        fill=(255, 255, 255, int(36 * card_alpha)),
        outline=(255, 255, 255, int(76 * card_alpha)),
        width=1,
    )
    h_draw.text(
        (px + pw // 2, py + ph // 2),
        preset_label,
        font=f_pill,
        fill=(255, 255, 255, int(230 * card_alpha)),
        anchor="mm",
    )

    # Column Subheaders - Aligned horizontally to exact column centers:
    # AVG FPS over zone3_col_center_x, % DIFFERENCE over zone2_center_x
    h_draw.text((zone3_col_center_x, grid_top + 10), f"AVG {unit_str}", font=f_col, fill=(255, 255, 255, int(102 * card_alpha)), anchor="mm")
    h_draw.text((zone2_center_x, grid_top + 10), "% DIFFERENCE", font=f_col, fill=(255, 255, 255, int(102 * card_alpha)), anchor="mm")
    canvas = Image.alpha_composite(canvas, header_layer)

    # -------------------------------------------------------------
    # 5. BACKGROUND TRACK CONTAINERS (Translucent Smoky Glass rgba(255,255,255,0.07))
    # -------------------------------------------------------------
    track_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    t_draw = ImageDraw.Draw(track_layer)
    track_alpha_fill = int(18 * card_alpha)
    track_alpha_stroke = int(46 * card_alpha)

    # Row 1 Track Container (Full Width W_track)
    t_draw.rounded_rectangle(
        [content_x, bars_start_y, content_x + W_track, bars_start_y + bar_h],
        radius=track_radius,
        fill=(255, 255, 255, track_alpha_fill),
        outline=(255, 255, 255, track_alpha_stroke),
        width=1,
    )

    # Row 2 Track Container (Full Width W_track)
    y_bar2 = bars_start_y + row_gap
    t_draw.rounded_rectangle(
        [content_x, y_bar2, content_x + W_track, y_bar2 + bar_h],
        radius=track_radius,
        fill=(255, 255, 255, track_alpha_fill),
        outline=(255, 255, 255, track_alpha_stroke),
        width=1,
    )
    canvas = Image.alpha_composite(canvas, track_layer)

    # -------------------------------------------------------------
    # 6. BENCHMARK BARS (Drop Shadow Depth + Colored Glow + 3D Elevation)
    # -------------------------------------------------------------
    # ROW 1 (Winner Bar)
    if cur_pill1_w >= bar_h:
        # A) 3D Drop Shadow
        shadow1_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        s1_draw = ImageDraw.Draw(shadow1_layer)
        s1_alpha = int(165 * min(bar_growth * 1.5, 1.0) * card_alpha)
        s1_draw.rounded_rectangle(
            [content_x + 6, bars_start_y + 10, content_x + cur_pill1_w + 6, bars_start_y + bar_h + 10],
            radius=track_radius,
            fill=(0, 5, 20, s1_alpha),
        )
        shadow1_blurred = shadow1_layer.filter(ImageFilter.GaussianBlur(radius=16))
        canvas = Image.alpha_composite(canvas, shadow1_blurred)

        # B) Directional Colored Glow: #00D8FF opacity 70% with Gaussian Blur 28px
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        gp_draw = ImageDraw.Draw(glow_layer)
        glow_alpha = int((178 + 30 * pulse_glow) * min(bar_growth * 1.5, 1.0) * card_alpha)
        gp_draw.rounded_rectangle(
            [content_x, bars_start_y, content_x + cur_pill1_w, bars_start_y + bar_h],
            radius=track_radius,
            fill=(0, 216, 255, glow_alpha),
        )
        glow_blurred = glow_layer.filter(ImageFilter.GaussianBlur(radius=28))
        canvas = Image.alpha_composite(canvas, glow_blurred)

        # C) Winner Pill: Cyan-to-Sapphire Gradient + Specular Upper Third
        pill1_img = build_winner_bar(cur_pill1_w, bar_h, track_radius)
        pill1_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pill1_layer.alpha_composite(pill1_img, (content_x, bars_start_y))
        canvas = Image.alpha_composite(canvas, pill1_layer)

    # ROW 2 (Runner-up Bar)
    if cur_pill2_w >= bar_h:
        # A) Soft Shadow
        shadow2_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(shadow2_layer).rounded_rectangle(
            [content_x + 6, y_bar2 + 4, content_x + cur_pill2_w + 14, y_bar2 + bar_h + 4],
            radius=track_radius,
            fill=(0, 0, 0, int(95 * card_alpha)),
        )
        shadow2_blurred = shadow2_layer.filter(ImageFilter.GaussianBlur(radius=10))
        canvas = Image.alpha_composite(canvas, shadow2_blurred)

        # B) Runner-up Pill: Translucent smoky blue-gray glass
        pill2_img = build_runner_up_bar(cur_pill2_w, bar_h, track_radius)
        pill2_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        pill2_layer.alpha_composite(pill2_img, (content_x, y_bar2))
        canvas = Image.alpha_composite(canvas, pill2_layer)

    # -------------------------------------------------------------
    # 7. TYPOGRAPHY AND BADGES (Text Bloom & Zero-Collision Partitioning)
    # -------------------------------------------------------------
    y_center1 = bars_start_y + (bar_h // 2)
    y_center2 = y_bar2 + (bar_h // 2)
    text_alpha = int(255 * card_alpha)

    # Helper function to render Zone 1 label with parentheses splitting
    def render_zone1_label(
        draw_obj,
        text_content: str,
        y_c: int,
        alpha_val: int,
        is_bloom: bool = False,
        bloom_color=(255, 255, 255),
    ):
        match = re.match(r"^([^(]+?)\s*(\([^)]+\))\s*$", text_content)
        if match:
            n_part = match.group(1).strip()
            s_part = match.group(2).strip()
            n_lines, f_n, _ = fit_text(n_part, max_width=max_label_w, max_lines=1, start_size=24 if vertical_format else 28, min_size=15, weight="bold")
            s_lines, f_s, _ = fit_text(s_part, max_width=max_label_w, max_lines=1, start_size=18 if vertical_format else 22, min_size=13, weight="medium")
            nt = n_lines[0] if n_lines else n_part
            st = s_lines[0] if s_lines else s_part
            y1 = y_c - (12 if vertical_format else 14)
            y2 = y_c + (13 if vertical_format else 15)
            c1 = (*bloom_color[:3], int(alpha_val * (0.40 if is_bloom else 1.0)))
            c2 = (*bloom_color[:3], int(alpha_val * (0.28 if is_bloom else 0.70)))
            draw_obj.text((content_x + lbl_pad_l, y1), nt, font=f_n, fill=c1, anchor="lm")
            draw_obj.text((content_x + lbl_pad_l, y2), st, font=f_s, fill=c2, anchor="lm")
        else:
            lines, font, _ = fit_text(text_content, max_width=max_label_w, max_lines=1, start_size=26 if vertical_format else 32, min_size=16, weight="bold")
            lt = lines[0] if lines else text_content
            col = (*bloom_color[:3], int(alpha_val * (0.40 if is_bloom else 1.0)))
            draw_obj.text((content_x + lbl_pad_l, y_c), lt, font=font, fill=col, anchor="lm")

    # A) TEXT BLOOM LAYER
    text_bloom_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    tb_draw = ImageDraw.Draw(text_bloom_layer)

    # Row 1 Zone 1 Bloom
    lbl1_text = labels[0] if len(labels) > 0 else "16GB VRAM"
    render_zone1_label(tb_draw, lbl1_text, y_center1, text_alpha, is_bloom=True, bloom_color=(255, 255, 255))

    # Row 1 Zone 3 FPS Bloom
    tb_draw.text(
        (zone3_right_x, y_center1),
        f"{disp_val1} {unit_str}",
        font=f_fps,
        fill=(180, 245, 255, int(255 * 0.60 * card_alpha)),
        anchor="rm",
    )

    # Row 1 Zone 2 Badge Bloom (Strictly invisible until bar_growth > 0.55)
    if bar_growth <= 0.55:
        effective_badge_alpha = 0.0
    else:
        p_growth = min((bar_growth - 0.55) / 0.30, 1.0)
        effective_badge_alpha = badge_alpha * p_growth

    badge_str = chart_data.winner_badge or "+38% FASTER"
    b_lines, f_badge, _ = fit_text(badge_str, max_width=zone2_w - 4, max_lines=1, start_size=28 if vertical_format else 34, min_size=16, weight="black")
    b_text = b_lines[0] if b_lines else badge_str

    if effective_badge_alpha > 0.01 and cur_pill1_w > bar_h:
        tb_draw.text(
            (zone2_center_x, y_center1),
            b_text,
            font=f_badge,
            fill=(180, 245, 255, int(255 * 0.60 * effective_badge_alpha)),
            anchor="mm",
        )

    bloom1_blurred = text_bloom_layer.filter(ImageFilter.GaussianBlur(radius=10))
    canvas = Image.alpha_composite(canvas, bloom1_blurred)

    # B) CRISP FOREGROUND TEXTS
    txt_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    t_draw = ImageDraw.Draw(txt_layer)

    # Row 1 Zone 1 Foreground
    render_zone1_label(t_draw, lbl1_text, y_center1, text_alpha, is_bloom=False)

    # Row 1 Zone 2 Badge Foreground (anchor="mm" at center 50%)
    if effective_badge_alpha > 0.01 and cur_pill1_w > bar_h:
        b_alpha_int = int(255 * effective_badge_alpha)
        t_draw.text((zone2_center_x + 2, y_center1 + 2), b_text, font=f_badge, fill=(0, 40, 90, int(130 * effective_badge_alpha)), anchor="mm")
        t_draw.text((zone2_center_x, y_center1), b_text, font=f_badge, fill=(255, 255, 255, b_alpha_int), anchor="mm")

    # Row 1 Zone 3 FPS Metric (anchor="rm" at right edge 96%)
    t_draw.text(
        (zone3_right_x, y_center1),
        f"{disp_val1} {unit_str}",
        font=f_fps,
        fill=(255, 255, 255, text_alpha),
        anchor="rm",
    )

    # Row 2 Zone 1 Label (Medium weight, 70% opacity)
    lbl2_text = labels[1] if len(labels) > 1 else "8GB VRAM"
    render_zone1_label(t_draw, lbl2_text, y_center2, int(180 * card_alpha), is_bloom=False)

    # Row 2 Zone 3 FPS Metric (anchor="rm" at right edge 96%)
    t_draw.text(
        (zone3_right_x, y_center2),
        f"{disp_val2} {unit_str}",
        font=f_fps,
        fill=(255, 255, 255, int(166 * card_alpha)),
        anchor="rm",
    )

    canvas = Image.alpha_composite(canvas, txt_layer)
    return canvas


def render_benchmark_chart(
    chart_data: ChartData,
    output_path: Path,
    vertical_format: bool = False,
) -> Path:
    """Renders the master high-resolution static frame of the Apple Liquid Glass benchmark card."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas = render_liquid_glass_benchmark_frame(
        chart_data=chart_data,
        card_alpha=1.0,
        bar_growth=1.0,
        badge_scale=1.0,
        badge_alpha=1.0,
        pulse_glow=0.4,
        time_sec=2.0,
        vertical_format=vertical_format,
    )
    # Save as RGB to permanently prevent any external viewer interpreting alpha as white
    rgb_master = canvas.convert("RGB")
    rgb_master.save(output_path, format="PNG", optimize=True)
    logger.info("Apple Liquid Glass benchmark chart rendered [%s]: %s", "9:16 Shorts" if vertical_format else "16:9", output_path.name)
    return output_path


def elegant_spring_ease(p: float) -> float:
    """Smooth elastic spring ease-out with soft deceleration and gentle settle."""
    clamped = max(min(p, 1.0), 0.0)
    if clamped >= 1.0:
        return 1.0
    return 1.0 - math.exp(-5.2 * clamped) * math.cos(2.2 * clamped)


def ease_out_back(x: float, c1: float = 1.4) -> float:
    """Smooth spring overshoot ease-out for badge pop."""
    clamped = max(min(x, 1.0), 0.0)
    c3 = c1 + 1.0
    return 1.0 + c3 * math.pow(clamped - 1.0, 3) + c1 * math.pow(clamped - 1.0, 2)


def ease_out_cubic(x: float) -> float:
    """Smooth cubic deceleration curve."""
    return 1.0 - math.pow(1.0 - max(min(x, 1.0), 0.0), 3)


def render_animated_benchmark_video(
    chart_data: ChartData,
    audio_path: Path,
    output_video_path: Path,
    duration_sec: float = 4.0,
    fps: int = 60,
    vertical_format: bool = False,
    subtitles_ass_path: Optional[Path] = None,
) -> Path:
    """Renders a premier 60 FPS Apple Liquid Glass video with continuous dynamic liquid mesh and spring motion.

    Timeline:
    - Frames 0 - 25 (0.00s - 0.42s): Floating glass card and tracks appear with smooth backdrop blur fade.
    - Frames 25 - 135 (0.42s - 2.25s): Liquid bars grow with spring physics ease-out (1.83s deployment duration).
                                      Real-time numeric FPS counter smoothly rolls up.
    - Frames 120 - 155 (2.00s - 2.58s): Winner '+38% FASTER' badge blooms with radiant cyan outer glow.
    - Frames 155 - 240 (2.58s - 4.00s): Bars remain anchored with breathing neon pulse, while background orbs
                                      continue their organic fluid flow throughout all 240 frames.
    """
    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    W, H = (1080, 1920) if vertical_format else (1920, 1080)
    total_frames = int(duration_sec * fps)

    logger.info(
        "Rendering animated Apple Liquid Glass video (%d frames @ %dfps, %s)...",
        total_frames, fps, "1080x1920" if vertical_format else "1920x1080"
    )

    # Spawn FFmpeg with rawvideo rgb24 stdin pipe to eliminate any alpha misinterpretation
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}",
        "-r", str(fps),
        "-i", "-",
    ]
    if audio_path and Path(audio_path).exists():
        cmd.extend(["-i", str(audio_path)])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])

    cmd.extend(["-t", f"{duration_sec:.2f}"])
    if subtitles_ass_path and Path(subtitles_ass_path).exists():
        logger.info("Burning synchronized ASS subtitles: %s", subtitles_ass_path)
        cmd.extend(["-vf", f"ass={subtitles_ass_path}"])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_video_path),
    ])

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    for frame_idx in range(total_frames):
        t_sec = frame_idx / float(fps)

        # 1. Frames 0 - 25: Card entrance fade
        if frame_idx < 25:
            card_alpha = ease_out_cubic(frame_idx / 25.0)
            bar_growth = 0.0
            badge_scale = 0.0
            badge_alpha = 0.0
            pulse_glow = 0.0

        # 2. Frames 25 - 135: Bar growth via Spring Physics (~1.83s duration)
        elif frame_idx < 135:
            card_alpha = 1.0
            p_bar = (frame_idx - 25) / 110.0
            bar_growth = elegant_spring_ease(p_bar)

            # Badge starts emerging near bar completion (frame 120+)
            if frame_idx >= 120:
                p_badge = (frame_idx - 120) / 25.0
                badge_scale = min(ease_out_back(p_badge, c1=1.4), 1.05)
                badge_alpha = min(p_badge * 2.0, 1.0)
            else:
                badge_scale = 0.0
                badge_alpha = 0.0
            pulse_glow = 0.0

        # 3. Frames 135 - 160: Badge settle & Peak Glow
        elif frame_idx < 160:
            card_alpha = 1.0
            bar_growth = 1.0
            badge_scale = 1.0
            badge_alpha = 1.0
            pulse_glow = (frame_idx - 135) / 25.0

        # 4. Frames 160 - 240: Hold & Organic Liquid Breathing
        else:
            card_alpha = 1.0
            bar_growth = 1.0
            badge_scale = 1.0
            badge_alpha = 1.0
            t_pulse = (frame_idx - 160) / max(total_frames - 160, 1)
            pulse_glow = 0.5 + 0.5 * math.sin(t_pulse * math.pi * 3)

        frame = render_liquid_glass_benchmark_frame(
            chart_data=chart_data,
            card_alpha=card_alpha,
            bar_growth=bar_growth,
            badge_scale=badge_scale,
            badge_alpha=badge_alpha,
            pulse_glow=pulse_glow,
            time_sec=t_sec,
            vertical_format=vertical_format,
            cached_bg=None,  # Continuous live fluid background
        )

        # Convert to RGB to ensure fully opaque, correct color blending for FFmpeg
        rgb_frame = frame.convert("RGB")
        try:
            proc.stdin.write(rgb_frame.tobytes())
        except (BrokenPipeError, IOError):
            logger.warning("FFmpeg closed input pipe at frame %d/%d.", frame_idx, total_frames)
            break

    try:
        proc.stdin.close()
    except Exception:
        pass
    stderr = proc.stderr.read().decode("utf-8") if proc.stderr else ""
    proc.wait()

    if proc.returncode != 0:
        logger.error("FFmpeg rawvideo pipeline failed:\n%s", stderr)
        raise RuntimeError(f"FFmpeg animated render failed: {stderr[-300:]}")

    logger.info("Apple Liquid Glass animated video encoded successfully: %s", output_video_path.name)
    return output_video_path


def generate_glass_whoosh_sfx(output_path: Path, duration_sec: float = 0.5) -> Path:
    """Generates a subtle high-tech crystalline glass whoosh / chime transition SFX at -18 dB using FFmpeg."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = shutil.which("ffmpeg") or str(Path(sys.executable).parent / "ffmpeg") or "ffmpeg"

    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", f"anoisesrc=c=pink:r=44100:d={duration_sec:.2f}",
        "-f", "lavfi", "-i", f"sine=f=2200:r=44100:d={duration_sec:.2f}",
        "-filter_complex",
        "[0:a]bandpass=f=3000:w=1200,volume=0.25[n];"
        "[1:a]volume=0.15[s];"
        "[n][s]amix=inputs=2:dropout_transition=0,afade=t=in:ss=0:d=0.03,afade=t=out:st=0.15:d=0.35,volume=0.12[sfx]",
        "-map", "[sfx]",
        "-t", f"{duration_sec:.2f}",
        "-c:a", "libmp3lame", "-b:a", "192k",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return output_path


def render_apple_liquid_glass_cta_frame(
    card_alpha: float = 1.0,
    card_scale: float = 1.0,
    pulse_glow: float = 0.0,
    time_sec: float = 0.0,
    headline_highlight: str = "SUBSCRIBE",
    headline_rest: str = "FOR DAILY VERDICTS",
    sub_text: str = "Unfiltered PC Hardware Telemetry & Benchmarks",
    vertical_format: bool = True,
    bg_image: Optional[Image.Image] = None,
) -> Image.Image:
    """Renders a single frame of the Apple Liquid Glass Call to Action (CTA) card.

    Strictly conforms to YouTube Shorts Safe Zone [Y=800 to Y=1100], placed at Y_c = 950.
    Card: 860x270 px (vertical).
    """
    W, H = (1080, 1920) if vertical_format else (1920, 1080)
    canvas = bg_image.copy() if bg_image else create_dynamic_liquid_mesh(W, H, t=time_sec)

    if card_alpha <= 0.01 or card_scale <= 0.05:
        return canvas

    base_w = 860 if vertical_format else 920
    base_h = 270 if vertical_format else 280
    center_x = W // 2
    center_y = 950 if vertical_format else 540

    cur_w = max(10, int(base_w * card_scale))
    cur_h = max(10, int(base_h * card_scale))
    x0 = center_x - cur_w // 2
    y0 = center_y - cur_h // 2
    x1 = x0 + cur_w
    y1 = y0 + cur_h
    radius = int(38 * card_scale)

    # 1. Base Glass Card (translucent frosted glass, 30px blur, specular edge)
    canvas = draw_true_liquid_glass_card(canvas, (x0, y0, x1, y1), radius=radius, card_alpha=card_alpha)

    # 2. Perimeter Pulse Bloom (breathing animation)
    if pulse_glow > 0.05 and card_alpha > 0.1:
        glow_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(glow_layer)
        glow_alpha = int(90 * pulse_glow * card_alpha)
        g_draw.rounded_rectangle(
            [x0 - 4, y0 - 4, x1 + 4, y1 + 4],
            radius=radius + 4,
            outline=(0, 245, 255, glow_alpha),
            width=4,
        )
        canvas = Image.alpha_composite(canvas, glow_layer.filter(ImageFilter.GaussianBlur(radius=16)))

    # 3. Card Inner Content Buffer (size base_w x base_h)
    card_content = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))
    cc_draw = ImageDraw.Draw(card_content)

    # A. Top Community Pill
    f_pill = resolve_system_font(13, weight="bold")
    pill_txt = "SILICON VERDICT • COMMUNITY"
    bb_pt = f_pill.getbbox(pill_txt)
    pw = (bb_pt[2] - bb_pt[0]) + 40
    ph = 26
    px0 = (base_w - pw) // 2
    py0 = 24
    cc_draw.rounded_rectangle(
        [px0, py0, px0 + pw, py0 + ph],
        radius=ph // 2,
        fill=(255, 255, 255, 22),
        outline=(0, 245, 255, 130),
        width=1,
    )
    cc_draw.ellipse([px0 + 12, py0 + ph // 2 - 3, px0 + 18, py0 + ph // 2 + 3], fill=(0, 245, 255, 255))
    cc_draw.text((px0 + 26, py0 + ph // 2), pill_txt, font=f_pill, fill=(255, 255, 255, 235), anchor="lm")

    # B. Emblem & Notification Bell Icon
    cx_emb = 82
    cy_emb = 142
    r_emb = 36
    cc_draw.ellipse(
        [cx_emb - r_emb, cy_emb - r_emb, cx_emb + r_emb, cy_emb + r_emb],
        fill=(0, 245, 255, 34),
        outline=(0, 245, 255, 150),
        width=1,
    )

    r_bell = 20
    cc_draw.ellipse([cx_emb - 3, cy_emb - r_bell - 5, cx_emb + 3, cy_emb - r_bell + 1], fill=(0, 245, 255, 255))
    bell_poly = [
        (cx_emb, cy_emb - r_bell),
        (cx_emb - int(r_bell * 0.65), cy_emb - int(r_bell * 0.2)),
        (cx_emb - r_bell, cy_emb + r_bell - 6),
        (cx_emb + r_bell, cy_emb + r_bell - 6),
        (cx_emb + int(r_bell * 0.65), cy_emb - int(r_bell * 0.2)),
    ]
    cc_draw.polygon(bell_poly, fill=(255, 255, 255, 255))
    cc_draw.rounded_rectangle(
        [cx_emb - r_bell - 2, cy_emb + r_bell - 6, cx_emb + r_bell + 2, cy_emb + r_bell - 2],
        radius=2,
        fill=(0, 245, 255, 255),
    )
    cc_draw.ellipse([cx_emb - 4, cy_emb + r_bell - 2, cx_emb + 4, cy_emb + r_bell + 5], fill=(255, 255, 255, 255))

    # C. Typography (SUBSCRIBE FOR DAILY VERDICTS)
    f_highlight = resolve_system_font(28, weight="black")
    f_rest = resolve_system_font(28, weight="bold")
    f_sub = resolve_system_font(17, weight="medium")

    tx0 = 142
    ty0 = 126

    # Soft text bloom behind highlight word
    bloom_layer = Image.new("RGBA", (base_w, base_h), (0, 0, 0, 0))
    b_draw = ImageDraw.Draw(bloom_layer)
    b_draw.text((tx0, ty0), headline_highlight, font=f_highlight, fill=(0, 245, 255, 170), anchor="lm")
    blurred_bloom = bloom_layer.filter(ImageFilter.GaussianBlur(radius=10))
    card_content = Image.alpha_composite(card_content, blurred_bloom)

    cc_draw = ImageDraw.Draw(card_content)
    cc_draw.text((tx0, ty0), headline_highlight, font=f_highlight, fill=(0, 245, 255, 255), anchor="lm")
    bb_hi = f_highlight.getbbox(headline_highlight)
    w_hi = bb_hi[2] - bb_hi[0]
    cc_draw.text((tx0 + w_hi + 10, ty0), headline_rest, font=f_rest, fill=(255, 255, 255, 255), anchor="lm")
    cc_draw.text((tx0, ty0 + 32), sub_text, font=f_sub, fill=(215, 235, 255, 215), anchor="lm")

    # D. Bottom Hint
    f_hint = resolve_system_font(12, weight="bold")
    hint_txt = "TAP BELL ICON TO NEVER MISS A DROP"
    cc_draw.text((base_w // 2, base_h - 24), hint_txt, font=f_hint, fill=(0, 245, 255, 185), anchor="mm")

    # 4. Scale and Composite Content Buffer
    if card_scale != 1.0:
        scaled_content = card_content.resize((cur_w, cur_h), resample=Image.Resampling.BICUBIC)
    else:
        scaled_content = card_content

    if card_alpha < 0.99:
        alpha_channel = np.array(scaled_content.getchannel("A"), dtype=np.float32) * card_alpha
        scaled_content.putalpha(Image.fromarray(alpha_channel.astype(np.uint8)))

    content_layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    content_layer.paste(scaled_content, (x0, y0))
    canvas = Image.alpha_composite(canvas, content_layer)
    return canvas


def render_animated_cta_video(
    audio_path: Optional[Path],
    output_video_path: Path,
    duration_sec: float = 2.5,
    fps: int = 60,
    vertical_format: bool = True,
    subtitles_ass_path: Optional[Path] = None,
    sfx_path: Optional[Path] = None,
    headline_highlight: str = "SUBSCRIBE",
    headline_rest: str = "FOR DAILY VERDICTS",
    sub_text: str = "Unfiltered PC Hardware Telemetry & Benchmarks",
) -> Path:
    """Renders 60 FPS Apple Liquid Glass Call to Action (CTA) video scene.

    - 0.0s - 0.25s: Spring ease-out entrance (scale 0.75 -> 1.05 -> 1.0).
    - 0.25s - 2.25s: Sustained hold with subtle perimeter breathing pulse.
    - 2.25s - 2.50s: Rapid fade-out giving immediate way to final verdict.
    """
    output_video_path = Path(output_video_path)
    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    W, H = (1080, 1920) if vertical_format else (1920, 1080)
    total_frames = int(duration_sec * fps)

    logger.info(
        "Rendering animated Apple Liquid Glass CTA scene (%d frames @ %dfps, %.2fs)...",
        total_frames, fps, duration_sec
    )

    ffmpeg_bin = shutil.which("ffmpeg") or str(Path(sys.executable).parent / "ffmpeg") or "ffmpeg"

    cmd = [
        ffmpeg_bin, "-y",
        "-f", "rawvideo",
        "-pix_fmt", "rgb24",
        "-s", f"{W}x{H}",
        "-r", str(fps),
        "-i", "-",
    ]
    if audio_path and Path(audio_path).exists():
        cmd.extend(["-i", str(audio_path)])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo"])

    cmd.extend(["-t", f"{duration_sec:.2f}"])
    if subtitles_ass_path and Path(subtitles_ass_path).exists():
        logger.info("Burning synchronized ASS subtitles: %s", subtitles_ass_path)
        cmd.extend(["-vf", f"ass={subtitles_ass_path}"])

    cmd.extend([
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        str(output_video_path),
    ])

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

    n_entrance = int(min(0.25, duration_sec * 0.12) * fps)
    n_exit = int(min(0.25, duration_sec * 0.10) * fps)

    for frame_idx in range(total_frames):
        t_sec = frame_idx / float(fps)
        if frame_idx < n_entrance:
            p = frame_idx / float(max(n_entrance, 1))
            card_scale = min(ease_out_back(p, c1=1.15), 1.05)
            card_alpha = ease_out_cubic(p)
            pulse_glow = 0.0
        elif frame_idx < total_frames - n_exit:
            card_scale = 1.0
            card_alpha = 1.0
            t_hold = (frame_idx - n_entrance) / max(1.0, float(total_frames - n_exit - n_entrance))
            pulse_glow = 0.5 + 0.5 * math.sin(t_hold * math.pi * 4)
        else:
            p_exit = (frame_idx - (total_frames - n_exit)) / float(max(n_exit, 1))
            card_scale = 1.0 - 0.05 * p_exit
            card_alpha = max(0.0, 1.0 - ease_out_cubic(p_exit))
            pulse_glow = 0.0

        frame = render_apple_liquid_glass_cta_frame(
            card_alpha=card_alpha,
            card_scale=card_scale,
            pulse_glow=pulse_glow,
            time_sec=t_sec,
            headline_highlight=headline_highlight,
            headline_rest=headline_rest,
            sub_text=sub_text,
            vertical_format=vertical_format,
        )
        rgb_frame = frame.convert("RGB")
        try:
            proc.stdin.write(rgb_frame.tobytes())
        except (BrokenPipeError, IOError):
            logger.warning("FFmpeg closed input pipe at frame %d/%d.", frame_idx, total_frames)
            break

    try:
        proc.stdin.close()
    except Exception:
        pass
    stderr = proc.stderr.read().decode("utf-8") if proc.stderr else ""
    proc.wait()

    if proc.returncode != 0:
        logger.error("FFmpeg rawvideo CTA pipeline failed:\n%s", stderr)
        raise RuntimeError(f"FFmpeg animated CTA render failed: {stderr[-300:]}")

    logger.info("Apple Liquid Glass CTA video encoded: %s", output_video_path.name)
    return output_video_path
