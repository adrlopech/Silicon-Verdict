"""Schematic Tech visual renderer and blueprint infographics generator for Silicon Verdict.

Implements the 'schematic_tech' visual preset:
- Exclusively channel palette: Obsidian Black (#07090E), Midnight Blue (#0F172A),
  Grid Slate (#1E293B), Dark Slate (#334155), Electric Blue (#007AFF),
  Electric Cyan (#38BDF8), Pure White (#FFFFFF), and Cool Gray (#94A3B8).
- Dark technical grid canvas (1080x1920) with subtle radial vignette.
- 2D transparent infographic schematics (datacenters, subsea fiber, EUV optics, network nodes).
- Floating telemetry pills and blueprint cards with crisp vector styling.
- Strictly isolated to category == 'tech_curiosities' (or explicit --preset schematic_tech).
"""
import logging
import math
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFilter

from config.settings import settings
from engine.charts import (
    resolve_system_font,
)

logger = logging.getLogger(__name__)
# Re-export core functions from engine.renderer for unified access
from engine.renderer import (  # noqa: F401
    VideoRenderer,
    create_golden_rule_card,
    create_introductory_dilemma_card,
    create_silicon_specs_card,
    create_vision_pro_hud_pill,
    create_voting_poll_card,
    render_composite_overlay_clip,
)

# ==============================================================================
# 1. CHANNEL PALETTE CONSTANTS (BLUES, GRAYS, WHITES, BLACKS)
# ==============================================================================
COLOR_OBSIDIAN_BG = (7, 9, 14)        # #07090E - Deep obsidian black
COLOR_MIDNIGHT_BLUE = (15, 23, 42)    # #0F172A - Subtle vignette core
COLOR_GRID_SLATE = (30, 41, 59)       # #1E293B - Technical grid lines (32px)
COLOR_LINE_DARK = (51, 65, 85)        # #334155 - Interconnect dark lines & borders
COLOR_ELECTRIC_BLUE = (0, 122, 255)   # #007AFF - Electric pulse blue
COLOR_CYAN_ACCENT = (56, 189, 248)    # #38BDF8 - Electric cyan highlights
COLOR_TEXT_PURE_WHITE = (255, 255, 255)  # #FFFFFF - Primary typography
COLOR_TEXT_MUTED_GRAY = (148, 163, 184) # #94A3B8 - Secondary telemetry & units

ASSETS_SCHEMATICS_DIR = settings.BASE_DIR / "assets" / "schematics"
ASSETS_SCHEMATICS_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 2. CANVAS GENERATOR: DARK TECHNICAL GRID (1080x1920)
# ==============================================================================
def generate_schematic_canvas(
    output_path: Path,
    width: int = 1080,
    height: int = 1920,
    grid_spacing: int = 32,
) -> Path:
    """Generates a 1080x1920 dark obsidian canvas with subtle midnight blue vignette and clean technical grid."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (width, height), (*COLOR_OBSIDIAN_BG, 255))
    draw = ImageDraw.Draw(img)

    # 1. Vignette Gradient: Midnight Blue center/top radiating to Obsidian Black
    center_x = width // 2
    center_y = int(height * 0.38)  # Centered slightly towards upper-middle
    max_radius = math.hypot(width, height) * 0.65

    # Render soft radial gradient using Pillow radial concentric ellipses
    gradient_img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    g_draw = ImageDraw.Draw(gradient_img)

    steps = 40
    for s in range(steps, 0, -1):
        frac = s / steps
        r_x = int(width * 0.65 * frac)
        r_y = int(height * 0.55 * frac)
        alpha = int(140 * (1.0 - frac))
        g_draw.ellipse(
            [center_x - r_x, center_y - r_y, center_x + r_x, center_y + r_y],
            fill=(*COLOR_MIDNIGHT_BLUE, alpha),
        )

    gradient_blurred = gradient_img.filter(ImageFilter.GaussianBlur(radius=36))
    img = Image.alpha_composite(img, gradient_blurred)
    draw = ImageDraw.Draw(img)

    # 2. Clean Technical Grid (32px spacing) in #1E293B
    grid_color = (*COLOR_GRID_SLATE, 160)
    for x in range(0, width, grid_spacing):
        draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
    for y in range(0, height, grid_spacing):
        draw.line([(0, y), (width, y)], fill=grid_color, width=1)

    # 3. Engineering Crosshairs at major intersections (every 128px)
    major_step = grid_spacing * 4
    cross_color = (*COLOR_LINE_DARK, 220)
    for x in range(major_step, width, major_step):
        for y in range(major_step, height, major_step):
            draw.line([(x - 4, y), (x + 4, y)], fill=cross_color, width=1)
            draw.line([(x, y - 4), (x, y + 4)], fill=cross_color, width=1)

    # 4. Blueprint Coordinate Stamps & Precision Markers
    f_stamp = resolve_system_font(12, weight="bold")
    draw.text((36, 42), "SV-SYS // SCHEMATIC 2D", font=f_stamp, fill=(*COLOR_CYAN_ACCENT, 180))
    draw.text((width - 180, 42), "GRID: 32px • 1080x1920", font=f_stamp, fill=(*COLOR_TEXT_MUTED_GRAY, 160))
    draw.text((36, height - 52), "TELEMETRY PRECISION: ±0.01ns", font=f_stamp, fill=(*COLOR_TEXT_MUTED_GRAY, 140))
    draw.text((width - 240, height - 52), "SILICON VERDICT ENGINEERING", font=f_stamp, fill=(*COLOR_CYAN_ACCENT, 160))

    img.save(output_path, format="PNG")
    return output_path


# ==============================================================================
# 3. 2D SCHEMATICS & INFOGRAPHICS LIBRARY (`assets/schematics/`)
# ==============================================================================
def generate_datacenter_speed_of_light_schematic(output_path: Optional[Path] = None) -> Path:
    """Renders a 2D technical diagram showing datacenter optical latency and the speed of light limit."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / "datacenter_speed_of_light.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Datacenter Node A (Left)
    da_x, da_y = 120, 240
    # Datacenter Node B (Right)
    db_x, db_y = 800, 240

    # Draw Dark Server Rack Silhouettes with Cyan LEDs
    def draw_rack(cx: int, cy: int, label: str):
        rw, rh = 130, 220
        rx1, ry1 = cx - rw // 2, cy - rh // 2
        rx2, ry2 = cx + rw // 2, cy + rh // 2
        # Rack body
        draw.rounded_rectangle([rx1, ry1, rx2, ry2], radius=12, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 255), width=2)
        # Rack server unit slots
        for sy in range(ry1 + 18, ry2 - 20, 26):
            draw.line([(rx1 + 10, sy), (rx2 - 10, sy)], fill=(*COLOR_LINE_DARK, 180), width=1)
            # Pulsing LEDs in cyan and blue
            draw.ellipse([rx1 + 16, sy - 4, rx1 + 22, sy + 2], fill=(*COLOR_CYAN_ACCENT, 255))
            draw.ellipse([rx1 + 26, sy - 4, rx1 + 32, sy + 2], fill=(*COLOR_ELECTRIC_BLUE, 220))
        # Label pill below rack
        f_lbl = resolve_system_font(14, weight="bold")
        draw.text((cx, ry2 + 16), label, font=f_lbl, fill=(*COLOR_TEXT_MUTED_GRAY, 230), anchor="mm")

    draw_rack(da_x, da_y, "CLUSTER ALPHA")
    draw_rack(db_x, db_y, "CLUSTER BETA")

    # Interconnecting Fiber Optic Line in Dark Slate
    draw.line([(da_x + 65, da_y), (db_x - 65, db_y)], fill=(*COLOR_LINE_DARK, 255), width=4)

    # Animated Light Pulse in Electric Cyan and Blue
    pulse_start_x = 320
    pulse_end_x = 600
    draw.line([(pulse_start_x, da_y), (pulse_end_x, da_y)], fill=(*COLOR_CYAN_ACCENT, 255), width=6)
    draw.line([(pulse_start_x + 40, da_y), (pulse_end_x - 40, da_y)], fill=(*COLOR_TEXT_PURE_WHITE, 255), width=3)

    # Data Waveform Nodes along cable
    node_xs = [da_x + 65, 280, 460, 640, db_x - 65]
    for nx in node_xs:
        draw.ellipse([nx - 9, da_y - 9, nx + 9, da_y + 9], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_CYAN_ACCENT, 255), width=2)
        draw.ellipse([nx - 4, da_y - 4, nx + 4, da_y + 4], fill=(*COLOR_ELECTRIC_BLUE, 255))

    # Floating Telemetry Callout Pills
    def draw_pill(cx: int, cy: int, text: str, unit: str):
        f_val = resolve_system_font(18, weight="bold")
        f_u = resolve_system_font(14, weight="medium")
        bbox_v = f_val.getbbox(text)
        bbox_u = f_u.getbbox(unit)
        pw = (bbox_v[2] - bbox_v[0]) + (bbox_u[2] - bbox_u[0]) + 38
        ph = 36
        px1, py1 = cx - pw // 2, cy - ph // 2
        px2, py2 = cx + pw // 2, cy + ph // 2
        draw.rounded_rectangle([px1, py1, px2, py2], radius=ph // 2, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 240), width=1)
        # Dot
        draw.ellipse([px1 + 10, cy - 3, px1 + 16, cy + 3], fill=(*COLOR_CYAN_ACCENT, 255))
        # Text
        vx = px1 + 24
        draw.text((vx, cy), text, font=f_val, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="lm")
        draw.text((vx + (bbox_v[2] - bbox_v[0]) + 6, cy), unit, font=f_u, fill=(*COLOR_TEXT_MUTED_GRAY, 220), anchor="lm")

    # Telemetry badges
    draw_pill(460, 150, "v = 200,000", "km/s (n = 1.46)")
    draw_pill(460, 330, "Δt = 5.0", "ns / meter")
    draw_pill(270, 380, "1,200", "km link")
    draw_pill(650, 380, "5.2", "ms RTT latency")

    # Top Header within schematic
    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 48), "OPTICAL PROPAGATION IN SILICA FIBER", font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 200), anchor="mm")
    draw.text((460, 72), "RELATIVISTIC LATENCY BOUND ACROSS DATACENTERS", font=f_hdr, fill=(*COLOR_TEXT_MUTED_GRAY, 170), anchor="mm")

    img.save(out, format="PNG")
    return out


