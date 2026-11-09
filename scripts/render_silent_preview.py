#!/usr/bin/env python3
"""Renders a Motion Graphics script WITHOUT any narration: a quick visual test of a script (no ElevenLabs, no upload, no history, no bank).

Each scene lasts what its narration would need at a natural pace (~2.5 words per second, like the length estimate of the validators), scenes are held at sentence ends to pass
the 62 s monetisation floor, and the soundtrack is only the project's own ambient bed and scene whooshes.

Usage:
  python scripts/render_silent_preview.py docs/generated_scripts/bank/fix/fix_001.json [more.json ...] [--out output/previews]
Output: <out>/<script name>_silent.mp4 (1080x1920, H.264, 30 fps)
"""
import argparse
import json
import math
import sys
import tempfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from services.motion_generator import WORDS_PER_SECOND, MotionProject, assign_cursors, sanitize_cursors  # noqa: E402
from services.series import apply_series  # noqa: E402
from services.motion_pipeline import FPS, MIN_VIDEO_SECONDS, VOICE_LEAD, add_sound, music_bed, qa_motion, render_motion, scene_audio_info  # noqa: E402


def time_scenes(project: MotionProject) -> None:
    """Gives every scene the length its narration would take, then holds sentence ends until the video passes the monetisation floor."""
    for sc in project.scenes:
        speech = len(sc.narration.split()) / WORDS_PER_SECOND
        sc.durationInFrames = max(sc.durationInFrames, math.ceil((speech + VOICE_LEAD + 0.12) * FPS))
    deficit = int(MIN_VIDEO_SECONDS * FPS) - project.total_frames
    if deficit > 0:
        ends = [i for i, sc in enumerate(project.scenes) if sc.narration.strip()[-1:] in ".!?"] or [len(project.scenes) - 1]
        per = math.ceil(deficit / len(ends))
        for i in ends:
            project.scenes[i].durationInFrames += per


def render_one(path: Path, out_dir: Path) -> Path:
    data = json.loads(path.read_text(encoding="utf-8"))
    name = data.pop("name", path.stem)
    data.pop("estimated_seconds", None)
    project = MotionProject.model_validate(data)
    sanitize_cursors(project.scenes, project.format)
    assign_cursors(project.scenes, project.format)
    apply_series(project, number=1)  # the title and the first-frame kicker as they will look in production (number 1 in the preview)
    time_scenes(project)
    out_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="silent_preview_") as tmp:
        raw = render_motion(project.to_props(), Path(tmp) / "raw.mp4")
        starts, acc = [], 0
        for sc in project.scenes:
            starts.append(acc)
            acc += sc.durationInFrames
        final = add_sound(raw, out_dir / f"{name}_silent.mp4", starts, None, kinds=[sc.type for sc in project.scenes], music_file=music_bed(project.format, project.topic), info=scene_audio_info(project.scenes))
    problems = qa_motion(final)
    print(f"{final}  ({project.total_frames / FPS:.1f} s){'  QA: ' + '; '.join(problems) if problems else '  QA ok'}")
    return final


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scripts", nargs="+", help="MotionProject JSON files (e.g. from docs/generated_scripts/bank/<type>/)")
    ap.add_argument("--out", default=str(BASE_DIR / "output" / "previews"), help="output folder")
    args = ap.parse_args()
    for s in args.scripts:
        render_one(Path(s), Path(args.out))


if __name__ == "__main__":
    main()
