"""Generates the original sound-design assets of the Motion series (no third-party audio, so no rights issues).

Music beds (loops, quiet under the voice; the formats pick one in services/motion_pipeline.py MUSIC_BY_FORMAT):
  motion_bed.wav   pulse    electronic pulse, A minor, 108 BPM            bed_chill.mp3   chill    lo-fi keys and soft beat, 78 BPM
  bed_drive.mp3    drive    four-on-the-floor synthwave, 124 BPM           bed_dark.mp3    dark     slow drone and heartbeat, 70 BPM
  bed_bright.mp3   bright   upbeat plucks and claps, C major, 112 BPM      bed_minimal.mp3 minimal  clicky minimal groove, 118 BPM
  bed_epic.mp3     epic     cinematic pad and timpani, 96 BPM
Effects (short wav files):
  sfx_riser, sfx_hit      rise into a data reveal / low impact          sfx_boom      big impact          sfx_click   mouse click
  sfx_pop     UI pop (a grab, a chip landing)                           sfx_tick      counter tick        sfx_swish   quick swipe (a selection)
  sfx_slide   downward slide                                            sfx_whoosh_soft  gentle scene change   sfx_chime   success (a fact, the outro)
  sfx_error   low buzz (a myth)                                         sfx_type      key click           sfx_glitch  digital stutter
  sfx_ding    notification                                              sfx_sparkle   bright reveal

Run: .venv/bin/python scripts/make_motion_sfx.py   (the beds are written as mp3 with ffmpeg: about a tenth of the size of wav)
"""
import subprocess
import sys
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


# ───────────── more beds ─────────────

def noise(n: int) -> np.ndarray:
    return RNG.standard_normal(n)


def kick(vol=1.0, dur=0.28, f0=120, f1=42) -> np.ndarray:
    t = np.arange(int(SR * dur)) / SR
    return np.sin(2 * np.pi * np.cumsum(f1 + (f0 - f1) * np.exp(-t * 28)) / SR) * np.exp(-t * 11) * vol


def hat(vol=1.0, dur=0.05, decay=90) -> np.ndarray:
    n = int(SR * dur)
    return np.diff(noise(n), prepend=0) * np.exp(-np.arange(n) / SR * decay) * vol


def clap(vol=1.0) -> np.ndarray:
    n = int(SR * 0.16)
    t = np.arange(n) / SR
    burst = np.diff(noise(n), prepend=0)
    return burst * (np.exp(-t * 26) + 0.6 * np.exp(-((t - 0.02) ** 2) * 6000)) * vol


def saw(f, t) -> np.ndarray:
    return 2 * ((f * t) % 1.0) - 1.0


def place(mix: np.ndarray, sound: np.ndarray, at: float) -> None:
    o = int(SR * at)
    if o < len(mix):
        mix[o:o + len(sound)] += sound[: max(0, min(len(sound), len(mix) - o))]


def finish(mix: np.ndarray, echo_beats: float = 0.0, bpm: int = 100) -> np.ndarray:
    if echo_beats:
        d = int(SR * 60 / bpm * echo_beats)
        e = mix.copy()
        e[d:] += mix[:-d] * 0.32
        e[2 * d:] += mix[:-2 * d] * 0.14
        mix = e
    fade = int(SR * 0.04)
    mix[:fade] *= np.linspace(0, 1, fade)
    mix[-fade:] *= np.linspace(1, 0, fade)
    return mix