def generate_submarine_cable_schematic(output_path: Optional[Path] = None) -> Path:
    """Renders a 2D technical cross-section schematic of a subsea transoceanic fiber cable."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / "submarine_fiber_cable.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = 340, 260

    # Concentric circles representing cable cross-section
    layers = [
        (180, COLOR_LINE_DARK, 2, "POLYETHYLENE OUTER JACKET"),
        (140, COLOR_GRID_SLATE, 2, "HIGH-TENSILE STEEL ARMOR WIRES"),
        (100, COLOR_ELECTRIC_BLUE, 2, "COPPER POWER CONDUCTOR (10kV)"),
        (65, COLOR_MIDNIGHT_BLUE, 2, "WATERPROOF THIXOTROPIC GEL"),
        (30, COLOR_CYAN_ACCENT, 0, "OPTICAL CORE (SILICA GLASS FIBER)"),
    ]

    for radius, color, width, _ in layers:
        r = radius
        if width == 0:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, 240))
        else:
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*COLOR_OBSIDIAN_BG, 200), outline=(*color, 255), width=width)

    # Core optical fibers (small points)
    for angle_deg in range(0, 360, 45):
        rad = math.radians(angle_deg)
        fx = cx + int(14 * math.cos(rad))
        fy = cy + int(14 * math.sin(rad))
        draw.ellipse([fx - 2, fy - 2, fx + 2, fy + 2], fill=(*COLOR_TEXT_PURE_WHITE, 255))

    # Leader callout lines to the right
    labels = [
        (180, "POLYETHYLENE SHEATH", "Biological & pressure protection"),
        (140, "STEEL WIRE ARMOR", "Tensile strength 200 kN"),
        (100, "COPPER CONDUCTOR", "10,000V DC power for repeaters"),
        (65, "THIXOTROPIC GEL BARRIER", "Abyssal hydrophobic sealing"),
        (30, "GLASS OPTICAL FIBERS", "250 Tbps bandwidth capacity"),
    ]

    f_lh = resolve_system_font(14, weight="bold")
    f_ls = resolve_system_font(12, weight="regular")
    start_y = 110
    step_y = 68

    for idx, (rad, title, desc) in enumerate(labels):
        cur_y = start_y + (idx * step_y)
        # Leader line from circle edge to text
        lx_start = cx + int(rad * 0.707)
        ly_start = cy - int(rad * 0.707) if idx < 3 else cy + int(rad * 0.707)
        lx_mid = 550
        lx_end = 580

        draw.line([(lx_start, ly_start), (lx_mid, cur_y + 8), (lx_end, cur_y + 8)], fill=(*COLOR_LINE_DARK, 220), width=1)
        draw.ellipse([lx_start - 3, ly_start - 3, lx_start + 3, ly_start + 3], fill=(*COLOR_CYAN_ACCENT, 255))

        draw.text((lx_end + 10, cur_y), title, font=f_lh, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="lt")
        draw.text((lx_end + 10, cur_y + 18), desc, font=f_ls, fill=(*COLOR_TEXT_MUTED_GRAY, 200), anchor="lt")

    # Header
    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 42), "TRANSOCEANIC SUBSEA CABLE CROSS-SECTION", font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 220), anchor="mm")

    img.save(out, format="PNG")
    return out


def generate_euv_lithography_schematic(output_path: Optional[Path] = None) -> Path:
    """Renders a 2D technical schematic of ASML EUV reflective optical projection."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / "euv_lithography_optics.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # EUV light source (Laser hitting tin droplet at left)
    sx, sy = 140, 260
    draw.ellipse([sx - 18, sy - 18, sx + 18, sy + 18], fill=(*COLOR_ELECTRIC_BLUE, 160), outline=(*COLOR_CYAN_ACCENT, 255), width=2)
    draw.ellipse([sx - 6, sy - 6, sx + 6, sy + 6], fill=(*COLOR_TEXT_PURE_WHITE, 255))

    # Collector Mirror (Curved arc behind tin droplet)
    draw.arc([sx - 80, sy - 90, sx - 20, sy + 90], start=280, end=80, fill=(*COLOR_CYAN_ACCENT, 255), width=4)

    # Multi-layer mirror array bouncing EUV light ray
    ray_points = [(sx, sy), (320, 150), (460, 370), (600, 150), (740, 360), (840, 360)]

    for i in range(len(ray_points) - 1):
        p1 = ray_points[i]
        p2 = ray_points[i + 1]
        draw.line([p1, p2], fill=(*COLOR_CYAN_ACCENT, 240), width=3)

    # Draw Mirror blocks at reflection vertices
    for mx, my in [(320, 150), (460, 370), (600, 150), (740, 360)]:
        draw.rounded_rectangle([mx - 32, my - 8, mx + 32, my + 8], radius=4, fill=(*COLOR_MIDNIGHT_BLUE, 255), outline=(*COLOR_TEXT_PURE_WHITE, 220), width=2)

    # Wafer Stage at final destination
    wx, wy = 840, 360
    draw.rounded_rectangle([wx - 20, wy - 30, wx + 40, wy + 30], radius=6, fill=(*COLOR_MIDNIGHT_BLUE, 255), outline=(*COLOR_CYAN_ACCENT, 255), width=2)
    f_w = resolve_system_font(12, weight="bold")
    draw.text((wx + 10, wy), "WAFER\n2nm", font=f_w, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="mm")

    # Floating Telemetry Callout Pills
    def draw_telemetry(cx: int, cy: int, text: str, unit: str):
        f_val = resolve_system_font(17, weight="bold")
        f_u = resolve_system_font(13, weight="medium")
        bv = f_val.getbbox(text)
        bu = f_u.getbbox(unit)
        pw = (bv[2] - bv[0]) + (bu[2] - bu[0]) + 34
        ph = 34
        draw.rounded_rectangle([cx - pw // 2, cy - ph // 2, cx + pw // 2, cy + ph // 2], radius=ph // 2, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 240), width=1)
        draw.ellipse([cx - pw // 2 + 10, cy - 3, cx - pw // 2 + 16, cy + 3], fill=(*COLOR_CYAN_ACCENT, 255))
        vx = cx - pw // 2 + 24
        draw.text((vx, cy), text, font=f_val, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="lm")
        draw.text((vx + (bv[2] - bv[0]) + 6, cy), unit, font=f_u, fill=(*COLOR_TEXT_MUTED_GRAY, 220), anchor="lm")

    draw_telemetry(240, 380, "λ = 13.5", "nm EUV")
    draw_telemetry(460, 460, "50,000", "tin droplets/s")
    draw_telemetry(680, 80, "R = 70%", "per Mo/Si mirror")

    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 42), "ASML EUV REFLECTIVE OPTICS • EXTREME LIGHT BEAM", font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 220), anchor="mm")

    img.save(out, format="PNG")
    return out


def generate_interconnected_nodes_schematic(output_path: Optional[Path] = None) -> Path:
    """Renders a clean network graph wireframe with pulsing electric blue data packets."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / "interconnected_nodes.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    nodes = [
        (160, 160, "CLUSTER-EU"),
        (460, 120, "CORE-BACKBONE"),
        (760, 180, "CLUSTER-US"),
        (260, 380, "EDGE-GATEWAY-01"),
        (640, 390, "EDGE-GATEWAY-02"),
    ]

    edges = [
        (0, 1), (1, 2), (0, 3), (1, 3), (1, 4), (2, 4), (3, 4)
    ]

    # Draw dark slate edges
    for i, j in edges:
        p1 = (nodes[i][0], nodes[i][1])
        p2 = (nodes[j][0], nodes[j][1])
        draw.line([p1, p2], fill=(*COLOR_LINE_DARK, 240), width=2)

    # Active data packet lines in electric cyan
    active_edges = [(0, 1), (1, 3), (1, 4)]
    for i, j in active_edges:
        p1 = (nodes[i][0], nodes[i][1])
        p2 = (nodes[j][0], nodes[j][1])
        mx = (p1[0] + p2[0]) // 2
        my = (p1[1] + p2[1]) // 2
        draw.line([p1, (mx, my)], fill=(*COLOR_CYAN_ACCENT, 255), width=3)
        draw.ellipse([mx - 4, my - 4, mx + 4, my + 4], fill=(*COLOR_TEXT_PURE_WHITE, 255))

    # Draw nodes
    f_lbl = resolve_system_font(12, weight="bold")
    for x, y, label in nodes:
        draw.ellipse([x - 24, y - 24, x + 24, y + 24], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_CYAN_ACCENT, 255), width=2)
        draw.ellipse([x - 12, y - 12, x + 12, y + 12], fill=(*COLOR_ELECTRIC_BLUE, 220))
        draw.ellipse([x - 4, y - 4, x + 4, y + 4], fill=(*COLOR_TEXT_PURE_WHITE, 255))
        draw.text((x, y + 36), label, font=f_lbl, fill=(*COLOR_TEXT_MUTED_GRAY, 220), anchor="mm")

    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 42), "GLOBAL DISTRIBUTED NETWORK TOPOLOGY & LATENCY", font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 220), anchor="mm")

    img.save(out, format="PNG")
    return out


def generate_gps_relativity_schematic(output_path: Optional[Path] = None) -> Path:
    """Renders a 2D technical diagram showing GPS satellite constellation, relativistic clock drift, and triangulation."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / "gps_relativity_schematic.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Earth curvature at bottom center
    earth_cx, earth_cy = 460, 720
    earth_r = 380
    draw.ellipse(
        [earth_cx - earth_r, earth_cy - earth_r, earth_cx + earth_r, earth_cy + earth_r],
        fill=(*COLOR_MIDNIGHT_BLUE, 220), outline=(*COLOR_LINE_DARK, 255), width=2,
    )

    # User mobile receiver icon on Earth surface
    rx, ry = 460, 345
    draw.rectangle([rx - 14, ry - 22, rx + 14, ry + 12], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_CYAN_ACCENT, 255), width=2)
    draw.ellipse([rx - 22, ry - 30, rx + 22, ry + 20], outline=(*COLOR_ELECTRIC_BLUE, 140), width=1)
    f_rx = resolve_system_font(12, weight="bold")
    draw.text((rx, ry + 28), "RECEIVER (0.0 W)", font=f_rx, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="mm")

    # 4 Satellites in Orbit
    sats = [
        (130, 140, "SV-01 (CESIUM ATOMIC CLOCK)"),
        (350, 100, "SV-02 (RUBIDIUM ATOMIC CLOCK)"),
        (570, 100, "SV-03 (CESIUM ATOMIC CLOCK)"),
        (790, 140, "SV-04 (RUBIDIUM ATOMIC CLOCK)"),
    ]

    for sx, sy, lbl in sats:
        draw.rectangle([sx - 18, sy - 12, sx + 18, sy + 12], fill=(*COLOR_MIDNIGHT_BLUE, 255), outline=(*COLOR_TEXT_PURE_WHITE, 255), width=2)
        draw.rectangle([sx - 44, sy - 8, sx - 20, sy + 8], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_CYAN_ACCENT, 200), width=1)
        draw.rectangle([sx + 20, sy - 8, sx + 44, sy + 8], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_CYAN_ACCENT, 200), width=1)
        draw.line([(sx, sy + 14), (rx, ry - 14)], fill=(*COLOR_LINE_DARK, 180), width=1)
        px = int(sx + (rx - sx) * 0.45)
        py = int(sy + 14 + (ry - 14 - sy) * 0.45)
        draw.ellipse([px - 4, py - 4, px + 4, py + 4], fill=(*COLOR_CYAN_ACCENT, 255))
        draw.text((sx, sy - 24), lbl, font=f_rx, fill=(*COLOR_TEXT_MUTED_GRAY, 220), anchor="mm")

    # Relativity telemetry callouts
    f_p = resolve_system_font(12, weight="bold")
    draw.rounded_rectangle([60, 240, 290, 276], radius=18, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_CYAN_ACCENT, 220), width=1)
    draw.text((175, 258), "EINSTEIN: +38.6 µs / DAY", font=f_p, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    draw.rounded_rectangle([630, 240, 860, 276], radius=18, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_ELECTRIC_BLUE, 220), width=1)
    draw.text((745, 258), "DRIFT WITHOUT FIX: +11.4 km / DAY", font=f_p, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="mm")

    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 38), "ORBITAL TRIANGULATION & RELATIVISTIC CORRECTION", font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 220), anchor="mm")

    img.save(out, format="PNG")
    return out


