"""Generate the Silicon Verdict channel brand assets (avatar + YouTube banner).

Palette (README): obsidian #05070C, blue #007AFF, electric cyan #00F0FF.
Output: assets/brand/*.png
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "brand"
FONT_B = str(ROOT / "assets" / "fonts" / "Inter-Bold.ttf")
FONT_R = str(ROOT / "assets" / "fonts" / "Inter-Regular.ttf")

OBSIDIAN = (5, 7, 12)
BLUE = (0, 122, 255)
CYAN = (0, 240, 255)
WHITE = (255, 255, 255)
MUTED = (148, 163, 184)


def glow_background(w, h, grid=64):
    img = Image.new("RGB", (w, h), OBSIDIAN)
    layer = Image.new("RGB", (w, h), OBSIDIAN)
    d = ImageDraw.Draw(layer)
    d.ellipse((-w * 0.25, -h * 0.9, w * 0.45, h * 0.8), fill=BLUE)
    d.ellipse((w * 0.6, h * 0.3, w * 1.2, h * 1.5), fill=(0, 110, 120))
    layer = layer.filter(ImageFilter.GaussianBlur(min(w, h) * 0.22))
    img = Image.blend(img, layer, 0.55)
    g = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(g)
    for x in range(0, w, grid):
        gd.line((x, 0, x, h), fill=(255, 255, 255, 14), width=1)
    for y in range(0, h, grid):
        gd.line((0, y, w, y), fill=(255, 255, 255, 14), width=1)
    img.paste(g, (0, 0), g)
    return img


def draw_icon(size, rounded=True):
    """Rounded square, cyan outline, inner square ring with a centre dot."""
    s = size * 4
    icon = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(icon)
    pad = s * 0.03
    r = s * 0.24
    if rounded:
        d.rounded_rectangle((pad, pad, s - pad, s - pad), r, fill=(10, 16, 28, 255), outline=CYAN, width=int(s * 0.035))
    else:
        d.rectangle((0, 0, s, s), fill=(10, 16, 28, 255))
    c = s / 2
    q = s * 0.19
    d.rectangle((c - q, c - q, c + q, c + q), outline=CYAN, width=int(s * 0.06))
    dot = s * 0.075
    d.ellipse((c - dot, c - dot, c + dot, c + dot), fill=CYAN)
    glow = icon.filter(ImageFilter.GaussianBlur(s * 0.03))
    out = Image.alpha_composite(glow, icon)
    return out.resize((size, size), Image.LANCZOS)



S_PATH = [(470, 270), (240, 270), (170, 340), (170, 410), (240, 480), (380, 520), (450, 590), (450, 660), (380, 730), (130, 730)]
V_PATH = [(580, 270), (720, 730), (930, 150)]
STROKE = 124
SHEAR = 0.14


def _stroke_polys(path, w):
    """Flat-ended thick polyline with bevelled joins, as a list of polygons."""
    import math
    h = w / 2
    polys = []
    norms = []
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        nx, ny = -(y1 - y0) / L * h, (x1 - x0) / L * h
        norms.append((nx, ny))
        polys.append([(x0 + nx, y0 + ny), (x1 + nx, y1 + ny), (x1 - nx, y1 - ny), (x0 - nx, y0 - ny)])
    for i in range(1, len(path)):
        if i < len(path) - 1:
            x, y = path[i]
            (ax, ay), (bx, by) = norms[i - 1], norms[i]
            polys.append([(x + ax, y + ay), (x + bx, y + by), (x - ax, y - ay), (x - bx, y - by)])
    return polys


def sv_mark(size, tile=False):
    """SV lettering: heavy italic S + V with bevelled corners, scan-line cuts and a verdict-tick V."""
    k = 4
    n = size * k
    sc = n / 1000 * 0.9
    ox, oy = n * 0.03, n * 0.04

    def pt(p):
        x, y = p
        x = x + (500 - y) * SHEAR
        return (x * sc + ox, y * sc + oy)

    mask = Image.new("L", (n, n), 0)
    d = ImageDraw.Draw(mask)
    for path in (S_PATH, V_PATH):
        for poly in _stroke_polys(path, STROKE):
            d.polygon([pt(q) for q in poly], fill=255)
    # scan-line cuts (parallel diagonal slits) for a glitch / chip feel
    cut = ImageDraw.Draw(mask)
    for cy in (455, 505):
        cut.line((0, cy * sc + oy + n * 0.10, n, (cy - 140) * sc + oy + n * 0.10), fill=0, width=max(2, int(11 * sc)))
    # gradient: cyan top-left -> blue bottom-right
    grad = Image.new("RGB", (n, n))
    gd = ImageDraw.Draw(grad)
    for i in range(n * 2):
        t = i / (n * 2)
        c = tuple(int(CYAN[j] * (1 - t) + BLUE[j] * t) for j in range(3))
        gd.line((i, 0, 0, i), fill=c, width=2)
    mark = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    mark.paste(grad, (0, 0), mask)
    # bright verdict tip: V's last segment fades to white-cyan
    tipmask = Image.new("L", (n, n), 0)
    td = ImageDraw.Draw(tipmask)
    tip_poly = _stroke_polys([V_PATH[1], V_PATH[2]], STROKE)[0]
    td.polygon([pt(q) for q in tip_poly], fill=255)
    tipmask = Image.composite(tipmask, Image.new("L", (n, n), 0), mask)
    fade = Image.new("L", (n, n), 0)
    fd = ImageDraw.Draw(fade)
    y0, y1 = pt(V_PATH[1])[1], pt(V_PATH[2])[1]
    for y in range(int(min(y0, y1)), int(max(y0, y1))):
        fd.line((0, y, n, y), fill=int(255 * (y0 - y) / (y0 - y1)))
    tipmask = Image.composite(tipmask, Image.new("L", (n, n), 0), fade)
    mark.paste(Image.new("RGB", (n, n), (200, 255, 255)), (0, 0), tipmask.point(lambda a: int(a * 0.85)))
    glow = mark.filter(ImageFilter.GaussianBlur(n * 0.03))
    out = Image.alpha_composite(glow, mark)
    return out.resize((size, size), Image.LANCZOS)


def avatar(size=800):
    """Square full-bleed avatar; platforms crop it to a circle, so keep the icon central."""
    img = glow_background(size, size, grid=size // 12).convert("RGBA")
    img.alpha_composite(sparkles(size, size, 28, seed=3))
    ic = sv_mark(int(size * 0.74))
    # centre on the letters' real bounding box (italic + tall V tip make the canvas centre misleading)
    bb = ic.getchannel("A").point(lambda a: 255 if a > 140 else 0).getbbox()
    cx, cy = (bb[0] + bb[2]) / 2, (bb[1] + bb[3]) / 2
    img.alpha_composite(ic, (int(size / 2 - cx), int(size / 2 - cy)))
    return img.convert("RGB")


def wordmark(draw, xy, px, anchor="la"):
    f = ImageFont.truetype(FONT_B, px)
    x, y = xy
    draw.text((x, y), "Silicon", font=f, fill=WHITE, anchor=anchor, stroke_width=3, stroke_fill=WHITE)
    x += draw.textlength("Silicon", font=f)
    draw.text((x, y), "Verdict", font=f, fill=CYAN, anchor=anchor, stroke_width=3, stroke_fill=CYAN)


FONT_SERIF = "/System/Library/Fonts/Supplemental/Georgia Italic.ttf"
FONT_MONO = "/System/Library/Fonts/SFNSMono.ttf"


def _glow(img, radius, strength=1.0):
    g = img.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        g.putalpha(g.getchannel("A").point(lambda a: min(255, int(a * strength))))
    return Image.alpha_composite(g, img)


def sparkles(w, h, count, seed=7, region=None, avoid=None):
    import random
    rnd = random.Random(seed)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for _ in range(count):
        x, y = rnd.randint(0, w), rnd.randint(0, h)
        if region and not (region[0] < x < region[2] and region[1] < y < region[3]):
            continue
        if avoid and avoid[0] < x < avoid[2] and avoid[1] < y < avoid[3]:
            continue
        r = rnd.choice([5, 7, 9, 14, 20, 28])
        a = rnd.randint(70, 200)
        col = rnd.choice([WHITE, CYAN, (150, 210, 255)])
        if r <= 9:
            d.ellipse((x - r / 3, y - r / 3, x + r / 3, y + r / 3), fill=col + (a,))
        else:
            k = 0.16
            d.polygon([(x, y - r), (x + r * k, y - r * k), (x + r, y), (x + r * k, y + r * k),
                       (x, y + r), (x - r * k, y + r * k), (x - r, y), (x - r * k, y - r * k)], fill=col + (a,))
    return _glow(layer, 5, 1.6)


def tile(size, kind):
    """Liquid-glass tile with a computing icon (cpu, gpu, ram, ssd, terminal, chart, wifi)."""
    k = 4
    n = size * k
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((n * .03, n * .03, n * .97, n * .97), n * .22, fill=(255, 255, 255, 16),
                        outline=CYAN + (120,), width=int(n * .012))
    d.rounded_rectangle((n * .05, n * .05, n * .95, n * .30), n * .2, fill=(255, 255, 255, 14))
    lw = int(n * .028)
    c = CYAN + (255,)
    cf = CYAN + (60,)

    def R(x0, y0, x1, y1, r=.04, fill=None):
        d.rounded_rectangle((n * x0, n * y0, n * x1, n * y1), n * r, outline=c, width=lw, fill=fill)

    def L(*pts):
        d.line([(n * x, n * y) for x, y in pts], fill=c, width=lw, joint="curve")

    if kind == "cpu":
        R(.30, .30, .70, .70, fill=cf)
        d.rounded_rectangle((n * .41, n * .41, n * .59, n * .59), n * .02, fill=c)
        for i in range(4):
            t = .365 + i * .09
            L((t, .30), (t, .20)); L((t, .70), (t, .80)); L((.30, t), (.20, t)); L((.70, t), (.80, t))
    elif kind == "gpu":
        R(.14, .34, .86, .66, .05, fill=cf)
        for cx in (.38, .62):
            d.ellipse((n * (cx - .10), n * .40, n * (cx + .10), n * .60), outline=c, width=lw)
            d.ellipse((n * (cx - .025), n * .475, n * (cx + .025), n * .525), fill=c)
        L((.14, .31), (.14, .69))
        d.rectangle((n * .26, n * .66, n * .62, n * .71), fill=c)
    elif kind == "ram":
        R(.12, .36, .88, .62, .03, fill=cf)
        for i in range(4):
            d.rounded_rectangle((n * (.19 + i * .17), n * .42, n * (.29 + i * .17), n * .56), n * .015, fill=c)
        for i in range(12):
            x = .16 + i * .06
            d.rectangle((n * x, n * .62, n * (x + .035), n * .69), fill=c)
    elif kind == "ssd":
        R(.24, .22, .76, .78, .06, fill=cf)
        R(.32, .30, .68, .46, .02)
        d.rounded_rectangle((n * .32, n * .56, n * .46, n * .68), n * .015, fill=c)
        d.ellipse((n * .60, n * .59, n * .68, n * .67), fill=c)
    elif kind == "terminal":
        R(.14, .24, .86, .76, .05, fill=cf)
        L((.14, .37), (.86, .37))
        L((.28, .47), (.39, .55), (.28, .63))
        L((.46, .65), (.62, .65))
    elif kind == "chart":
        L((.20, .76), (.80, .76))
        for x0, top in ((.26, .55), (.43, .40), (.60, .28)):
            d.rounded_rectangle((n * x0, n * top, n * (x0 + .12), n * .73), n * .015, fill=c)
        L((.22, .42), (.40, .32), (.55, .36), (.78, .20))
    elif kind == "wifi":
        for r in (.12, .22, .32):
            d.arc((n * (.5 - r), n * (.68 - r), n * (.5 + r), n * (.68 + r)), 225, 315, fill=c, width=lw)
        d.ellipse((n * .465, n * .645, n * .535, n * .715), fill=c)
    out = _glow(im, n * .02, 1.2)
    return out.resize((size, size), Image.LANCZOS)


def place(img, tile_img, cx, cy, angle=0, alpha=1.0):
    t = tile_img.rotate(angle, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        t.putalpha(t.getchannel("A").point(lambda a: int(a * alpha)))
    img.alpha_composite(t, (int(cx - t.width / 2), int(cy - t.height / 2)))


def cursor_arrow(img, tip, scale=1.8, ripples=True):
    """The video engine's pointer (cursor.tsx) with click ripples."""
    # smooth pointer: rounded corners, longer and slimmer tail
    pts = [(0, 0), (0, 32), (8.2, 25.2), (15.2, 43), (20.8, 40.8), (14.2, 23.6), (25, 23.4)]
    k = 4
    pad = 40
    W = int(34 * scale * k) + pad * 2
    H = int(48 * scale * k) + pad * 2
    poly = [(x * scale * k + pad, y * scale * k + pad) for x, y in pts]
    rr = 2.1 * scale * k  # corner rounding radius
    body = Image.new("L", (W, H), 0)
    bd = ImageDraw.Draw(body)
    bd.polygon(poly, fill=255)
    bd.line(poly + [poly[0]], fill=255, width=int(rr * 2), joint="curve")
    for x, y in poly:
        bd.ellipse((x - rr, y - rr, x + rr, y + rr), fill=255)
    # shrink back so the silhouette keeps its size but with round corners
    body = body.filter(ImageFilter.GaussianBlur(rr * .9)).point(lambda a: 255 if a > 176 else 0)
    body = body.filter(ImageFilter.GaussianBlur(1.6))
    stroke = 1.5 * scale * k
    outline = body.filter(ImageFilter.GaussianBlur(stroke * .55)).point(lambda a: min(255, int(a * 4)))
    cur = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    cur.paste(Image.new("RGBA", (W, H), OBSIDIAN + (255,)), (0, 0), outline)
    cur.paste(Image.new("RGBA", (W, H), WHITE + (255,)), (0, 0), body)
    cur = cur.resize((W // k, H // k), Image.LANCZOS)
    ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    tx, ty = tip
    if ripples:
        for r, a, wd in ((34, 230, 6), (66, 150, 5), (104, 80, 4), (150, 36, 3)):
            od.ellipse((tx - r, ty - r, tx + r, ty + r), outline=CYAN + (a,), width=wd)
        od.ellipse((tx - 16, ty - 16, tx + 16, ty + 16), fill=CYAN + (120,))
    ov = _glow(ov, 8, 1.3)
    img.alpha_composite(ov)
    sh = Image.new("RGBA", cur.size, (0, 0, 0, 0))
    sh.putalpha(cur.getchannel("A").point(lambda a: int(a * 0.55)))
    sh = sh.filter(ImageFilter.GaussianBlur(7))
    img.alpha_composite(sh, (int(tx - 10 + 8), int(ty - 10 + 12)))
    img.alpha_composite(cur, (int(tx - 10), int(ty - 10)))


def banner(w=2560, h=1440, with_cursor=False, compact=False):
    img = glow_background(w, h, grid=96).convert("RGBA")
    sw = 1546  # YouTube safe area (1546 x 423), visible on every device
    sx = (w - sw) // 2
    cy = h // 2
    # soft cyan bloom + light streak behind the lockup
    bl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bl)
    bd.ellipse((sx + 140, cy - 190, sx + sw + 100, cy + 190), fill=CYAN + (46,))
    bd.rectangle((0, cy - 3, w, cy + 3), fill=CYAN + (30,))
    img.alpha_composite(bl.filter(ImageFilter.GaussianBlur(110)))
    img.alpha_composite(sparkles(w, h, 90, seed=11, avoid=(sx + 380, cy - 230, sx + sw + 40, cy + 150)))
    # watermark monogram
    wm = sv_mark(1000)
    wm.putalpha(wm.getchannel("A").point(lambda a: int(a * 0.06)))
    img.alpha_composite(wm, (w - 1180, (h - 1000) // 2 + 40))
    # computing icons: bold ones in the always-visible band, faint ones for TV/tall screens
    if compact:  # mobile shows only the 1546x423 centre: put the hero icons inside it
        place(img, tile(124, "cpu"), sx + 98, cy - 20, -6)
        place(img, tile(124, "gpu"), sx + sw - 98, cy + 20, 6)
    else:
        place(img, tile(220, "cpu"), 200, cy - 95, -6)
        place(img, tile(230, "gpu"), w - 215, cy - 85, 6)
    place(img, tile(170, "terminal"), 395, cy + 120, 5)
    place(img, tile(170, "ram"), w - 420, cy + 125, -5)
    place(img, tile(150, "ssd"), 640, cy - 440, -8, .55)
    place(img, tile(150, "chart"), 1960, cy - 470, 7, .55)
    place(img, tile(150, "wifi"), 700, cy + 470, 6, .5)
    place(img, tile(150, "cpu"), 2060, cy + 460, -7, .5)
    # lockup
    d = ImageDraw.Draw(img)
    if compact:
        M, fs1, fs2, tag, tagtxt, cur_scale = 330, 112, 128, 38, "HARD DATA / REAL BENCHMARKS", 1.45
    else:
        M, fs1, fs2, tag, tagtxt, cur_scale = 440, 140, 160, 27, "HARD DATA / NO MARKETING FLUFF / REAL BENCHMARKS", 1.8
    f1 = ImageFont.truetype(FONT_B, fs1)
    f2 = ImageFont.truetype(FONT_SERIF, fs2)
    gap = 12 * fs1 / 140
    text_w = d.textlength("Silicon", font=f1) + gap + d.textlength("Verdict", font=f2)
    if compact:
        mark_vis = 0.86 * M
        total = mark_vis + 36 + text_w + 40
        left = sx + (sw - total) / 2
        mark_x = left - 0.11 * M
        tx = left + mark_vis + 36
    else:
        mark_x = sx - 20
        tx = sx + 440
    base = cy - 5 * fs1 / 140 + (14 if compact else 0)
    ic = sv_mark(M)
    img.alpha_composite(ic, (int(mark_x), int(cy - M / 2 - 28 * M / 440)))
    if with_cursor:
        sel_r = tx + text_w
        k_ = fs1 / 140
        selb = (tx - 14, base - 146 * k_, sel_r + 14, base + 36 * k_)
        sl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sl)
        sd.rectangle(selb, fill=BLUE + (120,))
        sd.rectangle(selb, outline=(70, 160, 255, 230), width=3)
        for hx, hy in ((selb[0], selb[1]), (selb[2], selb[3])):
            sd.rectangle((hx - 5, hy - 5, hx + 5, hy + 5), fill=WHITE + (255,), outline=BLUE + (255,), width=2)
        img.alpha_composite(_glow(sl, 10, 0.9))
        d = ImageDraw.Draw(img)
    d.text((tx, base), "Silicon", font=f1, fill=WHITE, anchor="ls", stroke_width=3, stroke_fill=WHITE)
    vx = tx + d.textlength("Silicon", font=f1) + gap
    wl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(wl).text((vx, base), "Verdict", font=f2, fill=CYAN + (255,), anchor="ls", stroke_width=1, stroke_fill=CYAN)
    img.alpha_composite(_glow(wl, 14, 1.2))
    vend = vx + d.textlength("Verdict", font=f2)
    fm = ImageFont.truetype(FONT_MONO, tag)
    if not with_cursor:
        d.rectangle((tx, base + 38, tx + 150, base + 42), fill=BLUE)
    d.text((tx, base + (62 if compact else 78) + (10 if compact else 0)), tagtxt, font=fm, fill=MUTED, anchor="ls")
    # HUD micro labels
    fs = ImageFont.truetype(FONT_MONO, 24)
    d.text((110, cy - 330), "SV // 01  HARDWARE · GAMING · CURIOSITIES", font=fs, fill=MUTED + (0,)[:0] or MUTED)
    d.text((w - 110, cy + 330), "FPS 144 ▲ 12%   0x5356", font=fs, fill=CYAN, anchor="ra")
    if with_cursor:
        cursor_arrow(img, (int(vend + 10), int(base + 20 * fs1 / 140)), scale=cur_scale, ripples=False)
    return img.convert("RGB")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    av = avatar()
    av.save(OUT / "avatar_800.png")
    av.resize((200, 200), Image.LANCZOS).save(OUT / "avatar_tiktok_200.png")
    sv_mark(512).save(OUT / "logo_icon_512.png")
    banner(with_cursor=True).save(OUT / "youtube_banner_cursor_2560x1440.png")
    banner(with_cursor=False).save(OUT / "youtube_banner_clean_2560x1440.png")
    banner(with_cursor=True, compact=True).save(OUT / "youtube_banner_cursor_mobile_2560x1440.png")
    banner(with_cursor=False, compact=True).save(OUT / "youtube_banner_clean_mobile_2560x1440.png")
    print("ok", sorted(p.name for p in OUT.iterdir()))
