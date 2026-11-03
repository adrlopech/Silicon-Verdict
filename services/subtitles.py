"""Kinetic synchronized subtitles service using faster-whisper and ASS styling.

Produces word-by-word highlighted subtitle cards conforming to YouTube Shorts
Safe Zone parameters:
- Baseline Y: 1380..1400 (MarginV: 520 on 1080x1920)
- Margins: MarginL: 140, MarginR: 180
- Active Word: Neon Cyan (&H00FFF200& BGR) scaled \fscx108\fscy108
- Inactive Words: Dimmed White (&H66FFFFFF&)
- Word grouping: 2 to 3 words maximum per block
"""
import logging
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import av

# Ensure compatibility between newer PyAV versions and faster-whisper
_orig_av_open = av.open


def _safe_av_open(*args, **kwargs):
    kwargs.pop("metadata_errors", None)
    return _orig_av_open(*args, **kwargs)


av.open = _safe_av_open

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)


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


def build_ass_header(font_name: str = "Montserrat", font_size: int = 72) -> str:
    """Builds standard ASS v4+ header calibrated to 1080x1920 Shorts Safe Zone."""
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


def generate_kinetic_subtitles(
    audio_path: Path,
    output_ass_path: Path,
    model_size: str = "base",
    fallback_words: Optional[List[str]] = None,
) -> Path:
    """Transcribes audio using faster-whisper and writes a word-by-word kinetic ASS subtitle file.

    Parameters:
    - audio_path: Path to input audio (.mp3, .wav, etc.)
    - output_ass_path: Destination .ass subtitle file path
    - model_size: Whisper model size (default "base")
    - fallback_words: Optional fallback word list if audio has no detectable speech
    """
    audio_path = Path(audio_path)
    output_ass_path = Path(output_ass_path)
    output_ass_path.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Generating kinetic subtitles with Whisper ('%s') for: %s", model_size, audio_path.name)
    model = WhisperModel(model_size, device="auto", compute_type="default")

    segments, info = model.transcribe(
        str(audio_path),
        language="en",
        word_timestamps=True,
    )

    extracted_words: List[Dict] = []
    for segment in segments:
        for w in (segment.words or []):
            clean_word = re.sub(r"[^\w\+\%\$\#\-\'\.]", "", w.word).strip()
            if clean_word:
                extracted_words.append({
                    "word": clean_word,
                    "start": float(w.start),
                    "end": float(w.end),
                })

    # If audio is silent (e.g. offline smoke test dummy audio), generate representative fallback words
    if not extracted_words:
        logger.warning("No words detected by Whisper (silent/dummy audio). Using kinetic test phrase.")
        default_phrase = fallback_words or [
            "WHY", "8GB", "VRAM", "IS", "OFFICIALLY", "DEAD", "FOR", "MODERN", "GAMING"
        ]
        duration = 4.0
        step = max(duration / len(default_phrase), 0.35)
        cur_t = 0.3
        for w in default_phrase:
            extracted_words.append({
                "word": w,
                "start": cur_t,
                "end": cur_t + step * 0.85,
            })
            cur_t += step

    chunks = group_words_into_chunks(extracted_words, max_words=3)
    logger.info("Organized %d words into %d kinetic subtitle chunks (2-3 words/screen)", len(extracted_words), len(chunks))

    dialogue_lines: List[str] = []

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
                    # Active word: Neon Cyan (&H00FFF200& BGR) with scale \fscx108\fscy108
                    formatted_tokens.append(
                        f"{{\\c&H00FFF200&\\1a&H00&\\fscx108\\fscy108}}{token_text}{{\\c&HFFFFFF&\\1a&H66&\\fscx100\\fscy100}}"
                    )
                else:
                    # Inactive word: Dimmed White (&H66FFFFFF&)
                    formatted_tokens.append(
                        f"{{\\c&HFFFFFF&\\1a&H66&\\fscx100\\fscy100}}{token_text}"
                    )

            event_text = " ".join(formatted_tokens)
            dialogue_lines.append(
                f"Dialogue: 0,{t_start_str},{t_end_str},Default,,0,0,0,,{event_text}"
            )

    ass_content = build_ass_header(font_name="Montserrat", font_size=72) + "\n".join(dialogue_lines) + "\n"
    output_ass_path.write_text(ass_content, encoding="utf-8")
    logger.info("Kinetic ASS subtitles written successfully to: %s", output_ass_path)
    return output_ass_path
