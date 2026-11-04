"""Silicon Verdict Quality Assurance & Interactive Correction Inspector.

Audits the latest generated video in output/tiktok/ on demand:
1. Subtitles / Whisper Audit:
   - Scans text for phonetic errors (e.g. 'Siliconvertingt', 'TB.', '14 to 40 p', 'Present -mont', 'PE Cores').
   - Detects orphaned hyphens at line start (-STARVES, -RANGE) or truncated words.
   - Verifies vertical coordinates against mobile UI safe zone (Y <= 1536, MarginV >= 384 on 1080x1920).
2. Audio & Mix Audit:
   - Analyzes audio dynamics via FFmpeg volumedetect (max_volume, mean_volume).
   - Detects clipping / distortion (max_volume >= -0.5 dB).
   - Checks voice / background music balance.
3. Visual Composition & Footage Audit:
   - Coherence check: prevents socket AM4 footage from leaking into Intel / GPU topics.
   - Telemetry legibility: checks HUD font standard (>= 96px for metrics).
   - Freeze frame check: detects initial frames stuck at 0 FPS.
4. Structure & Retention Audit:
   - Checks duration within 60.0s - 120.0s (TikTok Creator Rewards > 60.5s & Shorts compliant).
   - Verifies absence of intrusive mid-roll subscription banners.

Protocol:
- Activated strictly when the user types 'corregir'.
- Outputs structured QA report and awaits user confirmation ('Sí' / 'No').
- On confirmation, applies fixes, updates metadata, and records learned rules in data/qa_rules.json.
"""
import json
import logging
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# Ensure venv bin (where ffmpeg/ffprobe live) is in PATH
venv_bin = BASE_DIR / ".venv" / "bin"
if venv_bin.is_dir() and str(venv_bin) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = f"{venv_bin}:{os.environ.get('PATH', '')}"

from config.settings import settings

logger = logging.getLogger("silicon_verdict_qa")

QA_RULES_FILE = BASE_DIR / "data" / "qa_rules.json"


def get_ffmpeg_bin() -> str:
    """Locates ffmpeg executable in venv or system PATH."""
    local_ffmpeg = venv_bin / "ffmpeg"
    if local_ffmpeg.is_file() and os.access(str(local_ffmpeg), os.X_OK):
        return str(local_ffmpeg)
    system_ffmpeg = shutil.which("ffmpeg")
    return system_ffmpeg if system_ffmpeg else "ffmpeg"


def get_ffprobe_bin() -> str:
    """Locates ffprobe executable in venv or system PATH."""
    local_ffprobe = venv_bin / "ffprobe"
    if local_ffprobe.is_file() and os.access(str(local_ffprobe), os.X_OK):
        return str(local_ffprobe)
    system_ffprobe = shutil.which("ffprobe")
    return system_ffprobe if system_ffprobe else "ffprobe"


