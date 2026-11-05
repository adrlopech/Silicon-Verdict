"""Renders a Minecraft script (McStory) to a 1080x1920 @ 30 fps mp4 with Remotion (composition 'McStory').

The video carries its own audio (real game sounds placed by the director), so no narration is mixed in.
"""
import json
import logging
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

FPS = 30

from config.settings import settings
from core.schemas import McStory
from services.voice import get_ffmpeg_bin

logger = logging.getLogger(__name__)


def render_mc_video(story: McStory, output_video_path: Path, output_cover_path: Optional[Path] = None, voice_clips: Optional[list] = None) -> Tuple[Path, Path, Dict[str, float]]:
    t0 = time.time()
    output_video_path = Path(output_video_path).resolve()
    output_video_path.parent.mkdir(parents=True, exist_ok=True)
    cover = Path(output_cover_path).resolve() if output_cover_path else output_video_path.with_name(f"{output_video_path.stem}_cover.jpg")
    remotion_dir = settings.BASE_DIR / "remotion_studio"
    if not (remotion_dir / "public" / "mc" / "skin.png").is_file():
        raise FileNotFoundError("Minecraft assets missing: run `python3 scripts/extract_minecraft_assets.py` first (see docs/minecraft_assets.md)")

    props = output_video_path.with_suffix(".props.json")
    props.write_text(json.dumps({"script": story.to_script()}, ensure_ascii=False), encoding="utf-8")
    raw = output_video_path.with_name(f"raw_{output_video_path.name}")
    env = os.environ.copy()
    env["PATH"] = f"{Path.home() / '.local' / 'bin'}:{env.get('PATH', '')}"
    cmd = ["npx", "remotion", "render", "src/index.ts", "McStory", str(raw), f"--props={props}", "--public-dir=public", "--concurrency=4", "--log=error"]
    logger.info("Rendering Minecraft video via Remotion (McStory)...")
    t_r = time.time()
    proc = subprocess.run(cmd, cwd=str(remotion_dir), env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    t_render = time.time() - t_r
    props.unlink(missing_ok=True)
    if proc.returncode != 0 or not raw.is_file():
        raise RuntimeError(f"Remotion render failed: {proc.stdout[-600:]}")

    ff = get_ffmpeg_bin()
    if voice_clips:  # narration over ducked game sounds, each line at its beat's start frame
        from services.mc_director import compile_script
        beats = compile_script(story.to_script())["beats"]
        music = settings.BASE_DIR / "assets" / "audio" / "mc_bed.wav"  # original loop from scripts/make_mc_music.py; the old ambient bed is the fallback
        bed = music if music.is_file() else settings.BASE_DIR / "assets" / "audio" / "schematic_ambient.wav"
        ins = ["-stream_loop", "-1", "-i", str(bed)]
        parts, voices = ["[0:a]volume=0.4[g]", "[1:a]volume=0.5,afade=t=in:d=1.5[bed0]"], []
        for n, (bi, clip, _d) in enumerate(voice_clips, start=2):
            ins += ["-i", str(clip)]
            ms = int(beats[bi]["from"] / FPS * 1000) + 120
            parts.append(f"[{n}:a]adelay={ms}|{ms},volume=1.6[v{n}]")
            voices.append(f"[v{n}]")
        # the music ducks under the narration (side-chain compression), then everything is mixed and normalised
        parts.append("".join(voices) + f"amix=inputs={len(voices)}:duration=longest:normalize=0,asplit=2[vox1][vox2]")
        parts.append("[bed0][vox1]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=450[bed]")
        parts.append("[g][bed][vox2]amix=inputs=3:duration=first:normalize=0,loudnorm=I=-14:TP=-2:LRA=11[a]")
        mux = [ff, "-y", "-i", str(raw), *ins, "-filter_complex", ";".join(parts), "-map", "0:v", "-map", "[a]", "-ar", "48000", "-t", f"{beats[-1]['to'] / FPS:.2f}",
               "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output_video_path)]
    else:
        mux = [ff, "-y", "-i", str(raw), "-c:v", "libx264", "-preset", "medium", "-crf", "24", "-pix_fmt", "yuv420p",
               "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(output_video_path)]
    subprocess.run(mux, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    raw.unlink(missing_ok=True)
    try:  # the cover shows the title card and the hook sign
        subprocess.run([ff, "-y", "-ss", "1.2", "-i", str(output_video_path), "-vframes", "1", "-q:v", "2", str(cover)], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as exc:
        logger.warning("Could not extract cover: %s", exc)
    return output_video_path, cover, {"headless_render": t_render, "total_render": time.time() - t0}