def bed_chill() -> np.ndarray:
    bpm, bars = 78, 8
    beat = 60 / bpm
    bar = 4 * beat
    chords = [[53, 57, 60, 64], [52, 55, 59, 62], [50, 53, 57, 60], [48, 52, 55, 59]]  # Fmaj7 Em7 Dm7 Cmaj7
    mix = np.zeros(int(SR * bar * bars))
    for b in range(bars):
        ch = chords[b % 4]
        t0 = b * bar
        for k, m in enumerate([ch[0], ch[2], ch[1], ch[3], ch[2], ch[1], ch[3], ch[2]]):  # soft electric-piano arpeggio, 8th notes
            n = int(SR * 0.9)
            t = np.arange(n) / SR
            f = hz(m + 12)
            key = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * 2 * f * t) + 0.12 * np.sin(2 * np.pi * 3 * f * t)) * np.exp(-t * 3.4) * np.minimum(1, t * 220)
            place(mix, key * 0.16, t0 + k * beat / 2)
        n = int(SR * bar)
        t = np.arange(n) / SR
        place(mix, np.sin(2 * np.pi * hz(ch[0] - 24) * t) * np.minimum(1, t / 0.05) * np.exp(-t * 0.7) * 0.42, t0)  # sub bass, one long note per bar
        place(mix, kick(0.5), t0)
        place(mix, kick(0.38), t0 + 2.5 * beat)
        for k in range(8):
            place(mix, hat(0.045, 0.05, 130), t0 + (k + 0.5) * beat / 2)
        for _ in range(5):  # vinyl crackle
            place(mix, hat(0.05, 0.004, 900), t0 + RNG.random() * bar)
    return finish(mix, 0.75, bpm)


def bed_drive() -> np.ndarray:
    bpm, bars = 124, 8
    beat = 60 / bpm
    bar = 4 * beat
    roots = [45, 41, 36, 43]  # A F C G
    chords = [[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]]
    mix = np.zeros(int(SR * bar * bars))
    for b in range(bars):
        r = roots[b % 4]
        ch = chords[b % 4]
        t0 = b * bar
        for k in range(8):  # driving 8th-note bass, a saw softened by averaging
            n = int(SR * beat / 2 * 0.95)
            t = np.arange(n) / SR
            s_ = saw(hz(r), t)
            s_ = np.convolve(s_, np.ones(14) / 14, mode="same")
            place(mix, s_ * np.exp(-t * 6) * 0.34, t0 + k * beat / 2)
        for k in range(4):
            place(mix, kick(0.7), t0 + k * beat)
            place(mix, hat(0.08, 0.06, 110), t0 + (k + 0.5) * beat)
        for k in range(16):  # 16th arpeggio, triangle with a touch of echo
            note = ch[[0, 1, 2, 1][k % 4]] + 12 + (12 if (b % 2) else 0)
            n = int(SR * 0.22)
            t = np.arange(n) / SR
            place(mix, tri(hz(note), t) * np.exp(-t * 16) * 0.13, t0 + k * beat / 4)
        n = int(SR * bar)
        t = np.arange(n) / SR
        pad = sum(tri(hz(m), t) + 0.5 * tri(hz(m) * 1.006, t) for m in ch) / 6 * np.minimum(1, t / 0.5) * np.minimum(1, (bar - t) / 0.5)
        place(mix, pad * 0.2, t0)
    return finish(mix, 0.75, bpm)


