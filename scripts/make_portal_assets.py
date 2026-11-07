"""Generate the GitHub Pages (docs/) brand assets: logo.svg, favicon.svg, PNG icons and og-image.png.

Reuses the geometry and helpers of make_brand_assets.py so the portal and the channels share one logo.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_brand_assets as mb  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DOCS = mb.ROOT / "docs"


def svg_polys():
    """Polygons of the SV lettering in the final (sheared, offset) coordinate system of sv_mark()."""
    out = []
    for path in (mb.S_PATH, mb.V_PATH):
        for poly in mb._stroke_polys(path, mb.STROKE):
            out.append([(x + (500 - y) * mb.SHEAR + 33.3, y + 44.4) for x, y in poly])
    return out


def logo_svg(glow=True, tile=False):
    polys = svg_polys()
    xs = [p[0] for poly in polys for p in poly]
    ys = [p[1] for poly in polys for p in poly]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    pad = 40 if not tile else 150
    w, h = x1 - x0 + 2 * pad, y1 - y0 + 2 * pad
    side = max(w, h)
    vx, vy = x0 - pad - (side - w) / 2, y0 - pad - (side - h) / 2
    pts = lambda poly: " ".join(f"{x:.1f},{y:.1f}" for x, y in poly)
    tip_poly = polys[len(mb._stroke_polys(mb.S_PATH, mb.STROKE))]  # first V quad is seg1; need seg2
    v0 = len(mb._stroke_polys(mb.S_PATH, mb.STROKE))
    tip_poly = polys[v0 + 1]  # second V quad = the long arm that becomes the verdict tick
    cut = "".join(
        f'<line x1="0" y1="{cy + 155.6}" x2="1111" y2="{cy + 15.6}" stroke="#000" stroke-width="11"/>' for cy in (455, 505)
    )
    shapes = "".join(f'<polygon points="{pts(p)}" fill="url(#svg)" stroke="url(#svg)" stroke-width="1.2" stroke-linejoin="round"/>' for p in polys)
    tip_ys = [p[1] for p in tip_poly]
    glow_f = '<filter id="glow" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="14" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' if glow else ""
    filt = ' filter="url(#glow)"' if glow else ""
    bg = f'<rect x="{vx}" y="{vy}" width="{side}" height="{side}" rx="{side * 0.22}" fill="#05070C"/>' if tile else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vx:.1f} {vy:.1f} {side:.1f} {side:.1f}" role="img" aria-label="Silicon Verdict SV logo">'
        f'<defs><linearGradient id="svg" gradientUnits="userSpaceOnUse" x1="{x0:.0f}" y1="{y0:.0f}" x2="{x1:.0f}" y2="{y1:.0f}"><stop offset="0" stop-color="#00F0FF"/><stop offset="1" stop-color="#007AFF"/></linearGradient>'
        f'<linearGradient id="tip" gradientUnits="userSpaceOnUse" x1="0" y1="{max(tip_ys):.0f}" x2="0" y2="{min(tip_ys):.0f}"><stop offset="0" stop-color="#C8FFFF" stop-opacity="0"/><stop offset="1" stop-color="#C8FFFF" stop-opacity=".85"/></linearGradient>'
        f'<mask id="cut" maskUnits="userSpaceOnUse" x="{vx - 50:.0f}" y="{vy - 50:.0f}" width="{side + 100:.0f}" height="{side + 100:.0f}"><rect x="{vx - 50:.0f}" y="{vy - 50:.0f}" width="{side + 100:.0f}" height="{side + 100:.0f}" fill="#fff"/>{cut}</mask>'
        f'{glow_f}</defs>{bg}'
        f'<g mask="url(#cut)"{filt}>{shapes}<polygon points="{pts(tip_poly)}" fill="url(#tip)"/></g></svg>'
    )


def tile_png(size, rounded=True):
    """Obsidian rounded tile with the mark, for favicons / touch icons."""
    k = 4
    n = size * k
    bg = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    ImageDraw.Draw(bg).rounded_rectangle((0, 0, n - 1, n - 1), n * 0.22, fill=mb.OBSIDIAN + (255,))
    bg = bg.resize((size, size), Image.LANCZOS)
    glow = mb.glow_background(size, size, grid=max(8, size // 6)).convert("RGBA")
    m = Image.new("L", (size, size), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size - 1, size - 1), size * (0.22 if rounded else 0), fill=255)
    base = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    base.paste(glow, (0, 0), m)
    ic = mb.sv_mark(int(size * 0.82))
    bb = ic.getchannel("A").point(lambda a: 255 if a > 140 else 0).getbbox()
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    base.alpha_composite(ic, (int(size / 2 - cx), int(size / 2 - cy)))
    return base


def og_image(w=1200, h=630):
    img = mb.glow_background(w, h, grid=56).convert("RGBA")
    img.alpha_composite(mb.sparkles(w, h, 38, seed=21, avoid=(60, 40, 820, 600)))
    d = ImageDraw.Draw(img)
    # brand row
    ic = mb.sv_mark(150)
    img.alpha_composite(ic, (52, 58))
    f1 = ImageFont.truetype(mb.FONT_B, 54)
    f2 = ImageFont.truetype(mb.FONT_SERIF, 62)
    x, y = 205, 138
    d.text((x, y), "Silicon", font=f1, fill=mb.WHITE, anchor="ls", stroke_width=1, stroke_fill=mb.WHITE)
    x += d.textlength("Silicon", font=f1) + 6
    d.text((x, y), "Verdict", font=f2, fill=mb.CYAN, anchor="ls")
    # headline
    h1 = ImageFont.truetype(mb.FONT_B, 96)
    h2 = ImageFont.truetype(mb.FONT_SERIF, 110)
    d.text((80, 330), "From a topic to a", font=h1, fill=mb.WHITE, anchor="ls", stroke_width=2, stroke_fill=mb.WHITE)
    wl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(wl).text((80, 450), "published Short.", font=h2, fill=mb.CYAN + (255,), anchor="ls")
    img.alpha_composite(mb._glow(wl, 12, 1.1))
    fm = ImageFont.truetype(mb.FONT_MONO, 28)
    d.text((82, 520), "AUTOMATED VERTICAL-VIDEO STUDIO", font=fm, fill=mb.MUTED, anchor="ls")
    d.text((82, 560), "PC HARDWARE / GAMING TECH / COMPUTING CURIOSITIES", font=fm, fill=mb.MUTED, anchor="ls")
    # icon tiles on the right
    mb.place(img, mb.tile(190, "cpu"), 980, 190, -6)
    mb.place(img, mb.tile(160, "gpu"), 1060, 420, 6)
    mb.place(img, mb.tile(110, "ram"), 1105, 570, -5, 0.9)
    return img.convert("RGB")


if __name__ == "__main__":
    (DOCS / "logo.svg").write_text(logo_svg(glow=True), encoding="utf-8")
    (DOCS / "favicon.svg").write_text(logo_svg(glow=False, tile=True), encoding="utf-8")
    tile_png(32).save(DOCS / "favicon-32.png")
    tile_png(192).save(DOCS / "icon-192.png")
    tile_png(180, rounded=False).convert("RGB").save(DOCS / "apple-touch-icon.png")
    og_image().save(DOCS / "og-image.png")
    print("ok")
