"""Kinetic synchronized subtitles service using faster-whisper and ASS styling.

Produces word-by-word highlighted subtitle cards conforming to YouTube Shorts
Safe Zone parameters:
- Baseline Y: 1380..1400 (MarginV: 520 on 1080x1920)
- Margins: MarginL: 140, MarginR: 180
- Active Word: Neon Cyan (&H00FFF200& BGR) scaled \fscx108\fscy108
- Inactive Words: Dimmed White (&H66FFFFFF&)
- Word grouping: 2 to 3 words maximum per block
"""
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

import av

# Ensure compatibility between newer PyAV versions and faster-whisper
_orig_av_open = av.open


def _safe_av_open(*args, **kwargs):
    kwargs.pop("metadata_errors", None)
    return _orig_av_open(*args, **kwargs)


av.open = _safe_av_open

from faster_whisper import WhisperModel

from config.settings import settings

logger = logging.getLogger(__name__)


def apply_qa_phonetic_rules(word: str) -> str:
    """Applies persistent phonetic corrections from data/qa_rules.json."""
    rules_file = settings.BASE_DIR / "data" / "qa_rules.json"
    if not rules_file.is_file():
        return word
    try:
        data = json.loads(rules_file.read_text(encoding="utf-8"))
        corrections = data.get("phonetic_corrections", {})
        # Strip orphan leading hyphen (e.g. -RANGE -> RANGE)
        if word.startswith("-") and len(word) > 1 and word[1:].isalnum():
            word = word[1:]
        clean_upper = word.upper().strip()
        for bad_p, good_p in corrections.items():
            if clean_upper == bad_p.upper().strip():
                return good_p
    except Exception:
        pass
    return word


def format_ass_time(seconds: float) -> str:
    """Converts seconds into ASS timecode format: H:MM:SS.cs (centiseconds)."""
    if seconds < 0.0:
        seconds = 0.0
    total_centis = int(round(seconds * 100))
    centis = total_centis % 100
    total_secs = total_centis // 100
    secs = total_secs % 60
    total_mins = total_secs // 60
    mins = total_mins % 60
    hours = total_mins // 60
    return f"{hours}:{mins:02d}:{secs:02d}.{centis:02d}"


def group_words_into_chunks(words: List[Dict], max_words: int = 3) -> List[List[Dict]]:
    """Groups words into short chunks of 2 to 3 words for compact Shorts display."""
    chunks = []
    i = 0
    n = len(words)
    while i < n:
        rem = n - i
        if rem == 4:
            take = 2
        elif rem >= max_words:
            take = max_words
        else:
            take = rem
        chunks.append(words[i : i + take])
        i += take
    return chunks