def bed_dark() -> np.ndarray:
    bpm, bars = 70, 8
    beat = 60 / bpm
    bar = 4 * beat
    mix = np.zeros(int(SR * bar * bars))
    n = len(mix)
    t = np.arange(n) / SR
    trem = 0.75 + 0.25 * np.sin(2 * np.pi * t / (bar * 2))
    drone = (saw(hz(38), t) + saw(hz(38) * 1.004, t) * 0.8 + saw(hz(39), t) * 0.35) * trem  # D with a minor second leaning on it
    drone = np.convolve(drone, np.ones(30) / 30, mode="same")
    mix += drone * 0.22 + np.sin(2 * np.pi * hz(26) * t) * 0.3
    sweep = lowpass(noise(n), 250 + 700 * (0.5 + 0.5 * np.sin(2 * np.pi * t / (bar * 4))))
    mix += sweep * 0.1
    for b in range(bars):
        t0 = b * bar
        place(mix, kick(0.38, 0.45, 70, 36), t0)  # heartbeat: two soft thumps
        place(mix, kick(0.26, 0.45, 70, 36), t0 + 0.42 * beat)
        if b % 2 == 1:  # a distant bell
            m = [62, 65, 69, 74][(b // 2) % 4]
            nn = int(SR * 2.4)
            tt = np.arange(nn) / SR
            bell = (np.sin(2 * np.pi * hz(m) * tt + 2.2 * np.sin(2 * np.pi * hz(m) * 1.4 * tt) * np.exp(-tt * 3)) * np.exp(-tt * 1.6))
            place(mix, bell * 0.12, t0 + 1.5 * beat)
    return finish(mix, 1.5, bpm)


def bed_bright() -> np.ndarray:
    bpm, bars = 112, 8
    beat = 60 / bpm
    bar = 4 * beat
    chords = [[60, 64, 67], [55, 59, 62], [57, 60, 64], [53, 57, 60]]  # C G Am F
    mix = np.zeros(int(SR * bar * bars))
    for b in range(bars):
        ch = chords[b % 4]
        t0 = b * bar
        seq = [0, 1, 2, 1, 0, 1, 2, 1]
        for k in range(8):
            note = ch[seq[k]] + 12 + (12 if k == 7 else 0)
            n = int(SR * 0.3)
            t = np.arange(n) / SR
            w = (tri(hz(note), t) * 0.6 + np.sign(np.sin(2 * np.pi * hz(note) * t)) * 0.18) * np.exp(-t * 11) * np.minimum(1, t * 400)
            place(mix, w * 0.17, t0 + k * beat / 2)
        for k in range(4):
            n = int(SR * beat * 0.8)
            t = np.arange(n) / SR
            place(mix, tri(hz(ch[0] - 12), t) * np.exp(-t * 4) * 0.4, t0 + k * beat)
        place(mix, kick(0.5), t0)
        place(mix, kick(0.42), t0 + 2 * beat)
        place(mix, clap(0.28), t0 + beat)
        place(mix, clap(0.28), t0 + 3 * beat)
        for k in range(8):
            place(mix, hat(0.06, 0.05, 120), t0 + (k + 0.5) * beat / 2)
    return finish(mix, 0.5, bpm)


def bed_minimal() -> np.ndarray:
    bpm, bars = 118, 8
    beat = 60 / bpm
    bar = 4 * beat
    mix = np.zeros(int(SR * bar * bars))
    pattern = [1, 0, 0, 1, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0]  # 16 steps of a clicky groove
    for b in range(bars):
        t0 = b * bar
        for k in range(4):
            place(mix, kick(0.5, 0.2, 100, 48), t0 + k * beat)
        for k, on in enumerate(pattern):
            if on:
                place(mix, hat(0.18, 0.025, 260), t0 + k * beat / 4)
        n = int(SR * 0.12)
        t = np.arange(n) / SR
        for k in (3, 6, 11, 14):  # short filtered square stabs
            f = hz(57 if b % 4 < 2 else 60)
            stab = np.convolve(np.sign(np.sin(2 * np.pi * f * t)), np.ones(10) / 10, mode="same") * np.exp(-t * 28)
            place(mix, stab * 0.17, t0 + k * beat / 4)
        place(mix, np.sin(2 * np.pi * hz(33) * np.arange(int(SR * bar)) / SR) * 0.18 * (b % 2 == 0), t0)  # a low note every other bar
        for k in (5, 13):  # sparse high pings
            nn = int(SR * 0.4)
            tt = np.arange(nn) / SR
            place(mix, np.sin(2 * np.pi * hz(93) * tt) * np.exp(-tt * 9) * 0.07, t0 + k * beat / 4)
    return finish(mix, 0.75, bpm)


def bed_epic() -> np.ndarray:
    bpm, bars = 96, 8
    beat = 60 / bpm
    bar = 4 * beat
    chords = [[48, 51, 55], [44, 48, 51], [51, 55, 58], [46, 50, 53]]  # Cm Ab Eb Bb
    mix = np.zeros(int(SR * bar * bars))
    for b in range(bars):
        ch = chords[b % 4]
        t0 = b * bar
        n = int(SR * bar)
        t = np.arange(n) / SR
        swell = np.minimum(1, t / (bar * 0.6)) * np.minimum(1, (bar - t) / 0.4)
        strings = sum(saw(hz(m + 12), t) + saw(hz(m + 12) * 1.007, t) * 0.8 + saw(hz(m) * 0.997, t) * 0.5 for m in ch)
        strings = np.convolve(strings, np.ones(24) / 24, mode="same") / 9 * swell
        place(mix, strings * 0.42, t0)
        place(mix, np.sin(2 * np.pi * hz(ch[0] - 24) * t) * np.minimum(1, t / 0.1) * 0.4, t0)
        place(mix, kick(0.8, 0.7, 90, 34), t0)  # timpani-like hits
        place(mix, kick(0.55, 0.7, 90, 34), t0 + 2.5 * beat)
        if b % 4 == 3:  # the last bar of each phrase rolls into the next
            for k in range(8):
                place(mix, hat(0.12 + k * 0.03, 0.08, 40), t0 + 2 * beat + k * beat / 4)
    return finish(mix, 1.0, bpm)


# ───────────── more effects ─────────────

def sfx_click() -> np.ndarray:
    n = int(SR * 0.09)
    t = np.arange(n) / SR
    return np.diff(noise(n), prepend=0) * np.exp(-t * 520) * 0.9 + np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 110) * 0.6


def sfx_pop() -> np.ndarray:
    n = int(SR * 0.16)
    t = np.arange(n) / SR
    return np.sin(2 * np.pi * np.cumsum(900 * np.exp(-t * 26) + 260) / SR) * np.exp(-t * 24)


def sfx_tick() -> np.ndarray:
    n = int(SR * 0.05)
    t = np.arange(n) / SR
    return np.diff(noise(n), prepend=0) * np.exp(-t * 700) * 0.5 + np.sin(2 * np.pi * 2300 * t) * np.exp(-t * 160)


def sfx_swish() -> np.ndarray:
    n = int(SR * 0.3)
    t = np.arange(n) / SR
    cutoff = 400 + 6500 * np.sin(np.pi * t / 0.3) ** 2
    return lowpass(noise(n), cutoff) * np.sin(np.pi * t / 0.3) ** 1.5


def sfx_slide() -> np.ndarray:
    n = int(SR * 0.4)
    t = np.arange(n) / SR
    return lowpass(noise(n), 5200 * np.exp(-t * 6) + 300) * np.exp(-t * 4) + np.sin(2 * np.pi * np.cumsum(520 * np.exp(-t * 5) + 120) / SR) * np.exp(-t * 6) * 0.3


def sfx_whoosh_soft() -> np.ndarray:
    n = int(SR * 0.65)
    t = np.arange(n) / SR
    env = np.sin(np.pi * np.minimum(1, t / 0.65)) ** 2
    return lowpass(noise(n), 250 + 2400 * env) * env


def sfx_chime() -> np.ndarray:
    n = int(SR * 0.9)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for at, f in ((0.0, 1318.5), (0.11, 1975.5)):
        i = int(SR * at)
        tt = t[: n - i]
        out[i:] += (np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(2 * np.pi * 2.76 * f * tt)) * np.exp(-tt * 5.5)
    return out


def sfx_error() -> np.ndarray:
    n = int(SR * 0.38)
    t = np.arange(n) / SR
    w = np.sign(np.sin(2 * np.pi * np.cumsum(170 - 60 * t / 0.38) / SR)) * (0.7 + 0.3 * np.sign(np.sin(2 * np.pi * 34 * t)))
    return np.convolve(w, np.ones(8) / 8, mode="same") * np.exp(-t * 4.5)


def sfx_type() -> np.ndarray:
    n = int(SR * 0.03)
    t = np.arange(n) / SR
    return np.diff(noise(n), prepend=0) * np.exp(-t * 420) * 0.6 + np.sin(2 * np.pi * 220 * t) * np.exp(-t * 200) * 0.4


def sfx_glitch() -> np.ndarray:
    n = int(SR * 0.42)
    out = np.zeros(n)
    for i in range(7):
        a = int(SR * (i * 0.055 + RNG.random() * 0.02))
        ln = int(SR * (0.015 + RNG.random() * 0.04))
        seg = np.sign(np.sin(2 * np.pi * (300 + RNG.random() * 2200) * np.arange(ln) / SR)) * 0.4 + np.diff(noise(ln), prepend=0) * 0.5
        out[a:a + ln] += seg[: max(0, min(ln, n - a))]
    return np.round(out * 6) / 6  # a little bit-crush


def sfx_ding() -> np.ndarray:
    n = int(SR * 0.55)
    t = np.arange(n) / SR
    return (np.sin(2 * np.pi * 1318.5 * t) + 0.4 * np.sin(2 * np.pi * 2637 * t)) * np.exp(-t * 7) * np.minimum(1, t * 600)


def sfx_sparkle() -> np.ndarray:
    n = int(SR * 0.8)
    out = np.zeros(n)
    for i, m in enumerate((84, 88, 91, 96, 100)):
        a = int(SR * i * 0.06)
        t = np.arange(n - a) / SR
        out[a:] += np.sin(2 * np.pi * hz(m) * t) * np.exp(-t * 8) * (0.7 - i * 0.08)
    return out


def sfx_boom() -> np.ndarray:
    n = int(SR * 1.3)
    t = np.arange(n) / SR
    thump = np.sin(2 * np.pi * np.cumsum(70 * np.exp(-t * 4) + 26) / SR) * np.exp(-t * 2.8)
    tail = lowpass(noise(n), 900 * np.exp(-t * 5) + 90) * np.exp(-t * 3.2)
    return thump + tail * 0.7


BEDS = {"bed_chill": bed_chill, "bed_drive": bed_drive, "bed_dark": bed_dark, "bed_bright": bed_bright, "bed_minimal": bed_minimal, "bed_epic": bed_epic}
SFX = {"sfx_click": (sfx_click, 0.8), "sfx_pop": (sfx_pop, 0.8), "sfx_tick": (sfx_tick, 0.7), "sfx_swish": (sfx_swish, 0.7), "sfx_slide": (sfx_slide, 0.7),
       "sfx_whoosh_soft": (sfx_whoosh_soft, 0.7), "sfx_chime": (sfx_chime, 0.7), "sfx_error": (sfx_error, 0.7), "sfx_type": (sfx_type, 0.7), "sfx_glitch": (sfx_glitch, 0.7),
       "sfx_ding": (sfx_ding, 0.7), "sfx_sparkle": (sfx_sparkle, 0.65), "sfx_boom": (sfx_boom, 0.95)}


def to_mp3(wav_name: str, mp3_name: str) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from services.voice import get_ffmpeg_bin

    subprocess.run([get_ffmpeg_bin(), "-y", "-i", str(OUT / wav_name), "-c:a", "libmp3lame", "-b:a", "112k", str(OUT / mp3_name)], check=True, capture_output=True)
    (OUT / wav_name).unlink()
    print(f"  -> {mp3_name} ({(OUT / mp3_name).stat().st_size // 1024} KB)")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    write("motion_bed.wav", bed(), 0.7)
    write("sfx_riser.wav", riser(), 0.8)
    write("sfx_hit.wav", hit(), 0.9)
    for name, fn in BEDS.items():
        write(f"{name}.wav", fn(), 0.7)
        to_mp3(f"{name}.wav", f"{name}.mp3")
    for name, (fn, peak) in SFX.items():
        write(f"{name}.wav", fn(), peak)