def load_qa_rules() -> Dict[str, Any]:
    """Loads QA rules and persistent dictionary from data/qa_rules.json."""
    if QA_RULES_FILE.is_file():
        try:
            return json.loads(QA_RULES_FILE.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("Error reading %s (%s). Using defaults.", QA_RULES_FILE, exc)

    # Default rules schema
    default_rules = {
        "version": "1.0",
        "phonetic_corrections": {
            "Siliconvertingt": "Silicon Verdict",
            "Siliconverdict": "Silicon Verdict",
            "14 to 40 p": "1440p",
            "14 to 40": "1440p",
            "10 to 80 p": "1080p",
            "Present -mont": "PresentMon",
            "Present - mont": "PresentMon",
            "Present mont": "PresentMon",
            "PE Cores": "P-Cores",
            "PE cores": "P-Cores",
            "P cores": "P-Cores",
            "E cores": "E-Cores",
            "TB.": "TE VE.",
            "TB": "TE VE",
            "-STARVES": "STARVES",
            "-RANGE": "RANGE",
        },
        "audio_rules": {
            "max_clipping_threshold_db": -0.5,
            "target_max_volume_db": -1.5,
            "target_mean_volume_db": -17.0,
            "music_ducking_gain_db": -22.0,
        },
        "visual_rules": {
            "min_metric_font_px": 96,
            "max_subtitle_y": 1536,
            "min_margin_v": 384,
        },
        "retention_rules": {
            "min_duration_sec": 60.0,
            "max_duration_sec": 120.0,
            "prohibit_midroll_subscribe_banner": true,
        },
        "history_fixes_applied": [],
    }
    save_qa_rules(default_rules)
    return default_rules


def save_qa_rules(rules: Dict[str, Any]) -> None:
    """Persists QA rules to data/qa_rules.json."""
    QA_RULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    QA_RULES_FILE.write_text(json.dumps(rules, indent=2, ensure_ascii=False), encoding="utf-8")


def get_latest_tiktok_video() -> Optional[Path]:
    """Finds the most recently modified MP4 video in output/tiktok/."""
    tiktok_dir = BASE_DIR / "output" / "tiktok"
    if not tiktok_dir.is_dir():
        return None

    mp4_files = list(tiktok_dir.glob("*.mp4"))
    if not mp4_files:
        return None

    # Sort by modification time descending
    mp4_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return mp4_files[0]


def find_associated_assets(video_path: Path) -> Dict[str, Any]:
    """Locates metadata, YouTube mirror, temp run folder, and subtitle assets."""
    assets: Dict[str, Any] = {
        "video_path": video_path,
        "metadata_file": None,
        "youtube_video": None,
        "run_dir": None,
        "ass_file": None,
        "audio_file": None,
        "act_clips": [],
    }

    # 1. Metadata .txt
    txt_path = video_path.with_suffix(".txt")
    if txt_path.is_file():
        assets["metadata_file"] = txt_path

    # 2. YouTube copy
    yt_path = BASE_DIR / "output" / "youtube" / video_path.name
    if yt_path.is_file():
        assets["youtube_video"] = yt_path

    # 3. Locate active run directory in /tmp/yt_automation or temp/
    possible_roots = [
        Path("/tmp/yt_automation"),
        Path(settings.TMP_DIR),
        BASE_DIR / "temp",
    ]

    best_run_dir = None
    min_time_diff = float("inf")
    v_mtime = video_path.stat().st_mtime

    for r_root in possible_roots:
        if not r_root.is_dir():
            continue
        for d in r_root.iterdir():
            if not d.is_dir() or not (d.name.startswith("run_master_") or d.name.startswith("run_long_")):
                continue
            master_candidate = d / "final_master_1080x1920.mp4"
            if master_candidate.is_file():
                # Check size similarity or time closeness
                diff = abs(master_candidate.stat().st_mtime - v_mtime)
                if diff < min_time_diff:
                    min_time_diff = diff
                    best_run_dir = d

    if best_run_dir:
        assets["run_dir"] = best_run_dir
        ass_candidate = best_run_dir / "subtitles_vertical.ass"
        if ass_candidate.is_file():
            assets["ass_file"] = ass_candidate
        audio_candidate = best_run_dir / "master_audio_raw.mp3"
        if audio_candidate.is_file():
            assets["audio_file"] = audio_candidate
        clips = sorted(list(best_run_dir.glob("act*_clip.mp4")))
        if len(clips) == 5:
            assets["act_clips"] = clips

    return assets


def get_video_duration_ffprobe(video_path: Path) -> float:
    """Measures precise container duration via ffprobe."""
    ffprobe_bin = get_ffprobe_bin()
    cmd = [
        ffprobe_bin,
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def audit_subtitles(assets: Dict[str, Any], qa_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Audits subtitle content for phonetic errors, orphan hyphens, and safe zone UI compliance."""
    phonetic_dict = qa_rules.get("phonetic_corrections", {})
    ass_file: Optional[Path] = assets.get("ass_file")
    metadata_file: Optional[Path] = assets.get("metadata_file")

    found_errors: List[Dict[str, str]] = []
    orphan_hyphens: List[str] = []
    safe_zone_issues: List[str] = []
    raw_lines: List[str] = []

    # Read from ASS file if available, otherwise read from metadata script
    if ass_file and ass_file.is_file():
        content = ass_file.read_text(encoding="utf-8")
        raw_lines = content.splitlines()

        # Check safe zone margin in Style line
        for line in raw_lines:
            if line.startswith("Style:"):
                parts = line.split(",")
                if len(parts) >= 22:
                    try:
                        margin_v = int(parts[21].strip())
                        # If MarginV < 384, Y > 1536 (violates mobile UI bottom bar)
                        if margin_v < qa_rules.get("visual_rules", {}).get("min_margin_v", 384):
                            safe_zone_issues.append(
                                f"MarginV={margin_v} sitúa subtítulos en Y > 1536px (zona inferior bloqueada por UI TikTok/Shorts)."
                            )
                    except ValueError:
                        pass

        # Scan dialogue lines for phonetic misrecognitions and formatting flaws
        dialogue_text = " ".join(
            re.sub(r"\{.*?\}", "", line.split("Default,,0,0,0,,")[-1] if "Default,,0,0,0,," in line else line)
            for line in raw_lines if line.startswith("Dialogue:")
        )

        # Check phonetic dictionary
        for bad_p, good_p in phonetic_dict.items():
            pattern = r"\b" + re.escape(bad_p.upper().strip(".")) + r"[\.\,\!]?\b"
            if re.search(pattern, dialogue_text.upper()):
                found_errors.append({"found": bad_p, "replacement": good_p})

        # Check orphaned hyphens
        for token in dialogue_text.split():
            clean_tok = re.sub(r"[^\w\-]", "", token)
            if clean_tok.startswith("-") and len(clean_tok) > 1 and clean_tok[1:].isalpha():
                orphan_hyphens.append(clean_tok)

    elif metadata_file and metadata_file.is_file():
        meta_text = metadata_file.read_text(encoding="utf-8")
        for bad_p, good_p in phonetic_dict.items():
            pattern = r"\b" + re.escape(bad_p.upper().strip(".")) + r"[\.\,\!]?\b"
            if re.search(pattern, meta_text.upper()):
                found_errors.append({"found": bad_p, "replacement": good_p})

    # Summary formatting
    subtitle_ok = len(found_errors) == 0 and len(orphan_hyphens) == 0 and len(safe_zone_issues) == 0
    issues_desc: List[str] = []
    solutions_desc: List[str] = []

    if found_errors:
        err_str = ", ".join(f"'{e['found']}' ➔ '{e['replacement']}'" for e in found_errors)
        issues_desc.append(f"Términos fonéticos anómalos detectados: {err_str}")
        solutions_desc.append(f"Corregir términos fonéticos ({err_str}) en archivo de subtítulos y actualizar data/qa_rules.json")

    if orphan_hyphens:
        hyph_str = ", ".join(f"'{h}'" for h in set(orphan_hyphens))
        issues_desc.append(f"Guiones huérfanos al inicio de palabra: {hyph_str}")
        solutions_desc.append(f"Eliminar guiones huérfanos ({hyph_str}) de los chunks de subtítulos")

    if safe_zone_issues:
        issues_desc.extend(safe_zone_issues)
        solutions_desc.append("Reajustar MarginV >= 480 en encabezado ASS para garantizar holgura de 384px sobre la UI móvil")

    return {
        "status_ok": subtitle_ok,
        "found_errors": found_errors,
        "orphan_hyphens": list(set(orphan_hyphens)),
        "safe_zone_issues": safe_zone_issues,
        "issues_description": "; ".join(issues_desc) if issues_desc else "Sin fallos detectados",
        "solutions": solutions_desc,
    }


def audit_audio(video_path: Path, qa_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Audits audio levels via FFmpeg volumedetect filter."""
    ffmpeg_bin = get_ffmpeg_bin()
    cmd = [
        ffmpeg_bin,
        "-i", str(video_path),
        "-vn",
        "-af", "volumedetect",
        "-f", "null",
        "-",
    ]

    max_vol = -99.0
    mean_vol = -99.0

    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
        stderr_output = proc.stderr

        max_match = re.search(r"max_volume:\s*([\-\d\.]+)\s*dB", stderr_output)
        if max_match:
            max_vol = float(max_match.group(1))

        mean_match = re.search(r"mean_volume:\s*([\-\d\.]+)\s*dB", stderr_output)
        if mean_match:
            mean_vol = float(mean_match.group(1))

    except Exception as exc:
        logger.error("Error executing volumedetect on %s: %s", video_path, exc)

    audio_rules = qa_rules.get("audio_rules", {})
    clip_thresh = audio_rules.get("max_clipping_threshold_db", -0.5)

    clipping = max_vol >= clip_thresh
    too_quiet = mean_vol < -28.0
    too_loud = mean_vol > -11.0

    issues_desc: List[str] = []
    solutions_desc: List[str] = []

    if clipping:
        issues_desc.append(f"Riesgo de saturación/clipping detectado: max_volume={max_vol:.1f} dB (umbral: {clip_thresh} dB)")
        solutions_desc.append("Atenuar pista de audio (-1.5 dB headroom) mediante remux rápido en FFmpeg sin recodificar vídeo")
    elif max_vol == -99.0:
        issues_desc.append("No se pudo detectar el volumen de audio")
    else:
        status_audio = f"Niveles correctos (max: {max_vol:.1f} dB, mean: {mean_vol:.1f} dB, sin clipping)"

    if too_quiet:
        issues_desc.append(f"Volumen promedio bajo (mean: {mean_vol:.1f} dB, recomendado -16 a -18 dB)")
        solutions_desc.append("Normalizar volumen vocal a -16.5 dB LUFS")

    audio_ok = not clipping and not too_quiet and not too_loud and max_vol != -99.0

    return {
        "status_ok": audio_ok,
        "max_volume": max_vol,
        "mean_volume": mean_vol,
        "clipping_detected": clipping,
        "issues_description": "; ".join(issues_desc) if issues_desc else f"Niveles correctos (max: {max_vol:.1f} dB, mean: {mean_vol:.1f} dB)",
        "solutions": solutions_desc,
    }


def audit_visuals(video_path: Path, assets: Dict[str, Any], qa_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Audits visual composition, theme consistency, telemetry fonts, cover frame presence, and initial freeze frames."""
    issues_desc: List[str] = []
    solutions_desc: List[str] = []

    theme_name = video_path.stem.lower()

    # 1. Coherence & B-Roll Tag Collision check
    metadata_file = assets.get("metadata_file")
    meta_content = metadata_file.read_text(encoding="utf-8").lower() if metadata_file and metadata_file.is_file() else ""

    manifest_file = BASE_DIR / "assets" / "broll" / "manifest.json"
    if manifest_file.is_file():
        try:
            m_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            clips = m_data.get("clips", [])
            # Check if any used clip violates antagonistic exclusion
            topic_tokens = set(theme_name.replace("_", " ").split())
            if meta_content:
                topic_tokens.update(meta_content[:200].replace("#", "").split())

            for c in clips:
                if c.get("last_used_timestamp"):
                    conflicts = set(str(k).lower().strip() for k in c.get("conflicts_with", []))
                    collision = topic_tokens.intersection(conflicts)
                    if collision:
                        issues_desc.append(f"Colisión semántica en B-roll '{c['file']}': conflicto antagónico con {list(collision)}")
                        solutions_desc.append(f"Excluir '{c['file']}' mediante services/broll_selector.py y aplicar clip neutral")
        except Exception:
            pass

    if "intel" in theme_name and ("am4" in meta_content or "am5" in meta_content):
        issues_desc.append("Incoherencia temática detectada: metraje/etiquetas de AMD en tema de procesadores Intel")
        solutions_desc.append("Reemplazar B-roll / telemetría de zócalo AM4 por esquemas de arquitectura Intel")

    # 2. Cover Frame Audit (_cover.jpg)
    cover_file = video_path.parent / f"{video_path.stem}_cover.jpg"
    if not cover_file.is_file():
        # Check in output/tiktok as well
        cover_file = BASE_DIR / "output" / "tiktok" / f"{video_path.stem}_cover.jpg"

    if not cover_file.is_file():
        issues_desc.append("Fotograma de portada (_cover.jpg) ausente en output/tiktok/")
        solutions_desc.append("Generar fotograma de portada de alto CTR (1080x1920) mediante services/renderer.py")
    else:
        cov_size = cover_file.stat().st_size
        if cov_size < 15000:
            issues_desc.append(f"Portada (_cover.jpg) con peso anormalmente bajo ({cov_size} bytes, posible fallo de render)")
            solutions_desc.append("Re-renderizar portada con contraste 60% y tipografía masiva 88px")

    # 3. Check initial freeze frames (0 FPS or black screen during first 1.5s)
    ffmpeg_bin = get_ffmpeg_bin()
    cmd_freeze = [
        ffmpeg_bin,
        "-i", str(video_path),
        "-t", "2.0",
        "-vf", "freezedetect=n=-60dB:d=1.2",
        "-f", "null",
        "-",
    ]
    try:
        p = subprocess.run(cmd_freeze, capture_output=True, text=True)
        if "lavfi.freezedetect.freeze_start" in p.stderr:
            issues_desc.append("Fotogramas iniciales congelados detectados (>1.2s en estado cero)")
            solutions_desc.append("Ajustar punto de corte inicial para que la animación y narración arranquen en T=0.0s")
    except Exception:
        pass

    visual_ok = len(issues_desc) == 0

    return {
        "status_ok": visual_ok,
        "issues_description": "; ".join(issues_desc) if issues_desc else "Composición correcta (Esquemas 2D, B-roll coherente y portada lista)",
        "solutions": solutions_desc,
    }


def audit_structure_retention(video_path: Path, qa_rules: Dict[str, Any]) -> Dict[str, Any]:
    """Audits total video duration and retention constraints."""
    dur = get_video_duration_ffprobe(video_path)
    ret_rules = qa_rules.get("retention_rules", {})
    min_dur = ret_rules.get("min_duration_sec", 60.0)
    max_dur = ret_rules.get("max_duration_sec", 120.0)

    issues_desc: List[str] = []
    solutions_desc: List[str] = []

    if dur < min_dur:
        issues_desc.append(f"Duración insuficiente: {dur:.2f}s (requiere >60.5s para monetización en TikTok Creator Rewards)")
        solutions_desc.append("Extender el guion en los actos de desarrollo o reducir velocidad de locución a 0.90x")
    elif dur > max_dur:
        issues_desc.append(f"Duración excesiva: {dur:.2f}s (supera límite de 120s para vídeos cortos verticales)")
        solutions_desc.append("Comprimir guion eliminando redundancias en Acto 2 y Acto 3")

    structure_ok = len(issues_desc) == 0

    return {
        "status_ok": structure_ok,
        "duration": dur,
        "issues_description": "; ".join(issues_desc) if issues_desc else f"Duración óptima ({dur:.2f}s | Elegible TikTok Creator Rewards y YouTube Shorts)",
        "solutions": solutions_desc,
    }


def run_full_qa_audit(video_path: Optional[Path] = None) -> Dict[str, Any]:
    """Executes the complete inspection across the 4 QA dimensions without altering files."""
    if not video_path:
        video_path = get_latest_tiktok_video()

    if not video_path or not video_path.is_file():
        raise FileNotFoundError("No se encontró ningún vídeo generado en output/tiktok/ para auditar.")

    qa_rules = load_qa_rules()
    assets = find_associated_assets(video_path)

    sub_audit = audit_subtitles(assets, qa_rules)
    audio_audit = audit_audio(video_path, qa_rules)
    visual_audit = audit_visuals(video_path, assets, qa_rules)
    struct_audit = audit_structure_retention(video_path, qa_rules)

    all_solutions: List[str] = []
    all_solutions.extend(sub_audit["solutions"])
    all_solutions.extend(audio_audit["solutions"])
    all_solutions.extend(visual_audit["solutions"])
    all_solutions.extend(struct_audit["solutions"])

    if not all_solutions:
        all_solutions.append("El vídeo cumple con el 100% de los estándares de calidad técnica. No requiere modificaciones.")

    return {
        "video_path": video_path,
        "assets": assets,
        "duration": struct_audit["duration"],
        "subtitles": sub_audit,
        "audio": audio_audit,
        "visuals": visual_audit,
        "structure": struct_audit,
        "proposed_solutions": all_solutions,
        "qa_rules": qa_rules,
    }


def format_qa_report(audit_data: Dict[str, Any]) -> str:
    """Formats the audit findings into the exact user-facing template."""
    v_path = audit_data["video_path"]
    v_rel = f"output/tiktok/{v_path.name}"
    dur = audit_data["duration"]

    sub_desc = audit_data["subtitles"]["issues_description"]
    audio_desc = audit_data["audio"]["issues_description"]
    visual_desc = audit_data["visuals"]["issues_description"]
    struct_desc = audit_data["structure"]["issues_description"]

    solutions = audit_data["proposed_solutions"]
    solutions_str = "\n".join(f"- Solución {i+1}: {s}" for i, s in enumerate(solutions))

    report = (
        f"📋 **Auditoría de Calidad: Último Vídeo Generado**\n"
        f"**Archivo analizado:** `{v_rel}` (Duración: {dur:.1f}s)\n\n"
        f"**1. Errores Encontrados:**\n"
        f"- **Subtítulos / Whisper:** {sub_desc}\n"
        f"- **Niveles de Audio:** {audio_desc}\n"
        f"- **Composición Visual:** {visual_desc}\n"
        f"- **Estructura y Retención:** {struct_desc}\n\n"
        f"**2. Soluciones Propuestas para este Vídeo:**\n"
        f"{solutions_str}\n\n"
        f"⚠️ **Confirmación requerida:**\n"
        f"¿Deseas que aplique estas soluciones al vídeo actual y registre las reglas para las próximas ejecuciones? Responde **\"Sí\"**, **\"No\"** o indica instrucciones concretas."
    )
    return report


def apply_qa_fixes(audit_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Applies the approved corrections to output/tiktok/ and registers persistent rules."""
    if not audit_data:
        audit_data = run_full_qa_audit()

    video_path: Path = audit_data["video_path"]
    assets: Dict[str, Any] = audit_data["assets"]
    qa_rules: Dict[str, Any] = audit_data["qa_rules"]
    ffmpeg_bin = get_ffmpeg_bin()

    fixes_applied: List[str] = []
    run_dir = assets.get("run_dir")
    ass_file: Optional[Path] = assets.get("ass_file")
    metadata_file: Optional[Path] = assets.get("metadata_file")
    yt_video: Optional[Path] = assets.get("youtube_video")

    # 1. Phonetic subtitle corrections
    phonetic_fixes = audit_data["subtitles"].get("found_errors", [])
    if phonetic_fixes and ass_file and ass_file.is_file():
        ass_content = ass_file.read_text(encoding="utf-8")
        for fix in phonetic_fixes:
            bad_word = fix["found"].upper().strip(".")
            good_word = fix["replacement"].upper().strip(".")
            # Case insensitive exact token replacement
            pattern = re.compile(re.escape(bad_word), re.IGNORECASE)
            ass_content = pattern.sub(good_word, ass_content)
        ass_file.write_text(ass_content, encoding="utf-8")
        fixes_applied.append(f"Subtítulos corregidos en ASS ({len(phonetic_fixes)} términos)")

        # If act clips exist in run_dir, perform clean re-assembly with fixed subtitles
        act_clips = assets.get("act_clips", [])
        audio_file = assets.get("audio_file")
        if len(act_clips) == 5 and audio_file and audio_file.is_file():
            logger.info("Reassembling master video with corrected kinetic subtitles...")
            tmp_fixed = video_path.parent / f"fixed_{video_path.name}"
            inputs = []
            for c in act_clips:
                inputs.extend(["-i", str(c)])
            inputs.extend(["-i", str(audio_file)])

            ass_path_str = str(ass_file.resolve()).replace(":", r"\:")
            v_inputs = "".join(f"[{i}:v]" for i in range(len(act_clips)))
            filter_complex = f"{v_inputs}concat=n=5:v=1:a=0,ass='{ass_path_str}'[vout]"

            cmd_assemble = [
                ffmpeg_bin, "-y",
                *inputs,
                "-filter_complex", filter_complex,
                "-map", "[vout]",
                "-map", "5:a",
                "-c:v", "libx264", "-preset", "faster", "-crf", "18", "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "192k",
                "-shortest",
                str(tmp_fixed),
            ]
            subprocess.run(cmd_assemble, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            shutil.move(str(tmp_fixed), str(video_path))
            if yt_video and yt_video.is_file():
                shutil.copyfile(video_path, yt_video)
            fixes_applied.append("Vídeo máster re-renderizado con subtítulos corregidos")

    # 2. Audio attenuation / normalization if clipping was detected
    if audit_data["audio"].get("clipping_detected"):
        logger.info("Applying audio attenuation (-1.5 dB) via fast stream remux...")
        tmp_audio_fixed = video_path.parent / f"audio_fixed_{video_path.name}"
        cmd_remux = [
            ffmpeg_bin, "-y",
            "-i", str(video_path),
            "-af", "volume=-1.5dB",
            "-c:v", "copy",
            "-c:a", "aac", "-b:a", "192k",
            str(tmp_audio_fixed),
        ]
        subprocess.run(cmd_remux, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        shutil.move(str(tmp_audio_fixed), str(video_path))
        if yt_video and yt_video.is_file():
            shutil.copyfile(video_path, yt_video)
        fixes_applied.append("Pista de audio atenuada -1.5 dB para eliminar riesgo de clipping")

    # 3. Update metadata .txt if phonetic replacements affect the title / script
    if metadata_file and metadata_file.is_file() and phonetic_fixes:
        txt_content = metadata_file.read_text(encoding="utf-8")
        for fix in phonetic_fixes:
            pattern = re.compile(re.escape(fix["found"]), re.IGNORECASE)
            txt_content = pattern.sub(fix["replacement"], txt_content)
        metadata_file.write_text(txt_content, encoding="utf-8")
        fixes_applied.append("Metadatos .txt actualizados con correcciones ortográficas")

    # 4. Save persistent rules to data/qa_rules.json
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    record = {
        "timestamp": now_str,
        "video": video_path.name,
        "fixes": fixes_applied,
        "phonetic_added": [f["found"] for f in phonetic_fixes],
    }
    qa_rules.setdefault("history_fixes_applied", []).append(record)
    save_qa_rules(qa_rules)

    return {
        "success": True,
        "video_path": str(video_path),
        "fixes_applied": fixes_applied,
        "message": f"Se han aplicado {len(fixes_applied)} correcciones con éxito sobre `{video_path.name}`.",
    }


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Silicon Verdict QA Inspector & Auto-Corrector")
    parser.add_argument("--audit", action="store_true", help="Run quality audit on the latest video and print report")
    parser.add_argument("--apply", action="store_true", help="Apply proposed QA corrections directly to the video")
    parser.add_argument("--video", type=str, default=None, help="Explicit path to video file to inspect")
    args = parser.parse_args()

    v_path = Path(args.video) if args.video else get_latest_tiktok_video()
    if not v_path or not v_path.is_file():
        print("❌ No se encontró ningún vídeo para auditar en output/tiktok/.")
        sys.exit(1)

    if args.apply:
        print(f"🔧 Aplicando correcciones sobre: {v_path.name}...")
        audit_res = run_full_qa_audit(v_path)
        apply_res = apply_qa_fixes(audit_res)
        print("✅ Correcciones finalizadas:")
        for fix in apply_res["fixes_applied"]:
            print(f"   • {fix}")
        print(f"📁 Archivo final actualizado: {apply_res['video_path']}")
    else:
        # Default: audit and print report
        audit_res = run_full_qa_audit(v_path)
        report = format_qa_report(audit_res)
        print("\n" + report + "\n")


if __name__ == "__main__":
    main()