def build_ass_header(
    font_name: str = "Montserrat",
    font_size: int = 72,
    preset: str = "default",
) -> str:
    """Builds standard ASS v4+ header calibrated to 1080x1920 Shorts Safe Zone."""
    if preset == "schematic_tech":
        # Schematic Tech typography: Clean heavy sans-serif, pure white base, electric cyan secondary
        return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H00F8BD38,&H000E0907,&H80000000,-1,0,0,0,100,100,0,0,1,3,6,2,140,180,480,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    return f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H66FFFFFF,&H00FFF200,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,4,8,2,140,180,520,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def fuse_technical_tokens(raw_tokens: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Automatically fuses compound units, broken acronyms, and technical figures:
    - Wi + Fi -> Wi-Fi
    - Numbers + units: '2.4' + 'GHz' -> '2.4 GHz', '1000' + 'W' -> '1000 W'
    - Acronyms: 'P' + 'Cores' -> 'P-Cores', '1%' + 'Low' -> '1% Low'
    """
    fused = []
    i = 0
    n = len(raw_tokens)

    while i < n:
        curr = raw_tokens[i]
        curr_word = curr["word"].strip().upper().replace(",", "").replace(".", "")

        if i + 1 < n:
            next_t = raw_tokens[i + 1]
            next_word = next_t["word"].strip().upper().replace(",", "").replace(".", "")

            # Fusión por acrónimos rotos
            if curr_word in ["WI"] and next_word in ["FI"]:
                fused.append({"word": "WI-FI", "start": curr["start"], "end": next_t["end"]})
                i += 2
                continue

            # Fusión de número + unidad (GHz, MHz, W, Watts, GB/s, ms, FPS, ns, kB, MB, TB)
            if re.match(r"^\d+(\.\d+)?$", curr_word) and next_word in [
                "GHZ", "MHZ", "W", "WATTS", "MS", "FPS", "GB/S", "KB", "NS", "MB", "TB", "GB"
            ]:
                fused.append({"word": f"{curr_word} {next_word}", "start": curr["start"], "end": next_t["end"]})
                i += 2
                continue

            # Fusión de P-Cores, E-Cores, 1% Low, etc.
            if curr_word in ["P", "E"] and next_word in ["CORES", "CORE"]:
                fused.append({"word": f"{curr_word}-CORES", "start": curr["start"], "end": next_t["end"]})
                i += 2
                continue

            if curr_word in ["1%"] and next_word in ["LOW", "LOWS"]:
                fused.append({"word": f"{curr_word} {next_word}", "start": curr["start"], "end": next_t["end"]})
                i += 2
                continue

        fused.append({"word": curr_word, "start": curr["start"], "end": curr["end"]})
        i += 1

    return fused


def extract_word_timestamps(
    audio_path: Path,
    model_size: str = "base",
    fallback_script: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Transcribes audio using faster-whisper or returns cached ElevenLabs alignment tokens if available."""
    audio_path = Path(audio_path)

    # Check for direct ElevenLabs timestamps first (Zero-Whisper optimization)
    candidate_whisper_paths = [
        audio_path.parent / "whisper.json",
        settings.BASE_DIR / "remotion_studio" / "public" / "data" / "whisper.json",
        settings.BASE_DIR / "remotion_studio" / "public" / "whisper.json",
    ]
    for c_path in candidate_whisper_paths:
        if c_path.is_file():
            try:
                tokens = json.loads(c_path.read_text(encoding="utf-8"))
                if isinstance(tokens, list) and len(tokens) > 0 and "word" in tokens[0]:
                    logger.info("Loaded %d native ElevenLabs word timestamps from %s (0.00s inference)", len(tokens), c_path.name)
                    return tokens
            except Exception:
                pass

    logger.info("Extracting word timestamps with Whisper ('%s') for: %s", model_size, audio_path.name)
    try:
        model = WhisperModel(model_size, device="auto", compute_type="default")
    except Exception as exc:
        logger.warning("Default Whisper initialization failed (%s). Retrying with CPU int8...", exc)
        model = WhisperModel(model_size, device="cpu", compute_type="int8")

    # Dynamic brand-tailored initial prompt to eliminate cross-brand terminology bleed
    script_lower = (fallback_script or "").lower()
    if any(k in script_lower for k in ["ryzen", "3d v-cache", "v-cache", "vcache", "zen", "x3d", "am5"]):
        dyn_prompt = "Silicon Verdict, AMD Ryzen, Zen 5, 3D V-Cache, CCD, I/O Die, Infinity Fabric, TSMC SoIC, 64MB SRAM, nano-seconds, AM5, Socket, Cache L3"
    elif any(k in script_lower for k in ["intel", "core ultra", "raptor lake", "arrow lake"]):
        dyn_prompt = "Silicon Verdict, Intel Core Ultra, P-Cores, E-Cores, Thread Director, Compute Tile, SoC Tile, Foveros, nano-seconds, LGA1851"
    elif any(k in script_lower for k in ["wifi", "wi-fi", "microwave", "magnetron", "ghz", "rf"]):
        dyn_prompt = "Silicon Verdict, 2.4 GHz, 5 GHz, Wi-Fi 6E, Wi-Fi 7, Magnetron, Microwave, ISM Band, dBm, attenuation, RF interference"
    else:
        dyn_prompt = "Silicon Verdict, PresentMon, 1440p, DLSS 3.5, Frame Generation, Zen Cores, Ray Tracing, VRAM, PCIe, Ryzen, Cache L3"

    transcribe_kwargs = {
        "language": "en",
        "task": "transcribe",
        "word_timestamps": True,
        "vad_filter": True,
        "initial_prompt": dyn_prompt,
    }

    try:
        segments_gen, info = model.transcribe(
            str(audio_path),
            **transcribe_kwargs,
        )
        segments = list(segments_gen)
    except RuntimeError as r_err:
        if "onnxruntime" in str(r_err).lower() or "vad" in str(r_err).lower():
            logger.warning("VAD filter requires onnxruntime which is unavailable in this environment (%s). Retrying with vad_filter=False...", r_err)
            transcribe_kwargs["vad_filter"] = False
            segments_gen, info = model.transcribe(
                str(audio_path),
                **transcribe_kwargs,
            )
            segments = list(segments_gen)
        else:
            raise

    extracted_words: List[Dict[str, Any]] = []
    for segment in segments:
        for w in (segment.words or []):
            clean_word = re.sub(r"[^\w\+\%\$\#\-\'\.]", "", w.word).strip()
            if clean_word:
                clean_word = apply_qa_phonetic_rules(clean_word)
                extracted_words.append({
                    "word": clean_word,
                    "start": float(w.start),
                    "end": float(w.end),
                })

    if not extracted_words:
        logger.warning("No words detected by Whisper. Using fallback script words.")
        default_phrase = fallback_script.split() if fallback_script else ["SILICON", "VERDICT", "NEXT", "GEN", "HARDWARE", "TELEMETRY"]
        duration = 5.0
        step = max(duration / len(default_phrase), 0.35)
        cur_t = 0.3
        for w in default_phrase:
            extracted_words.append({
                "word": w,
                "start": cur_t,
                "end": cur_t + step * 0.85,
            })
            cur_t += step

    return fuse_technical_tokens(extracted_words)


def generate_kinetic_subtitles(
    audio_path: Path,
    output_ass_path: Path,
    model_size: str = "base",
    fallback_words: Optional[List[str]] = None,
    preset: str = "default",
    language: Optional[str] = None,
) -> Path:
    """Transcribes audio using faster-whisper and writes a word-by-word kinetic ASS subtitle file.

    Parameters:
    - audio_path: Path to input audio (.mp3, .wav, etc.)
    - output_ass_path: Destination .ass subtitle file path
    - model_size: Whisper model size (default "base")
    - fallback_words: Optional fallback word list if audio has no detectable speech
    - preset: Visual subtitle preset ('default' or 'schematic_tech')
    - language: Optional language code ('es', 'en', or None for auto-detect)
    """
    audio_path = Path(audio_path)
    output_ass_path = Path(output_ass_path)
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)

    fallback_str = " ".join(fallback_words) if fallback_words else None
    extracted_words = extract_word_timestamps(audio_path, model_size=model_size, fallback_script=fallback_str)

    chunks = group_words_into_chunks(extracted_words, max_words=3)
    logger.info("Organized %d words into %d kinetic subtitle chunks (2-3 words/screen)", len(extracted_words), len(chunks))

    dialogue_lines: List[str] = []

    # Color codes
    # In ASS, BGR format:
    # Electric Cyan (#38BDF8): B=F8, G=BD, R=38 -> &H00F8BD38&
    # Neon Cyan (#00F2FF): B=FF, G=F2, R=00 -> &H00FFF200&
    # Cool Gray (#94A3B8): B=B8, G=A3, R=94 -> &H00B8A394&
    active_color = "&H00F8BD38&" if preset == "schematic_tech" else "&H00FFF200&"
    inactive_color = "&H00B8A394&" if preset == "schematic_tech" else "&H66FFFFFF&"

    for chunk in chunks:
        chunk_start = chunk[0]["start"]
        chunk_end = max(chunk[-1]["end"], chunk_start + 0.4)

        for k, active_w in enumerate(chunk):
            w_start = active_w["start"]
            # Active word duration extends to next word or chunk end
            if k < len(chunk) - 1:
                w_end = max(chunk[k + 1]["start"], w_start + 0.15)
            else:
                w_end = max(chunk_end, w_start + 0.2)

            t_start_str = format_ass_time(w_start)
            t_end_str = format_ass_time(w_end)

            formatted_tokens = []
            for j, token in enumerate(chunk):
                token_text = token["word"].upper().replace("{", "").replace("}", "").replace("\\", "")
                if j == k:
                    # Active word: Highlighted cyan scaled \fscx108\fscy108
                    formatted_tokens.append(
                        f"{{\\c{active_color}\\1a&H00&\\fscx108\\fscy108}}{token_text}{{\\c&HFFFFFF&\\1a&H00&\\fscx100\\fscy100}}"
                    )
                else:
                    # Inactive word: Cool gray or Dimmed white
                    formatted_tokens.append(
                        f"{{\\c{inactive_color}\\fscx100\\fscy100}}{token_text}"
                    )

            event_text = " ".join(formatted_tokens)
            dialogue_lines.append(
                f"Dialogue: 0,{t_start_str},{t_end_str},Default,,0,0,0,,{event_text}"
            )

    font_choice = "Inter" if os.path.isfile(str(settings.BASE_DIR / "assets" / "fonts" / "Inter-Bold.ttf")) else "Montserrat"
    ass_content = build_ass_header(font_name=font_choice, font_size=72, preset=preset) + "\n".join(dialogue_lines) + "\n"
    output_ass_path.write_text(ass_content, encoding="utf-8")
    logger.info("Kinetic ASS subtitles (%s preset) written successfully to: %s", preset, output_ass_path)
    return output_ass_path
