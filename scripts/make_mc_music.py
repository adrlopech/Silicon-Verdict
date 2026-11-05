"""Generates the original background music loop for the Minecraft series (no third-party music, so no rights issues).

Soft pad + plucked arpeggio + bass in C minor (Cm - Ab - Eb - Bb), 100 BPM, 16 bars (~38 s), written to assets/audio/mc_bed.wav.
Run: python3 scripts/make_mc_music.py
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
BPM = 100
BEAT = 60 / BPM
BAR = 4 * BEAT
CHORDS = [[48, 51, 55], [44, 48, 51], [51, 55, 58], [46, 50, 53]]  # MIDI notes: Cm, Ab, Eb, Bb (root, third, fifth)
OUT = Path(__file__).resolve().parent.parent / "assets" / "audio" / "mc_bed.wav"


def hz(m): return 440.0 * 2 ** ((m - 69) / 12)


def tri(f, t): return 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * t))


def pluck(f, dur, vol):
    t = np.arange(int(SR * dur)) / SR
    env = np.exp(-t * 7.0) * np.minimum(1, t * 400)
    wav = (np.sign(np.sin(2 * np.pi * f * t)) * 0.35 + tri(f * 2, t) * 0.4 + tri(f, t) * 0.5) * env
    return wav * vol


def build() -> np.ndarray:
    bars = 16
    n = int(SR * BAR * bars)
    mix = np.zeros(n)
    for b in range(bars):
        chord = CHORDS[b % 4]
        s = int(SR * BAR * b)
        L = int(SR * BAR)
        t = np.arange(L) / SR
        env = np.minimum(1, t / 0.6) * np.minimum(1, (BAR - t) / 0.6)  # pad: slow swell per bar
        pad = sum(tri(hz(m + 12), t) + 0.5 * tri(hz(m + 12) * 1.004, t) for m in chord) / 6 * env
        mix[s:s + L] += pad * 0.28
        bass = tri(hz(chord[0] - 12), t) * np.minimum(1, t / 0.05) * (0.6 + 0.4 * np.exp(-t * 1.2))
        mix[s:s + L] += bass * 0.30
        pattern = [0, 1, 2, 1, 2, 1, 0, 2]  # 8th-note arpeggio, an octave up on the second half of the 4-bar phrase
        for k, idx in enumerate(pattern):
            note = chord[idx] + 12 + (12 if (b % 4) >= 2 and k % 4 == 3 else 0)
            p = pluck(hz(note), 0.5, 0.20)
            o = s + int(SR * k * BEAT / 2)
            mix[o:o + len(p)] += p[: max(0, min(len(p), n - o))]
    # simple feedback echo for space, then fade the loop edges so it repeats seamlessly
    d = int(SR * BEAT * 0.75)
    echo = mix.copy()
    echo[d:] += mix[:-d] * 0.35
    echo[2 * d:] += mix[:-2 * d] * 0.15
    echo /= max(1e-9, np.abs(echo).max()) / 0.8
    fade = int(SR * 0.05)
    echo[:fade] *= np.linspace(0, 1, fade)
    echo[-fade:] *= np.linspace(1, 0, fade)
    return echo


def main() -> None:
    a = build()
    pcm = (a * 32767).astype("<i2")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {OUT} ({len(a) / SR:.1f} s)")


if __name__ == "__main__":
    main()
