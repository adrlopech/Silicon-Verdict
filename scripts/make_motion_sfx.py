"""Generates the original sound-design assets of the Motion series (no third-party audio, so no rights issues):

  assets/audio/motion_bed.wav   a quiet electronic pulse loop (A minor, 108 BPM, 8 bars): sub bass, soft pad, sparse ticks
  assets/audio/sfx_riser.wav    1.0 s rising sweep that lands on a data reveal (counter, versus, verdict, timeline)
  assets/audio/sfx_hit.wav      0.6 s low impact for the first frame and for flash scenes

Run: .venv/bin/python scripts/make_motion_sfx.py
"""
import wave
from pathlib import Path

import numpy as np

SR = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "audio"
RNG = np.random.default_rng(7)


def write(name: str, data: np.ndarray, peak: float = 0.8) -> None:
    data = data / max(1e-9, np.abs(data).max()) * peak
    pcm = (np.clip(data, -1, 1) * 32767).astype("<i2")
    with wave.open(str(OUT / name), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print(f"wrote {name} ({len(data) / SR:.1f} s)")


def hz(m: float) -> float:
    return 440.0 * 2 ** ((m - 69) / 12)


def tri(f, t):
    return 2 / np.pi * np.arcsin(np.sin(2 * np.pi * f * t))


def lowpass(x: np.ndarray, cutoff: np.ndarray) -> np.ndarray:
    """One-pole low-pass whose cutoff (Hz) may change per sample."""
    a = 1 - np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x)
    acc = 0.0
    for i in range(len(x)):
        acc += a[i] * (x[i] - acc)
        y[i] = acc
    return y


def bed() -> np.ndarray:
    bpm, bars = 108, 8
    beat = 60 / bpm
    bar = 4 * beat
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]  # Am, F, C, G
    mix = np.zeros(int(SR * bar * bars))
    for b in range(bars):
        chord = chords[b % 4]
        s, length = int(SR * bar * b), int(SR * bar)
        t = np.arange(length) / SR
        swell = np.minimum(1, t / 0.8) * np.minimum(1, (bar - t) / 0.8)
        pad = sum(tri(hz(m), t) + 0.5 * tri(hz(m) * 1.005, t) for m in chord) / 6 * swell
        mix[s:s + length] += pad * 0.30
        for k in range(4):  # sub bass pulse on every beat, soft attack
            o = s + int(SR * k * beat)
            n = int(SR * beat * 0.9)
            tt = np.arange(n) / SR
            note = np.sin(2 * np.pi * hz(chord[0] - 24) * tt) * np.minimum(1, tt / 0.02) * np.exp(-tt * 3.2)
            mix[o:o + n] += note[: max(0, min(n, len(mix) - o))] * (0.55 if k % 2 == 0 else 0.38)
        for k in range(8):  # off-beat ticks: very short filtered noise
            o = s + int(SR * (k + 0.5) * beat / 2)
            n = int(SR * 0.05)
            tick = RNG.standard_normal(n) * np.exp(-np.arange(n) / SR * 90)
            tick = np.diff(tick, prepend=0)
            mix[o:o + n] += tick[: max(0, min(n, len(mix) - o))] * 0.10
    fade = int(SR * 0.04)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix


def riser() -> np.ndarray:
    n = int(SR * 1.0)
    t = np.arange(n) / SR
    noise = lowpass(RNG.standard_normal(n), 300 + 7000 * (t / 1.0) ** 2)
    sweep = np.sin(2 * np.pi * np.cumsum(180 + 1500 * (t / 1.0) ** 2) / SR)
    env = (t / 1.0) ** 1.6
    out = (noise * 0.9 + sweep * 0.45) * env
    out[-int(SR * 0.012):] *= np.linspace(1, 0, int(SR * 0.012))  # cut right before the reveal
    return out


def hit() -> np.ndarray:
    n = int(SR * 0.6)
    t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * np.cumsum(95 * np.exp(-t * 7) + 38) / SR) * np.exp(-t * 5.5)
    burst = lowpass(RNG.standard_normal(n), 2400 * np.exp(-t * 14) + 200) * np.exp(-t * 18)
    return thump + burst * 0.5


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    write("motion_bed.wav", bed(), 0.7)
    write("sfx_riser.wav", riser(), 0.8)
    write("sfx_hit.wav", hit(), 0.9)
