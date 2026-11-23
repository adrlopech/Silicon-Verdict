"""Audio synthesis and modulation service for Silicon Verdict single master videos.

Calibrated for:
- tech_curiosities (Storytelling / Tecnología Desmontada):
  * Speed: 0.92x (measured, serene, didactic rhythm).
  * ElevenLabs Voice Settings:
      - stability: 0.75
      - similarity_boost: 0.80
      - style: 0.12 (calm/intellectual)
      - use_speaker_boost: True
- Hardware Benchmarks / Gaming:
  * Speed: 1.00x - 1.02x
  * Standard energetic narration settings.
- Generates a SINGLE master audio track per execution.
- Validates and enforces runtime strictly between 60.0 and 120.0 seconds.
"""
import logging
import re



logger = logging.getLogger(__name__)


def normalize_phonetics_us_english(text: str) -> str:
    """Normalizes acronyms and technical terms according to standard US English phonetic rules."""
    replacements = [
        (r"\b1440p\b", "fourteen-forty p"),
        (r"\b1080p\b", "ten-eighty p"),
        (r"\b4[kK]\b", "4-K"),
        (r"\bFPS\b", "F-P-S"),
        (r"\bfps\b", "F-P-S"),
        (r"\bRTX\b", "R-T-X"),
        (r"\bDLSS\b", "D-L-S-S"),
        (r"\bFSR\b", "F-S-R"),
        (r"\bPCIe\b", "P-C-I-e"),
        (r"\bVCSEL\b", "V-C-S-E-L"),
        (r"\bMEMS\b", "M-E-M-S"),
        (r"\bNFC\b", "N-F-C"),
        (r"\bGPS\b", "G-P-S"),
        (r"\bASML\b", "A-S-M-L"),
        (r"\bTSMC\b", "T-S-M-C"),
        (r"\bCCD\b", "C-C-D"),
        (r"\bCCDs\b", "C-C-Ds"),
        (r"\bSoIC\b", "S-O-I-C"),
        (r"\bIHS\b", "I-H-S"),
        (r"\bVRM\b", "V-R-M"),
        (r"\bVRMs\b", "V-R-Ms"),
        (r"\bGHz\b", "gigahertz"),
        (r"\bMHz\b", "megahertz"),
        (r"\bGbps\b", "gigabits per second"),
        (r"\bTbps\b", "terabits per second"),
        (r"\bnanoseconds\b", "nano-seconds"),
        (r"\bnanosecond\b", "nano-second"),
        (r"\bns\b", "nano-seconds"),
        (r"\bSRAM\b", "S-RAM"),
        (r"\bsub-11\b", "sub eleven"),
        (r"\bsub-eleven\b", "sub eleven"),
        (r"\bms\b", "milliseconds"),
    ]
    norm = text
    for pattern, repl in replacements:
        norm = re.sub(pattern, repl, norm)
    return norm


