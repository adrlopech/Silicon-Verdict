#!/usr/bin/env python3
"""Silicon Verdict Semantic B-Roll Auto-Indexer.

Scans assets/broll/ and maintains assets/broll/manifest.json:
1. Detects component, brand, tags, and conflicts via filename heuristics.
2. For generic filenames without keywords, extracts a frame at 00:00:02 and
   queries Gemini Vision multimodal API.
3. Automatically avoids visual and semantic incoherencies in video assembly.

Usage:
  python scripts/index_broll.py            # Index new clips
  python scripts/index_broll.py --force    # Re-index all clips
  python scripts/index_broll.py --dry-run  # Preview tagging
"""
import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure venv bin (where ffmpeg/ffprobe live) is in PATH
venv_bin = BASE_DIR / ".venv" / "bin"
if venv_bin.is_dir() and str(venv_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

from config.settings import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("broll_indexer")

BROLL_DIR = BASE_DIR / "assets" / "broll"
MANIFEST_PATH = BROLL_DIR / "manifest.json"

HEURISTIC_RULES = [
    {
        "pattern": r"(4060|4070|4080|4090|3060|3070|3080|rtx|gtx|geforce|nvidia)",
        "component": "gpu",
        "brand": "nvidia",
        "category": "gaming_benchmarks",
        "tags": ["gpu", "nvidia", "rtx", "vram", "pcie", "dlss", "raster", "benchmarks"],
        "conflicts_with": ["cpu", "intel", "amd", "ryzen", "socket", "am4", "am5"],
    },
    {
        "pattern": r"(rx|radeon|7800|7900|6700|6600|rdna)",
        "component": "gpu",
        "brand": "amd",
        "category": "gaming_benchmarks",
        "tags": ["gpu", "amd", "radeon", "rdna", "vram", "fsr", "benchmarks"],
        "conflicts_with": ["nvidia", "geforce", "dlss", "intel", "lga1700"],
    },
    {
        "pattern": r"(lga1700|intel|core_ultra|i9|i7|i5|alder|raptor|arrow_lake|hybrid)",
        "component": "cpu",
        "brand": "intel",
        "category": "hardware_benchmarks",
        "tags": ["cpu", "intel", "p-cores", "e-cores", "hybrid", "socket", "lga1700", "silicon"],
        "conflicts_with": ["amd", "ryzen", "am4", "am5", "gpu", "vram", "radeon"],
    },
    {
        "pattern": r"(am5|am4|ryzen|zen4|zen5|zen3|x3d|threadripper)",
        "component": "cpu",
        "brand": "amd",
        "category": "hardware_benchmarks",
        "tags": ["cpu", "amd", "ryzen", "am5", "zen4", "zen5", "x3d", "socket", "silicon"],
        "conflicts_with": ["intel", "lga1700", "core_ultra", "nvidia", "gpu"],
    },
    {
        "pattern": r"(cyberpunk|helldivers|wukong|flight|cs2|gameplay|gaming|benchmark)",
        "component": "gameplay",
        "brand": "none",
        "category": "gaming_benchmarks",
        "tags": ["gameplay", "gaming", "fps", "1080p", "1440p", "textures", "fluidez"],
        "conflicts_with": ["datacenter", "submarino", "euv", "satelite"],
    },
    {
        "pattern": r"(abstract|neutral|grid|dark|minimal|canvas)",
        "component": "neutral",
        "brand": "none",
        "category": "abstract",
        "tags": ["abstract", "neutral", "dark", "grid", "minimal", "engineering"],
        "conflicts_with": [],
    },
    {
        "pattern": r"(motherboard|pcb|vrm|chipset|socket)",
        "component": "motherboard",
        "brand": "none",
        "category": "hardware_benchmarks",
        "tags": ["motherboard", "pcb", "vrm", "hardware", "components"],
        "conflicts_with": [],
    },
]


def load_manifest() -> Dict[str, Any]:
    """Loads manifest.json or creates initial structure."""
    if MANIFEST_PATH.is_file():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Failed to parse manifest.json: %s. Creating new.", exc)
    return {"version": "1.0", "clips": []}


def save_manifest(manifest: Dict[str, Any]) -> None:
    """Writes manifest.json atomically."""
    BROLL_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("Saved manifest with %d clips to %s", len(manifest.get("clips", [])), MANIFEST_PATH)


def extract_frame_at_2s(clip_path: Path, output_jpg: Path) -> bool:
    """Extracts a single representative frame at 00:00:02."""
    local_ffmpeg = venv_bin / "ffmpeg"
    ffmpeg_bin = str(local_ffmpeg) if local_ffmpeg.is_file() else "ffmpeg"
    cmd = [
        ffmpeg_bin, "-y",
        "-ss", "00:00:02",
        "-i", str(clip_path),
        "-vframes", "1",
        "-q:v", "2",
        str(output_jpg),
    ]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return output_jpg.is_file()
    except Exception as exc:
        logger.warning("Frame extraction at 2s failed for %s: %s", clip_path.name, exc)
        return False


def query_gemini_vision(frame_path: Path) -> Optional[Dict[str, Any]]:
    """Analyzes a generic B-roll frame with Gemini Vision."""
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        logger.warning("GEMINI_API_KEY not configured. Skipping multimodal analysis.")
        return None

    prompt = (
        "Analiza esta imagen para un canal de hardware de PC. Identifica el componente, "
        "marca o videojuego que aparece. Devuelve únicamente un JSON con los campos: "
        "component (cpu/gpu/ram/datacenter/gameplay), brand (intel/amd/nvidia/none), "
        "tags (lista de 5 strings) y conflicts_with (lista de marcas o componentes opuestos incompatibles)."
    )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)
        with open(frame_path, "rb") as f:
            img_bytes = f.read()

        response = client.models.generate_content(
            model=settings.GEMINI_MODEL or "gemini-2.5-flash",
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                prompt,
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.2,
            ),
        )
        if response and response.text:
            cleaned = response.text.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(cleaned)
    except Exception as exc:
        logger.warning("Gemini Vision classification failed (%s). Falling back to neutral.", exc)
    return None