def generate_faceid_infrared_mesh_schematic(output_path: Optional[Path] = None) -> Path:
    """Renders a 2D technical diagram of Face ID 30,000 infrared dot projection and 3D facial wireframe mesh."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / "faceid_infrared_mesh.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. 3D Wireframe Depth Contour Face Mesh (Top Center)
    face_cx, face_cy = 460, 190
    rows = 6
    cols = 13
    grid_pts = []

    for r in range(rows):
        y_base = 90 + (r * 38)
        row_pts = []
        for c in range(cols):
            x_base = 250 + (c * 35)
            dx = (c - 6) / 6.0
            dy = (r - 2.5) / 2.5
            rad_sq = dx * dx + dy * dy
            relief = math.exp(-rad_sq * 1.5) * 24.0 if rad_sq < 1.4 else 0.0
            py = int(y_base - relief)
            row_pts.append((x_base, py))
            draw.ellipse([x_base - 2, py - 2, x_base + 2, py + 2], fill=(*COLOR_CYAN_ACCENT, 255))
        grid_pts.append(row_pts)

    for r in range(rows):
        for c in range(cols):
            if c < cols - 1:
                draw.line([grid_pts[r][c], grid_pts[r][c + 1]], fill=(*COLOR_LINE_DARK, 180), width=1)
            if r < rows - 1:
                draw.line([grid_pts[r][c], grid_pts[r + 1][c]], fill=(*COLOR_ELECTRIC_BLUE, 140), width=1)

    draw.ellipse([face_cx - 4, face_cy - 20, face_cx + 4, face_cy - 12], fill=(*COLOR_TEXT_PURE_WHITE, 255))
    draw.ellipse([face_cx - 70, face_cy, face_cx - 62, face_cy + 8], fill=(*COLOR_TEXT_PURE_WHITE, 255))
    draw.ellipse([face_cx + 62, face_cy, face_cx + 70, face_cy + 8], fill=(*COLOR_TEXT_PURE_WHITE, 255))

    # 2. TrueDepth Emitter Notch Module
    nw, nh = 420, 64
    nx1, ny1 = 460 - nw // 2, 410
    nx2, ny2 = 460 + nw // 2, ny1 + nh
    draw.rounded_rectangle([nx1, ny1, nx2, ny2], radius=16, fill=(*COLOR_MIDNIGHT_BLUE, 240), outline=(*COLOR_LINE_DARK, 255), width=2)

    # Flood Illuminator (Left)
    draw.ellipse([nx1 + 35, ny1 + 18, nx1 + 65, ny1 + 48], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_CYAN_ACCENT, 200), width=2)
    draw.ellipse([nx1 + 45, ny1 + 28, nx1 + 55, ny1 + 38], fill=(*COLOR_CYAN_ACCENT, 255))
    f_sm = resolve_system_font(11, weight="bold")
    draw.text((nx1 + 50, ny2 + 14), "FLOOD ILLUM.", font=f_sm, fill=(*COLOR_TEXT_MUTED_GRAY, 220), anchor="mm")

    # Infrared Camera (Center)
    draw.ellipse([nx1 + 195, ny1 + 18, nx1 + 225, ny1 + 48], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_ELECTRIC_BLUE, 220), width=2)
    draw.ellipse([nx1 + 205, ny1 + 28, nx1 + 215, ny1 + 38], fill=(*COLOR_TEXT_PURE_WHITE, 255))
    draw.text((nx1 + 210, ny2 + 14), "IR CAMERA", font=f_sm, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    # Dot Projector VCSEL (Right)
    vcsel_x = nx1 + 360
    vcsel_y = ny1 + 33
    draw.ellipse([vcsel_x - 15, vcsel_y - 15, vcsel_x + 15, vcsel_y + 15], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_CYAN_ACCENT, 255), width=2)
    draw.ellipse([vcsel_x - 5, vcsel_y - 5, vcsel_x + 5, vcsel_y + 5], fill=(*COLOR_CYAN_ACCENT, 255))
    draw.text((vcsel_x, ny2 + 14), "VCSEL PROJECTOR", font=f_sm, fill=(*COLOR_TEXT_MUTED_GRAY, 220), anchor="mm")

    # Infrared Beam Rays
    for ray_x in [face_cx - 140, face_cx - 50, face_cx + 50, face_cx + 140]:
        draw.line([(vcsel_x, vcsel_y - 15), (ray_x, 260)], fill=(*COLOR_LINE_DARK, 180), width=1)
        px = int(vcsel_x + (ray_x - vcsel_x) * 0.55)
        py = int(vcsel_y - 15 + (260 - (vcsel_y - 15)) * 0.55)
        draw.ellipse([px - 3, py - 3, px + 3, py + 3], fill=(*COLOR_CYAN_ACCENT, 240))

    # Telemetry Badges
    def draw_badge(x, y, title, val):
        draw.rounded_rectangle([x - 110, y - 18, x + 110, y + 18], radius=18, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_CYAN_ACCENT, 180), width=1)
        f_b = resolve_system_font(11, weight="bold")
        draw.text((x, y), f"{title}: {val}", font=f_b, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    draw_badge(130, 110, "WAVELENGTH", "940 nm")
    draw_badge(130, 160, "VCSEL ARRAY", "30,000 DOTS")
    draw_badge(790, 110, "DEPTH PROFILE", "3D RELIEF")
    draw_badge(790, 160, "FLAT 2D PHOTO", "REJECTED (0.00)")

    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 42), "3D STRUCTURED LIGHT PROJECTION • VCSEL DEPTH SENSOR", font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 240), anchor="mm")

    img.save(out, format="PNG")
    return out


def generate_mems_accelerometer_schematic(output_path: Optional[Path] = None) -> Path:
    """Renders a 2D technical diagram of a silicon MEMS capacitive accelerometer."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / "mems_accelerometer.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = 460, 245
    pw, ph = 190, 210

    # Silicon frame cavity
    draw.rounded_rectangle([130, 80, 790, 410], radius=18, fill=(*COLOR_OBSIDIAN_BG, 220), outline=(*COLOR_LINE_DARK, 255), width=2)

    # Central Proof Mass
    draw.rounded_rectangle([cx - pw // 2, cy - ph // 2, cx + pw // 2, cy + ph // 2], radius=14, fill=(*COLOR_MIDNIGHT_BLUE, 240), outline=(*COLOR_CYAN_ACCENT, 255), width=2)
    f_lbl = resolve_system_font(13, weight="bold")
    draw.text((cx, cy - 14), "CENTRAL PROOF MASS", font=f_lbl, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")
    f_sub = resolve_system_font(11, weight="medium")
    draw.text((cx, cy + 12), "SUSPENDED SILICON (m = 12 µg)", font=f_sub, fill=(*COLOR_TEXT_PURE_WHITE, 220), anchor="mm")

    # Serpentine Folded Suspension Springs
    for sx in [cx - 60, cx + 60]:
        pts_top = [(sx, cy - ph // 2), (sx - 16, cy - ph // 2 - 18), (sx + 16, cy - ph // 2 - 36), (sx, cy - ph // 2 - 54), (sx, 80)]
        for i in range(len(pts_top) - 1):
            draw.line([pts_top[i], pts_top[i + 1]], fill=(*COLOR_CYAN_ACCENT, 240), width=2)
        pts_bot = [(sx, cy + ph // 2), (sx - 16, cy + ph // 2 + 18), (sx + 16, cy + ph // 2 + 36), (sx, cy + ph // 2 + 54), (sx, 410)]
        for i in range(len(pts_bot) - 1):
            draw.line([pts_bot[i], pts_bot[i + 1]], fill=(*COLOR_CYAN_ACCENT, 240), width=2)

    # Interdigitated Comb Fingers
    for idx, y_f in enumerate(range(cy - 65, cy + 85, 26)):
        draw.line([(cx - pw // 2, y_f), (cx - pw // 2 - 75, y_f)], fill=(*COLOR_CYAN_ACCENT, 255), width=3)
        draw.line([(170, y_f + 8), (cx - pw // 2 - 15, y_f + 8)], fill=(*COLOR_LINE_DARK, 255), width=3)
        draw.line([(cx + pw // 2, y_f), (cx + pw // 2 + 75, y_f)], fill=(*COLOR_CYAN_ACCENT, 255), width=3)
        draw.line([(cx + pw // 2 + 15, y_f + 8), (750, y_f + 8)], fill=(*COLOR_LINE_DARK, 255), width=3)

    # Differential Capacitance Callouts
    f_p = resolve_system_font(11, weight="bold")
    draw.rounded_rectangle([40, 435, 270, 475], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_CYAN_ACCENT, 200), width=1)
    draw.text((155, 455), "FREE FALL: a = 0.00 m/s² (0g)", font=f_p, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    draw.rounded_rectangle([330, 435, 590, 475], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_LINE_DARK, 220), width=1)
    draw.text((460, 455), "CAPACITANCE: ΔC = ε·A / d", font=f_p, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="mm")

    draw.rounded_rectangle([650, 435, 880, 475], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_ELECTRIC_BLUE, 200), width=1)
    draw.text((765, 455), "AT REST: a = 9.81 m/s² (1g)", font=f_p, fill=(*COLOR_ELECTRIC_BLUE, 255), anchor="mm")

    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 42), "MEMS CAPACITIVE ACCELEROMETER • MICROMECHANICAL SILICON", font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 240), anchor="mm")

    img.save(out, format="PNG")
    return out


def generate_nfc_secure_element_schematic(output_path: Optional[Path] = None) -> Path:
    """Renders a 2D technical diagram of NFC inductive coupling and hardware Secure Element tokenization."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / "nfc_secure_element.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Smartphone Body with NFC Loop Antenna
    sx, sy = 240, 240
    draw.rounded_rectangle([sx - 110, sy - 140, sx + 110, sy + 140], radius=20, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 255), width=2)
    for loop_r in [95, 85, 75]:
        draw.rounded_rectangle([sx - loop_r, sy - loop_r, sx + loop_r, sy + loop_r], radius=14, outline=(*COLOR_CYAN_ACCENT, 180), width=2)
    f_lbl = resolve_system_font(12, weight="bold")
    draw.text((sx, sy - 110), "NFC ANTENNA (COPPER)", font=f_lbl, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    # Secure Element Die
    draw.rounded_rectangle([sx - 60, sy - 20, sx + 60, sy + 70], radius=10, fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_ELECTRIC_BLUE, 255), width=2)
    draw.text((sx, sy + 12), "SECURE ELEMENT", font=f_lbl, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="mm")
    f_sub = resolve_system_font(10, weight="medium")
    draw.text((sx, sy + 36), "CRYPTOGRAPHIC DIE", font=f_sub, fill=(*COLOR_CYAN_ACCENT, 220), anchor="mm")
    draw.text((sx, sy + 54), "ISOLATED PAN: 4532****", font=f_sub, fill=(*COLOR_TEXT_MUTED_GRAY, 200), anchor="mm")

    # POS Payment Terminal
    tx, ty = 680, 240
    draw.rounded_rectangle([tx - 110, ty - 140, tx + 110, ty + 140], radius=20, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 255), width=2)
    for loop_r in [95, 85, 75]:
        draw.rounded_rectangle([tx - loop_r, ty - loop_r, tx + loop_r, ty + loop_r], radius=14, outline=(*COLOR_ELECTRIC_BLUE, 180), width=2)
    draw.text((tx, ty - 110), "POS PAYMENT TERMINAL", font=f_lbl, fill=(*COLOR_ELECTRIC_BLUE, 255), anchor="mm")
    draw.rounded_rectangle([tx - 70, ty - 20, tx + 70, ty + 70], radius=10, fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_LINE_DARK, 255), width=2)
    draw.text((tx, ty + 12), "RF RECEIVER", font=f_lbl, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="mm")
    draw.text((tx, ty + 36), "DYNAMIC TOKEN", font=f_sub, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")
    draw.text((tx, ty + 54), "SINGLE USE: 9B2F****", font=f_sub, fill=(*COLOR_TEXT_MUTED_GRAY, 200), anchor="mm")

    # Magnetic Coupling Field in Center
    cx = 460
    for r in range(40, 150, 25):
        draw.arc([cx - r, ty - r, cx + r, ty + r], start=300, end=60, fill=(*COLOR_CYAN_ACCENT, 220), width=2)
        draw.arc([cx - r, ty - r, cx + r, ty + r], start=120, end=240, fill=(*COLOR_ELECTRIC_BLUE, 220), width=2)

    # Dynamic Token Pulse
    draw.line([(sx + 60, sy + 25), (tx - 70, ty + 25)], fill=(*COLOR_CYAN_ACCENT, 255), width=3)
    draw.ellipse([cx - 6, ty + 19, cx + 6, ty + 31], fill=(*COLOR_TEXT_PURE_WHITE, 255))

    # Telemetry badges
    f_p = resolve_system_font(11, weight="bold")
    draw.rounded_rectangle([70, 425, 290, 465], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_CYAN_ACCENT, 200), width=1)
    draw.text((180, 445), "FREQUENCY: 13.56 MHz NFC", font=f_p, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    draw.rounded_rectangle([350, 425, 570, 465], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_LINE_DARK, 200), width=1)
    draw.text((460, 445), "RANGE: < 4.0 cm (INDUCTIVE)", font=f_p, fill=(*COLOR_TEXT_PURE_WHITE, 220), anchor="mm")

    draw.rounded_rectangle([630, 425, 850, 465], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_ELECTRIC_BLUE, 200), width=1)
    draw.text((740, 445), "ORIGINAL PAN: NEVER BROADCAST", font=f_p, fill=(*COLOR_ELECTRIC_BLUE, 255), anchor="mm")

    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 42), "MAGNETIC INDUCTION & SECURE ELEMENT TOKENIZATION", font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 240), anchor="mm")

    img.save(out, format="PNG")
    return out


def generate_wifi_rf_interference_schematic(output_path: Optional[Path] = None) -> Path:
    """Renders a 2D technical diagram of 2.45 GHz microwave magnetron interference vs 2.4 GHz Wi-Fi channels."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / "wifi_microwave_interference.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    mx, my = 220, 240
    draw.rounded_rectangle([mx - 120, my - 130, mx + 120, my + 130], radius=18, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 255), width=2)
    draw.ellipse([mx - 60, my - 60, mx + 60, my + 60], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_CYAN_ACCENT, 255), width=2)
    draw.ellipse([mx - 15, my - 15, mx + 15, my + 15], fill=(*COLOR_TEXT_PURE_WHITE, 255))
    for a in range(0, 360, 45):
        rad = math.radians(a)
        draw.line([(mx + int(15 * math.cos(rad)), my + int(15 * math.sin(rad))), (mx + int(55 * math.cos(rad)), my + int(55 * math.sin(rad)))], fill=(*COLOR_CYAN_ACCENT, 200), width=2)
    f_lbl = resolve_system_font(12, weight="bold")
    draw.text((mx, my + 85), "MAGNETRON (800 W)", font=f_lbl, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")
    f_sub = resolve_system_font(11, weight="medium")
    draw.text((mx, my + 105), "λ = 12.2 cm • 2,450 MHz", font=f_sub, fill=(*COLOR_TEXT_MUTED_GRAY, 220), anchor="mm")

    wx, wy = 700, 240
    draw.rounded_rectangle([wx - 100, wy - 130, wx + 100, wy + 130], radius=18, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 255), width=2)
    draw.line([(wx, wy - 120), (wx, wy - 60)], fill=(*COLOR_ELECTRIC_BLUE, 255), width=4)
    draw.ellipse([wx - 6, wy - 126, wx + 6, wy - 114], fill=(*COLOR_CYAN_ACCENT, 255))
    draw.ellipse([wx - 40, wy - 30, wx + 40, wy + 50], fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_ELECTRIC_BLUE, 255), width=2)
    draw.text((wx, wy + 85), "WI-FI ROUTER (0.1 W)", font=f_lbl, fill=(*COLOR_ELECTRIC_BLUE, 255), anchor="mm")
    draw.text((wx, wy + 105), "CHANNELS 1-11 (2,412-2,462 MHz)", font=f_sub, fill=(*COLOR_TEXT_MUTED_GRAY, 220), anchor="mm")

    cx = 460
    pts_mag = []
    for x in range(340, 600, 5):
        y = int(my - 50 * math.sin((x - 340) / 260.0 * 4 * math.pi))
        pts_mag.append((x, y))
    for i in range(len(pts_mag) - 1):
        draw.line([pts_mag[i], pts_mag[i + 1]], fill=(*COLOR_CYAN_ACCENT, 240), width=3)

    pts_wifi = []
    for x in range(340, 600, 5):
        y = int(my + 10 * math.sin((x - 340) / 260.0 * 8 * math.pi))
        pts_wifi.append((x, y))
    for i in range(len(pts_wifi) - 1):
        draw.line([pts_wifi[i], pts_wifi[i + 1]], fill=(*COLOR_LINE_DARK, 255), width=2)

    f_p = resolve_system_font(11, weight="bold")
    draw.rounded_rectangle([60, 425, 290, 465], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_CYAN_ACCENT, 200), width=1)
    draw.text((175, 445), "EXACT COLLISION: 2.4 GHz", font=f_p, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    draw.rounded_rectangle([340, 425, 580, 465], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_LINE_DARK, 200), width=1)
    draw.text((460, 445), "DISPROPORTION: 8,000x POWER", font=f_p, fill=(*COLOR_TEXT_PURE_WHITE, 220), anchor="mm")

    draw.rounded_rectangle([630, 425, 860, 465], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_ELECTRIC_BLUE, 200), width=1)
    draw.text((745, 445), "RESULT: PACKET FREEZE / LAG", font=f_p, fill=(*COLOR_ELECTRIC_BLUE, 255), anchor="mm")

    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 42), "2.4 GHz RF SPECTRUM COLLISION • ELECTROMAGNETIC RESONANCE", font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 240), anchor="mm")

    img.save(out, format="PNG")
    return out


def generate_wafer_die_schematic(
    topic_key: str,
    title: str,
    principle: str = "",
    output_path: Optional[Path] = None,
) -> Path:
    """Renders a procedural 2D silicon wafer and microchip die schematic without template bleed."""
    out = output_path or (ASSETS_SCHEMATICS_DIR / f"{topic_key}_schematic.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    w, h = 920, 520
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = 460, 245
    r_wafer = 195
    draw.ellipse([cx - r_wafer, cy - r_wafer, cx + r_wafer, cy + r_wafer], fill=(*COLOR_MIDNIGHT_BLUE, 220), outline=(*COLOR_LINE_DARK, 255), width=2)
    draw.line([(cx - 15, cy - r_wafer), (cx, cy - r_wafer + 12), (cx + 15, cy - r_wafer)], fill=(*COLOR_CYAN_ACCENT, 255), width=2)

    grid_step = 40
    for x in range(cx - 160, cx + 180, grid_step):
        for y in range(cy - 160, cy + 180, grid_step):
            if math.hypot(x - cx, y - cy) < r_wafer - 15:
                draw.rectangle([x, y, x + grid_step - 4, y + grid_step - 4], outline=(*COLOR_GRID_SLATE, 160), width=1)

    dw, dh = 180, 140
    draw.rounded_rectangle([cx - dw // 2, cy - dh // 2, cx + dw // 2, cy + dh // 2], radius=12, fill=(*COLOR_OBSIDIAN_BG, 255), outline=(*COLOR_CYAN_ACCENT, 255), width=2)
    draw.rectangle([cx - dw // 2 + 10, cy - dh // 2 + 10, cx - 10, cy + dh // 2 - 10], outline=(*COLOR_ELECTRIC_BLUE, 200), width=1)
    draw.rectangle([cx + 10, cy - dh // 2 + 10, cx + dw // 2 - 10, cy + dh // 2 - 10], outline=(*COLOR_CYAN_ACCENT, 200), width=1)

    f_die = resolve_system_font(12, weight="bold")
    draw.text((cx - 48, cy), "CORE 0", font=f_die, fill=(*COLOR_ELECTRIC_BLUE, 255), anchor="mm")
    draw.text((cx + 48, cy), "CORE 1", font=f_die, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    for angle_deg in range(0, 360, 30):
        rad = math.radians(angle_deg)
        x1 = cx + int(100 * math.cos(rad))
        y1 = cy + int(80 * math.sin(rad))
        x2 = cx + int((r_wafer - 20) * math.cos(rad))
        y2 = cy + int((r_wafer - 20) * math.sin(rad))
        draw.line([(x1, y1), (x2, y2)], fill=(*COLOR_LINE_DARK, 200), width=1)
        draw.ellipse([x2 - 3, y2 - 3, x2 + 3, y2 + 3], fill=(*COLOR_CYAN_ACCENT, 255))

    f_p = resolve_system_font(11, weight="bold")
    draw.rounded_rectangle([60, 435, 300, 475], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_CYAN_ACCENT, 200), width=1)
    clean_topic_label = topic_key.replace("_", " ").upper()[:24]
    draw.text((180, 455), f"TOPIC: {clean_topic_label}", font=f_p, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    draw.rounded_rectangle([620, 435, 860, 475], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_ELECTRIC_BLUE, 200), width=1)
    draw.text((740, 455), "FABRICATION: 2D SILICON", font=f_p, fill=(*COLOR_ELECTRIC_BLUE, 255), anchor="mm")

    f_hdr = resolve_system_font(13, weight="bold")
    draw.text((460, 42), title.upper()[:52], font=f_hdr, fill=(*COLOR_CYAN_ACCENT, 240), anchor="mm")

    img.save(out, format="PNG")
    return out


# Alias for backwards compatibility
generate_generic_tech_schematic = generate_wafer_die_schematic


def generate_contextual_schematic_for_topic(
    topic_key: str,
    title: str,
    act_number: int,
    output_path: Path,
) -> Path:
    """Intelligently dispatches the exact contextual 2D schematic diagram based on topic keywords.
    Ensures zero template bleed and absolute coherence with the narrative script.
    """
    t_lower = (topic_key or "").lower() + " " + (title or "").lower()

    if any(k in t_lower for k in ["aceler", "caida", "caída", "sensor", "grito", "acceler", "fall", "drop", "shock"]):
        return generate_mems_accelerometer_schematic(output_path)
    elif any(k in t_lower for k in ["faceid", "punto", "facial", "proyecc", "cara", "face", "dot", "infrared", "true depth", "mesh"]):
        return generate_faceid_infrared_mesh_schematic(output_path)
    elif any(k in t_lower for k in ["nfc", "pago", "tarjeta", "token", "banco", "tpv", "datafono", "pay", "card", "terminal"]):
        return generate_nfc_secure_element_schematic(output_path)
    elif any(k in t_lower for k in ["wifi", "wi-fi", "microondas", "bluetooth", "auricular", "microwave", "magnetron", "interference", "rf"]):
        return generate_wifi_rf_interference_schematic(output_path)
    elif any(k in t_lower for k in ["gps", "relativ", "satelite", "satélite", "cesio", "reloj", "satellite", "cesium", "clock", "orbit", "einstein"]):
        return generate_gps_relativity_schematic(output_path)
    elif any(k in t_lower for k in ["luz", "datacenter", "latencia", "curva_fibra", "velocidad_luz", "light", "latency", "silica"]):
        return generate_datacenter_speed_of_light_schematic(output_path)
    elif any(k in t_lower for k in ["cable", "submarino", "oceano", "océano", "marea", "subsea", "ocean", "transoceanic", "abyssal"]):
        return generate_submarine_cable_schematic(output_path)
    elif any(k in t_lower for k in ["asml", "euv", "litograf", "nanometr", "nanómetr", "tsmc", "wafer", "lithography", "nanometer"]):
        return generate_euv_lithography_schematic(output_path)
    else:
        return generate_wafer_die_schematic(topic_key, title, output_path=output_path)


# ==============================================================================
# 4. TYPOGRAPHY & BLUEPRINT CARDS FOR THE 5 NARRATIVE ACTS
# ==============================================================================
def draw_text_autoscale(
    draw: ImageDraw.ImageDraw,
    text: str,
    x: int,
    y: int,
    max_w: int,
    max_h: int,
    start_size: int = 32,
    min_size: int = 16,
    weight: str = "bold",
    fill: Tuple[int, int, int, int] = (*COLOR_TEXT_PURE_WHITE, 255),
    line_spacing: Optional[int] = None,
) -> int:
    """Universal word-wrap and autoscaling typography renderer preventing word truncation."""
    clean_text = " ".join(text.strip().split())
    words = clean_text.split()
    if not words:
        return y

    best_lines = [clean_text]
    best_font = resolve_system_font(start_size, weight=weight)
    best_line_h = start_size + (line_spacing if line_spacing is not None else int(start_size * 0.22))

    for sz in range(start_size, min_size - 1, -2):
        font = resolve_system_font(sz, weight=weight)
        cur_spacing = line_spacing if line_spacing is not None else int(sz * 0.22)
        line_h = sz + cur_spacing
        lines = []
        cur_line = []
        fits = True

        for w in words:
            candidate = " ".join(cur_line + [w]) if cur_line else w
            bbox = font.getbbox(candidate)
            w_px = bbox[2] - bbox[0]
            if w_px <= max_w:
                cur_line.append(w)
            else:
                if cur_line:
                    lines.append(" ".join(cur_line))
                    cur_line = [w]
                    w_single = font.getbbox(w)
                    if (w_single[2] - w_single[0]) > max_w:
                        fits = False
                        break
                else:
                    fits = False
                    break

        if fits and cur_line:
            lines.append(" ".join(cur_line))

        if fits:
            total_h = len(lines) * line_h
            if total_h <= max_h:
                best_lines = lines
                best_font = font
                best_line_h = line_h
                break

    cur_y = y
    for line in best_lines:
        draw.text((x, cur_y), line, font=best_font, fill=fill)
        cur_y += best_line_h

    return cur_y


def create_schematic_hook_card(
    paradox_title: str,
    subtitle: str,
    output_path: Path,
) -> Path:
    """Act 1: Renders the paradoxical premise blueprint card."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_w, card_h = 920, 440
    radius = 24
    shadow_pad = 36

    canvas_w = card_w + (shadow_pad * 2)
    canvas_h = card_h + (shadow_pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle([shadow_pad + 4, shadow_pad + 12, shadow_pad + card_w + 4, shadow_pad + card_h + 12], radius=radius, fill=(0, 4, 12, 190))
    img.alpha_composite(shadow_img.filter(ImageFilter.GaussianBlur(radius=20)), (0, 0))

    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_img)
    c_draw.rounded_rectangle([0, 0, card_w, card_h], radius=radius, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 255), width=2)
    c_draw.rounded_rectangle([2, 2, card_w - 2, 48], radius=radius, outline=(*COLOR_CYAN_ACCENT, 90), width=1)

    pad_x = 48
    content_y = 36

    f_cat = resolve_system_font(13, weight="bold")
    cat_txt = "TECHNICAL PARADOX // PHYSICS & INFRASTRUCTURE"
    bb_cat = f_cat.getbbox(cat_txt)
    cp_w = (bb_cat[2] - bb_cat[0]) + 34
    cp_h = 28
    c_draw.rounded_rectangle([pad_x, content_y, pad_x + cp_w, content_y + cp_h], radius=cp_h // 2, fill=(*COLOR_OBSIDIAN_BG, 220), outline=(*COLOR_CYAN_ACCENT, 160), width=1)
    c_draw.ellipse([pad_x + 10, content_y + cp_h // 2 - 3, pad_x + 16, content_y + cp_h // 2 + 3], fill=(*COLOR_CYAN_ACCENT, 255))
    c_draw.text((pad_x + 24, content_y + cp_h // 2), cat_txt, font=f_cat, fill=(*COLOR_TEXT_PURE_WHITE, 255), anchor="lm")

    # Paradox Headline with autoscale
    y_title = content_y + cp_h + 18
    next_y = draw_text_autoscale(
        c_draw, paradox_title.upper(), pad_x, y_title,
        max_w=card_w - (pad_x * 2), max_h=130,
        start_size=34, min_size=20, weight="heavy",
        fill=(*COLOR_TEXT_PURE_WHITE, 255),
    )

    # Subtitle with autoscale
    draw_text_autoscale(
        c_draw, subtitle, pad_x, next_y + 12,
        max_w=card_w - (pad_x * 2), max_h=130,
        start_size=21, min_size=15, weight="medium",
        fill=(*COLOR_TEXT_MUTED_GRAY, 240),
    )

    f_bot = resolve_system_font(12, weight="bold")
    c_draw.text((pad_x, card_h - 36), "SILICON VERDICT // ENGINEERING TEARDOWNS", font=f_bot, fill=(*COLOR_CYAN_ACCENT, 180), anchor="lt")

    img.alpha_composite(card_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


def create_schematic_concept_card(
    title: str,
    bullets: List[str],
    output_path: Path,
) -> Path:
    """Act 2: Renders the core concept explanation card with clean autoscale bullets."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_w, card_h = 920, 440
    radius = 24
    shadow_pad = 36

    canvas_w = card_w + (shadow_pad * 2)
    canvas_h = card_h + (shadow_pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle([shadow_pad + 4, shadow_pad + 12, shadow_pad + card_w + 4, shadow_pad + card_h + 12], radius=radius, fill=(0, 4, 12, 190))
    img.alpha_composite(shadow_img.filter(ImageFilter.GaussianBlur(radius=20)), (0, 0))

    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_img)
    c_draw.rounded_rectangle([0, 0, card_w, card_h], radius=radius, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 255), width=2)

    pad_x = 48
    f_pill = resolve_system_font(12, weight="bold")
    pill_txt = "CORE CONCEPT // PHYSICAL PRINCIPLE"
    bb_pt = f_pill.getbbox(pill_txt)
    pw = (bb_pt[2] - bb_pt[0]) + 30
    ph = 28
    c_draw.rounded_rectangle([pad_x, 34, pad_x + pw, 34 + ph], radius=ph // 2, fill=(*COLOR_OBSIDIAN_BG, 220), outline=(*COLOR_CYAN_ACCENT, 160), width=1)
    c_draw.text((pad_x + pw // 2, 34 + ph // 2), pill_txt, font=f_pill, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    # Title
    draw_text_autoscale(c_draw, title.upper(), pad_x, 78, max_w=card_w - (pad_x * 2), max_h=60, start_size=26, min_size=18, weight="heavy")

    # Bullets
    y_b = 148
    for b in bullets[:3]:
        c_draw.ellipse([pad_x, y_b + 4, pad_x + 10, y_b + 14], fill=(*COLOR_CYAN_ACCENT, 255))
        next_b_y = draw_text_autoscale(c_draw, b, pad_x + 22, y_b, max_w=card_w - pad_x - 36, max_h=55, start_size=19, min_size=15, weight="medium", fill=(*COLOR_TEXT_MUTED_GRAY, 250))
        y_b = max(y_b + 52, next_b_y + 8)

    f_bot = resolve_system_font(12, weight="bold")
    c_draw.text((pad_x, card_h - 36), "EMPIRICAL METRIC // FUNDAMENTAL TELEMETRY", font=f_bot, fill=(*COLOR_CYAN_ACCENT, 180), anchor="lt")

    img.alpha_composite(card_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


def create_schematic_analogy_card(
    analogy_title: str,
    left_concept: str,
    right_analogy: str,
    output_path: Path,
) -> Path:
    """Act 3: Renders the tangible everyday analogy card with dual comparison containers."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_w, card_h = 920, 440
    radius = 24
    shadow_pad = 36

    canvas_w = card_w + (shadow_pad * 2)
    canvas_h = card_h + (shadow_pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle([shadow_pad + 4, shadow_pad + 12, shadow_pad + card_w + 4, shadow_pad + card_h + 12], radius=radius, fill=(0, 4, 12, 190))
    img.alpha_composite(shadow_img.filter(ImageFilter.GaussianBlur(radius=20)), (0, 0))

    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_img)
    c_draw.rounded_rectangle([0, 0, card_w, card_h], radius=radius, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_LINE_DARK, 255), width=2)

    pad_x = 48
    f_pill = resolve_system_font(12, weight="bold")
    pill_txt = "TANGIBLE ANALOGY // EVERYDAY MECHANISM"
    bb_pt = f_pill.getbbox(pill_txt)
    pw = (bb_pt[2] - bb_pt[0]) + 30
    ph = 28
    c_draw.rounded_rectangle([pad_x, 34, pad_x + pw, 34 + ph], radius=ph // 2, fill=(*COLOR_OBSIDIAN_BG, 220), outline=(*COLOR_CYAN_ACCENT, 160), width=1)
    c_draw.text((pad_x + pw // 2, 34 + ph // 2), pill_txt, font=f_pill, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    # Title
    draw_text_autoscale(c_draw, analogy_title.upper(), pad_x, 78, max_w=card_w - (pad_x * 2), max_h=55, start_size=26, min_size=18, weight="heavy")

    # Dual Comparison Boxes
    box_w = (card_w - (pad_x * 2) - 24) // 2
    box_h = 205
    y_box = 138

    # Box 1: Abstract Magnitude
    c_draw.rounded_rectangle([pad_x, y_box, pad_x + box_w, y_box + box_h], radius=16, fill=(*COLOR_OBSIDIAN_BG, 220), outline=(*COLOR_LINE_DARK, 200), width=1)
    f_bh = resolve_system_font(13, weight="bold")
    c_draw.text((pad_x + 18, y_box + 18), "ABSTRACT MAGNITUDE", font=f_bh, fill=(*COLOR_CYAN_ACCENT, 220))
    draw_text_autoscale(c_draw, left_concept, pad_x + 18, y_box + 50, max_w=box_w - 36, max_h=135, start_size=18, min_size=13, weight="medium", fill=(*COLOR_TEXT_PURE_WHITE, 255))

    # Box 2: Everyday Comparison
    bx2 = pad_x + box_w + 24
    c_draw.rounded_rectangle([bx2, y_box, bx2 + box_w, y_box + box_h], radius=16, fill=(*COLOR_OBSIDIAN_BG, 220), outline=(*COLOR_CYAN_ACCENT, 180), width=1)
    c_draw.text((bx2 + 18, y_box + 18), "REAL-WORLD EQUIVALENCE", font=f_bh, fill=(*COLOR_CYAN_ACCENT, 255))
    draw_text_autoscale(c_draw, right_analogy, bx2 + 18, y_box + 50, max_w=box_w - 36, max_h=135, start_size=18, min_size=13, weight="medium", fill=(*COLOR_TEXT_PURE_WHITE, 255))

    f_bot = resolve_system_font(12, weight="bold")
    c_draw.text((pad_x, card_h - 36), "HUMAN SCALE // COMPARATIVE TELEMETRY", font=f_bot, fill=(*COLOR_CYAN_ACCENT, 180), anchor="lt")

    img.alpha_composite(card_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


def create_schematic_resolution_card(
    resolution_title: str,
    takeaway: str,
    output_path: Path,
) -> Path:
    """Act 4: Renders the engineering resolution and industry solution card."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_w, card_h = 920, 440
    radius = 24
    shadow_pad = 36

    canvas_w = card_w + (shadow_pad * 2)
    canvas_h = card_h + (shadow_pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle([shadow_pad + 4, shadow_pad + 12, shadow_pad + card_w + 4, shadow_pad + card_h + 12], radius=radius, fill=(0, 4, 12, 190))
    img.alpha_composite(shadow_img.filter(ImageFilter.GaussianBlur(radius=20)), (0, 0))

    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_img)
    c_draw.rounded_rectangle([0, 0, card_w, card_h], radius=radius, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_ELECTRIC_BLUE, 220), width=2)

    pad_x = 48
    f_pill = resolve_system_font(12, weight="bold")
    pill_txt = "ENGINEERING RESOLUTION // REAL-WORLD SOLUTION"
    bb_pt = f_pill.getbbox(pill_txt)
    pw = (bb_pt[2] - bb_pt[0]) + 30
    ph = 28
    c_draw.rounded_rectangle([pad_x, 34, pad_x + pw, 34 + ph], radius=ph // 2, fill=(*COLOR_OBSIDIAN_BG, 220), outline=(*COLOR_ELECTRIC_BLUE, 200), width=1)
    c_draw.text((pad_x + pw // 2, 34 + ph // 2), pill_txt, font=f_pill, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    # Title
    draw_text_autoscale(c_draw, resolution_title.upper(), pad_x, 78, max_w=card_w - (pad_x * 2), max_h=60, start_size=26, min_size=18, weight="heavy")

    # Takeaway text with dynamic autoscale
    draw_text_autoscale(c_draw, takeaway, pad_x, 148, max_w=card_w - (pad_x * 2), max_h=200, start_size=21, min_size=15, weight="medium", fill=(*COLOR_TEXT_MUTED_GRAY, 250))

    f_bot = resolve_system_font(12, weight="bold")
    c_draw.text((pad_x, card_h - 36), "SYSTEM ARCHITECTURE // SILICON VERDICT", font=f_bot, fill=(*COLOR_CYAN_ACCENT, 180), anchor="lt")

    img.alpha_composite(card_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


def create_schematic_punchline_card(
    question: str,
    option_a: str = "",
    option_b: str = "",
    output_path: Path = None,
) -> Path:
    """Act 5: Renders the closing community debate punchline card without fake voting polls."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    card_w, card_h = 920, 440
    radius = 24
    shadow_pad = 36

    canvas_w = card_w + (shadow_pad * 2)
    canvas_h = card_h + (shadow_pad * 2)
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))

    shadow_img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    s_draw = ImageDraw.Draw(shadow_img)
    s_draw.rounded_rectangle([shadow_pad + 4, shadow_pad + 12, shadow_pad + card_w + 4, shadow_pad + card_h + 12], radius=radius, fill=(0, 4, 12, 190))
    img.alpha_composite(shadow_img.filter(ImageFilter.GaussianBlur(radius=20)), (0, 0))

    card_img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    c_draw = ImageDraw.Draw(card_img)
    c_draw.rounded_rectangle([0, 0, card_w, card_h], radius=radius, fill=(*COLOR_MIDNIGHT_BLUE, 230), outline=(*COLOR_CYAN_ACCENT, 200), width=2)

    pad_x = 48
    f_pill = resolve_system_font(12, weight="bold")
    pill_txt = "COMMUNITY DEBATE // SILICON VERDICT"
    bb_pt = f_pill.getbbox(pill_txt)
    pw = (bb_pt[2] - bb_pt[0]) + 30
    ph = 28
    c_draw.rounded_rectangle([pad_x, 34, pad_x + pw, 34 + ph], radius=ph // 2, fill=(*COLOR_OBSIDIAN_BG, 220), outline=(*COLOR_CYAN_ACCENT, 160), width=1)
    c_draw.text((pad_x + pw // 2, 34 + ph // 2), pill_txt, font=f_pill, fill=(*COLOR_CYAN_ACCENT, 255), anchor="mm")

    # Community Question
    next_y = draw_text_autoscale(
        c_draw, question.upper(), pad_x, 82,
        max_w=card_w - (pad_x * 2), max_h=120,
        start_size=26, min_size=18, weight="heavy",
        fill=(*COLOR_TEXT_PURE_WHITE, 255),
    )

    # Native Community Debate Call-to-Action container (replacing fake poll buttons)
    y_callout = max(next_y + 16, 210)
    box_w = card_w - (pad_x * 2)
    box_h = 135
    c_draw.rounded_rectangle([pad_x, y_callout, pad_x + box_w, y_callout + box_h], radius=16, fill=(*COLOR_OBSIDIAN_BG, 230), outline=(*COLOR_CYAN_ACCENT, 180), width=1)

    f_dh = resolve_system_font(15, weight="heavy")
    c_draw.text((pad_x + 24, y_callout + 20), "💬 LEAVE YOUR VERDICT IN THE COMMENTS", font=f_dh, fill=(*COLOR_CYAN_ACCENT, 255))

    prompt_desc = "What is your technical take on this dilemma? The best engineering insights will be pinned and featured."
    draw_text_autoscale(c_draw, prompt_desc, pad_x + 24, y_callout + 54, max_w=box_w - 48, max_h=65, start_size=16, min_size=13, weight="medium", fill=(*COLOR_TEXT_MUTED_GRAY, 240))

    f_bot = resolve_system_font(12, weight="bold")
    c_draw.text((pad_x, card_h - 34), "SHARE YOUR TAKE • SUBSCRIBE TO SILICON VERDICT", font=f_bot, fill=(*COLOR_CYAN_ACCENT, 180), anchor="lt")

    img.alpha_composite(card_img, (shadow_pad, shadow_pad))
    img.save(output_path, format="PNG")
    return output_path


# ==============================================================================
# 5. DYNAMIC SCHEMATIC COMPOSITION RENDERER (ZERO STATIC FRAMES @ 60 FPS)
# ==============================================================================
def render_schematic_act_clip(
    canvas_bg_path: Path,
    schematic_png_path: Optional[Path],
    card_png_path: Path,
    duration_sec: float,
    output_path: Path,
    fps: int = 60,
) -> Path:
    """Composites the dark grid background, upper 2D schematic, and bottom card via FFmpeg.

    Continuous Dynamics (Zero Static Frames @ 60 FPS):
    - Ken Burns Camera: Continuous subtle zoom from 1.0x to 1.04x throughout clip duration.
    - Laser Scanner Sweep: Continuous vertical oscillating cyan laser beam traversing the schematic.
    - Ease-Out Cubic Slide-in: Blueprint card enters smoothly from bottom to resting position in 0.45s.
    - Layout: Upper 65% schematic + card, lower 35% reserved for subtitles with mobile safe zone insets.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = shutil.which("ffmpeg") or str(Path(sys.executable).parent / "ffmpeg") or "ffmpeg"

    d_str = f"{duration_sec:.2f}"

    if schematic_png_path and schematic_png_path.is_file():
        inputs = [
            "-loop", "1", "-t", d_str, "-i", str(canvas_bg_path),
            "-loop", "1", "-t", d_str, "-i", str(schematic_png_path),
            "-loop", "1", "-t", d_str, "-i", str(card_png_path),
        ]

        filter_complex = (
            f"[0:v]scale=eval=frame:w='1080*(1.0+0.04*t/{d_str})':h='1920*(1.0+0.04*t/{d_str})',crop=1080:1920:(iw-1080)/2:(ih-1920)/2[bg_cam];"
            f"[1:v]scale=920:-1,format=rgba,fade=t=in:st=0:d=0.30:alpha=1[sch];"
            f"color=c=0x38bdf8@0.35:s=920x22:d={d_str}[laser_glow];"
            f"color=c=0xffffff@0.85:s=920x2:d={d_str}[laser_core];"
            f"[laser_glow][laser_core]overlay=0:10[laser_bar];"
            f"[bg_cam][sch]overlay=(W-w)/2:180:shortest=1[bg_sch];"
            f"[bg_sch][laser_bar]overlay=(W-w)/2:'180 + 240 + 200*sin(2*PI*t/3.0)':shortest=1[bg_scanned];"
            f"[2:v]format=rgba[crd];"
            f"[bg_scanned][crd]overlay=x=(W-w)/2:y='if(lt(t,0.45), 1800-(1800-720)*(1-pow(1-t/0.45,3)), 720)':shortest=1[out]"
        )
    else:
        # Act 5 without top schematic: centered debate card with Ken Burns camera
        inputs = [
            "-loop", "1", "-t", d_str, "-i", str(canvas_bg_path),
            "-loop", "1", "-t", d_str, "-i", str(card_png_path),
        ]
        filter_complex = (
            f"[0:v]scale=eval=frame:w='1080*(1.0+0.04*t/{d_str})':h='1920*(1.0+0.04*t/{d_str})',crop=1080:1920:(iw-1080)/2:(ih-1920)/2[bg_cam];"
            f"[1:v]format=rgba[crd];"
            f"[bg_cam][crd]overlay=x=(W-w)/2:y='if(lt(t,0.45), 1800-(1800-580)*(1-pow(1-t/0.45,3)), 580)':shortest=1[out]"
        )

    cmd = [
        ffmpeg_bin, "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-t", d_str,
        "-r", str(fps),
        "-c:v", "libx264",
        "-preset", "faster",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        str(output_path),
    ]

    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    return output_path


# ==============================================================================
# 6. HIGH-CTR COVER FRAME GENERATOR (FRAME 00:00.00 & STANDALONE JPEG)
# ==============================================================================
def generate_cover_frame(
    title: str,
    category_badge: str,
    background_clip: Optional[Path],
    output_path: Path,
    highlight_words: Optional[List[str]] = None,
    width: int = 1080,
    height: int = 1920,
) -> Path:
    """Generates a high-CTR mobile-first cover frame (1080x1920) for TikTok and YouTube Shorts."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg_bin = shutil.which("ffmpeg") or str(Path(sys.executable).parent / "ffmpeg") or "ffmpeg"

    # 1. Base Canvas Preparation
    canvas = None
    if background_clip and Path(background_clip).is_file():
        # Extract a clean representative frame from the B-roll
        tmp_frame = output_path.parent / f".tmp_cover_raw_{output_path.stem}.png"
        cmd_extract = [
            ffmpeg_bin, "-y",
            "-ss", "00:00:01.5",
            "-i", str(background_clip),
            "-vframes", "1",
            str(tmp_frame),
        ]
        try:
            subprocess.run(cmd_extract, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if tmp_frame.is_file():
                raw_bg = Image.open(tmp_frame).convert("RGBA")
                # Crop and scale to fill 1080x1920
                src_w, src_h = raw_bg.size
                scale = max(width / src_w, height / src_h)
                new_w = int(src_w * scale)
                new_h = int(src_h * scale)
                scaled_bg = raw_bg.resize((new_w, new_h), Image.Resampling.LANCZOS)
                # Center crop
                left = (new_w - width) // 2
                top = (new_h - height) // 2
                canvas = scaled_bg.crop((left, top, left + width, top + height))
                # Slight blur for depth of field
                canvas = canvas.filter(ImageFilter.GaussianBlur(radius=3))
                tmp_frame.unlink(missing_ok=True)
        except Exception:
            pass

    if canvas is None:
        # Fallback to procedural dark obsidian grid
        tmp_grid = output_path.parent / f".tmp_grid_{output_path.stem}.png"
        generate_schematic_canvas(tmp_grid, width=width, height=height)
        canvas = Image.open(tmp_grid).convert("RGBA")
        tmp_grid.unlink(missing_ok=True)

    # 2. Darkening Tint Overlay (60% dark obsidian / midnight blue tint for massive contrast)
    dark_tint = Image.new("RGBA", (width, height), (7, 9, 14, 160))
    canvas = Image.alpha_composite(canvas, dark_tint)

    draw = ImageDraw.Draw(canvas)

    # 3. Top Category Badge (Centered at Y: 300)
    badge_text = category_badge.upper().strip()
    if not badge_text.startswith("["):
        badge_text = f"[ {badge_text} ]"
    badge_font = resolve_system_font(38, weight="bold")
    bbox = draw.textbbox((0, 0), badge_text, font=badge_font)
    bw = bbox[2] - bbox[0]
    bh = bbox[3] - bbox[1]
    bx = (width - bw) // 2
    by = 310

    # Draw rounded pill box behind category badge
    pad_x, pad_y = 28, 14
    draw.rounded_rectangle(
        [bx - pad_x, by - pad_y, bx + bw + pad_x, by + bh + pad_y],
        radius=14,
        fill=(30, 41, 59, 230),
        outline=(56, 189, 248, 180),
        width=2,
    )
    draw.text((bx, by), badge_text, font=badge_font, fill=COLOR_CYAN_ACCENT)

    # 4. Massive Hook Title (Center Y: 740 - 1050)
    # Target 86-92px font size for high CTR mobile readability
    title_font = resolve_system_font(88, weight="black")
    clean_title = re.sub(r"[\#\@\[\]]", "", title).strip()

    # Wrap title into 2-3 massive lines (max 18 chars per line)
    words = clean_title.split()
    lines: List[List[str]] = []
    cur_line: List[str] = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + 1 > 18 and cur_line:
            lines.append(cur_line)
            cur_line = [w]
            cur_len = len(w)
        else:
            cur_line.append(w)
            cur_len += len(w) + 1
    if cur_line:
        lines.append(cur_line)

    # Keep at most 3 lines
    if len(lines) > 3:
        lines = lines[:3]
        lines[-1][-1] = lines[-1][-1].rstrip(".") + "..."

    # Highlight keyword detection
    default_highlights = {
        "4060", "4070", "4080", "4090", "8GB", "16GB", "12GB", "1440P", "1080P", "4K",
        "EINSTEIN", "RELATIVITY", "FPS", "DEAD", "VRAM", "AM5", "INTEL", "RYZEN", "DLSS",
        "BOTTLENECK", "SATELLITE", "ZERO", "MICROSECONDS", "EUV", "ASML", "NANOMETERS"
    }
    if highlight_words:
        for hw in highlight_words:
            default_highlights.add(hw.upper().strip())

    line_height = 115
    total_text_h = len(lines) * line_height
    start_y = 760 - (total_text_h // 2)

    for i, line_words in enumerate(lines):
        line_y = start_y + (i * line_height)
        # Measure entire line width
        line_str = " ".join(line_words)
        line_bbox = draw.textbbox((0, 0), line_str, font=title_font)
        line_w = line_bbox[2] - line_bbox[0]
        cur_x = (width - line_w) // 2

        # Draw word by word with drop shadow
        for j, w in enumerate(line_words):
            w_str = w + (" " if j < len(line_words) - 1 else "")
            clean_w_upper = re.sub(r"[^\w]", "", w).upper()
            is_highlight = clean_w_upper in default_highlights or any(h in clean_w_upper for h in default_highlights)
            text_color = COLOR_CYAN_ACCENT if is_highlight else COLOR_TEXT_PURE_WHITE

            # Drop shadow (3px, 4px)
            draw.text((cur_x + 3, line_y + 4), w_str, font=title_font, fill=(0, 0, 0, 220))
            # Main text
            draw.text((cur_x, line_y), w_str, font=title_font, fill=text_color)

            wb = draw.textbbox((0, 0), w_str, font=title_font)
            cur_x += (wb[2] - wb[0])

    # 5. Bottom Brand Watermark
    watermark_font = resolve_system_font(34, weight="bold")
    wm_text = "@SiliconVerdict"
    wm_bbox = draw.textbbox((0, 0), wm_text, font=watermark_font)
    wm_w = wm_bbox[2] - wm_bbox[0]
    wm_x = (width - wm_w) // 2
    wm_y = 1710

    # Draw small subtle watermark pill
    draw.rounded_rectangle(
        [wm_x - 20, wm_y - 8, wm_x + wm_w + 20, wm_y + 36],
        radius=10,
        fill=(15, 23, 42, 190),
        outline=(51, 65, 85, 140),
        width=1,
    )
    draw.text((wm_x, wm_y), wm_text, font=watermark_font, fill=(148, 163, 184))

    # Convert to RGB and save as high-quality JPEG
    final_rgb = canvas.convert("RGB")
    final_rgb.save(output_path, "JPEG", quality=95)
    logger.info("Generated high-CTR Cover Frame: %s (Badge: %s | Title lines: %d)", output_path.name, category_badge, len(lines))
    return output_path
