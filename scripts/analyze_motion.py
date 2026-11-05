#!/usr/bin/env python3
"""Measure motion quality of a rendered video without watching it.

  python3 scripts/analyze_motion.py output/video.mp4 --cuts 60,170,232 [--keep]

For every shot (between cuts) it reports:
  - pops:   frames whose change from the previous frame is > 2.5x the local median (excluding the 14 frames around each cut,
            where the zoom transition is expected). Pops mean jitter, teleporting or flicker.
  - dof:    sharpness of the subject (centre) vs the background (top band). Ratio > 1.3 = the background really is blurred.
  - pump:   largest frame-to-frame change of the subject sharpness (log). Large values mean the focus is pumping.
Uses only Pillow + the ffmpeg that ships with Remotion.
"""
import argparse, math, os, shutil, statistics, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageChops, ImageFilter, ImageStat

ROOT = Path(__file__).resolve().parent.parent
FF = ROOT / "remotion_studio" / "node_modules" / "@remotion" / "compositor-darwin-arm64"

def sharp(img):
    return ImageStat.Stat(img.filter(ImageFilter.FIND_EDGES)).var[0]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("video"); ap.add_argument("--cuts", default=""); ap.add_argument("--keep", action="store_true"); a = ap.parse_args()
    cuts = [int(c) for c in a.cuts.split(",") if c]
    tmp = Path(tempfile.mkdtemp())
    env = dict(os.environ, DYLD_LIBRARY_PATH=str(FF), LD_LIBRARY_PATH=str(FF))
    subprocess.run([str(FF / "ffmpeg"), "-v", "error", "-y", "-i", a.video, "-an", "-vf", "scale=270:480", str(tmp / "f_%04d.png")], check=True, env=env)
    files = sorted(tmp.glob("f_*.png")); n = len(files)
    gray = [Image.open(f).convert("L") for f in files]
    diff = [0.0] + [ImageStat.Stat(ImageChops.difference(gray[i], gray[i - 1])).mean[0] for i in range(1, n)]
    subj = [sharp(g.crop((70, 150, 200, 330))) for g in gray]      # centre: where the camera looks
    bg = [sharp(g.crop((0, 0, 270, 90))) for g in gray]             # top band: sky and far background
    bounds = [0] + cuts + [n]
    print(f"{a.video}: {n} frames, {len(cuts)} cuts")
    print(f"{'shot':>10} {'frames':>7} {'median change':>14} {'pops':>5} {'worst pop (x median)':>22} {'dof subj/bg':>12} {'pump (max dlog)':>16}")
    for k in range(len(bounds) - 1):
        s, e = bounds[k], bounds[k + 1]
        lo, hi = s + (0 if k == 0 else 14), e - (0 if k == len(bounds) - 2 else 14)
        if hi - lo < 6: continue
        pops, worst = [], 0.0
        for f in range(lo + 1, hi):
            win = [diff[j] for j in range(max(lo + 1, f - 8), min(hi, f + 9))]
            med = statistics.median(win) or 1e-6
            r = diff[f] / med
            worst = max(worst, r)
            if r > 2.5 and diff[f] > 0.8: pops.append(f)
        ratio = statistics.mean(subj[lo:hi]) / max(1e-6, statistics.mean(bg[lo:hi]))
        pump = max(abs(math.log(max(1e-6, subj[f]) / max(1e-6, subj[f - 1]))) for f in range(lo + 1, hi))
        med_all = statistics.median(diff[lo + 1:hi])
        print(f"{s:>4}-{e:<5} {hi - lo:>7} {med_all:>14.2f} {len(pops):>5} {worst:>22.1f} {ratio:>12.2f} {pump:>16.2f}" + (f"   pops at {pops[:6]}" if pops else ""))
    # transitions: the change around each cut should be a clean blur-zoom, not a long flash
    for c in cuts:
        win = diff[max(1, c - 14): min(n, c + 14)]
        calm = statistics.median(diff[1:n])
        print(f"cut {c}: peak change {max(win):.1f}; frames above 3x the video's median change ({calm:.2f}): {sum(1 for d in win if d > 3 * calm)} of {len(win)}")
    if not a.keep: shutil.rmtree(tmp)
main()