def classify_clip(clip_path: Path) -> Dict[str, Any]:
    """Applies heuristic rule matching or Gemini multimodal analysis."""
    filename = clip_path.name.lower()

    # 1. Filename heuristic matching
    for rule in HEURISTIC_RULES:
        if re.search(rule["pattern"], filename):
            return {
                "file": clip_path.name,
                "category": rule["category"],
                "component": rule["component"],
                "brand": rule["brand"],
                "tags": rule["tags"],
                "conflicts_with": rule["conflicts_with"],
                "last_used_timestamp": None,
                "use_count": 0,
            }

    # 2. Multimodal fallback for generic names (e.g. broll_04.mp4, clip_01.mp4)
    logger.info("Filename '%s' is generic. Invoking Gemini Vision analysis...", clip_path.name)
    tmp_frame = BROLL_DIR / f".tmp_{clip_path.stem}.jpg"
    entry = None
    if extract_frame_at_2s(clip_path, tmp_frame):
        vision_data = query_gemini_vision(tmp_frame)
        if vision_data:
            entry = {
                "file": clip_path.name,
                "category": "gaming_benchmarks" if vision_data.get("component") == "gameplay" else "hardware_benchmarks",
                "component": vision_data.get("component", "hardware"),
                "brand": vision_data.get("brand", "none"),
                "tags": vision_data.get("tags", ["hardware", "pc"]),
                "conflicts_with": vision_data.get("conflicts_with", []),
                "last_used_timestamp": None,
                "use_count": 0,
            }
        if tmp_frame.is_file():
            tmp_frame.unlink()

    if not entry:
        entry = {
            "file": clip_path.name,
            "category": "hardware_benchmarks",
            "component": "hardware",
            "brand": "none",
            "tags": ["hardware", "pc", "components", "benchmarks"],
            "conflicts_with": [],
            "last_used_timestamp": None,
            "use_count": 0,
        }

    return entry


def index_broll(force: bool = False, dry_run: bool = False) -> Dict[str, Any]:
    """Indexes all video clips in assets/broll/."""
    manifest = load_manifest()
    existing_by_file = {c["file"]: c for c in manifest.get("clips", [])}

    video_exts = {".mp4", ".mov", ".mkv", ".webm"}
    video_files = [f for f in BROLL_DIR.iterdir() if f.is_file() and f.suffix.lower() in video_exts and not f.name.startswith(".")]

    logger.info("Found %d video files in %s", len(video_files), BROLL_DIR)

    updated_clips = []
    added_count = 0
    updated_count = 0

    for v_file in video_files:
        if not force and v_file.name in existing_by_file:
            updated_clips.append(existing_by_file[v_file.name])
            continue

        clip_data = classify_clip(v_file)
        if v_file.name in existing_by_file:
            # Preserve usage counters if re-indexing
            clip_data["use_count"] = existing_by_file[v_file.name].get("use_count", 0)
            clip_data["last_used_timestamp"] = existing_by_file[v_file.name].get("last_used_timestamp")
            updated_count += 1
        else:
            added_count += 1

        updated_clips.append(clip_data)
        logger.info("Indexed clip '%s': component=%s, brand=%s, tags=%s", v_file.name, clip_data["component"], clip_data["brand"], clip_data["tags"])

    manifest["clips"] = updated_clips
    if not dry_run:
        save_manifest(manifest)
    else:
        logger.info("[DRY RUN] Skipped saving manifest to disk.")

    return {
        "total_clips": len(updated_clips),
        "added": added_count,
        "updated": updated_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Silicon Verdict Semantic B-Roll Indexer")
    parser.add_argument("--force", action="store_true", help="Re-index all clips and regenerate tags")
    parser.add_argument("--dry-run", action="store_true", help="Simulate indexing without saving manifest")
    args = parser.parse_args()

    res = index_broll(force=args.force, dry_run=args.dry_run)
    print("\n" + "=" * 60)
    print(" 🎬 SILICON VERDICT: REPORTE DE AUTO-INDEXACIÓN DE B-ROLL")
    print("=" * 60)
    print(f" Total de Clips en Manifiesto: {res['total_clips']}")
    print(f" Nuevos Clips Indexados:       {res['added']}")
    print(f" Clips Actualizados:           {res['updated']}")
    print(f" Ruta del Manifiesto:          {MANIFEST_PATH}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
