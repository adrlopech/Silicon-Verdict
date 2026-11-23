import React from 'react';
import { interpolate, random, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { Reveal } from './anim';
import { clamp } from './primitives';

/** One word, revealed in the scene's mode. Every effect ends in an untouched, un-transformed word so settled text never shimmers. `char0` = how many characters came before it in the line (for typing). */
export const RevealWord: React.FC<{ word: string; mode: Reveal; index: number; delay: number; stagger: number; size: number; accent: string; char0: number; total: number }> = ({ word, mode, index, delay, stagger, size, accent, char0, total }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const f = frame - delay - index * stagger;
  const chars = Array.from(word);
  const wrap: React.CSSProperties = { display: 'inline-block', whiteSpace: 'nowrap', position: 'relative' };

  if (mode === 'type') {
    const per = Math.min(2.2, 34 / Math.max(1, total));
    const start = delay + 2;
    const last = Math.floor((frame - start) / per) + 5 - char0; // index (within this word) of the last typed character
    const typing = frame - start < total * per + 8;
    return (
      <span style={wrap}>
        {chars.map((c, k) => {
          const shown = k <= last;
          const caret = typing && k === last && Math.floor(frame / 5) % 2 === 0;
          return (
            <span key={k} style={{ position: 'relative', opacity: shown ? 1 : 0 }}>
              {c}
              {caret && <span style={{ position: 'absolute', right: -size * 0.1, top: size * 0.08, width: size * 0.07, height: size * 0.82, background: accent, boxShadow: `0 0 12px ${accent}` }} />}
            </span>
          );
        })}
      </span>
    );
  }

  if (mode === 'scramble') {
    const GL = 'abcdefghjknopqrstuvxyzABCDEFGHJKLNOPQRSTUVXYZ0123456789#%&';
    return (
      <span style={wrap}>
        {chars.map((c, k) => {
          const at = index * stagger + k * 1.7 + 6;
          const done = f >= at + 10 - index * stagger || /[^A-Za-z0-9]/.test(c);
          const g = GL[Math.floor(random(`${frame}-${index}-${k}`) * GL.length)];
          return (
            <span key={k} style={{ color: done ? undefined : accent, opacity: f < 0 ? 0 : 1 }}>
              {done ? c : g}
            </span>
          );
        })}
      </span>
    );
  }

  if (mode === 'drop' || mode === 'wave') {
    return (
      <span style={wrap}>
        {chars.map((c, k) => {
          const g = f - k * (mode === 'drop' ? 1.8 : 1.3);
          const p = spring({ frame: g, fps, config: mode === 'drop' ? { damping: 9, stiffness: 190, mass: 0.7 } : { damping: 14, stiffness: 170, mass: 0.6 } });
          const done = g > 40;
          const y = mode === 'drop' ? -(1 - p) * size * 1.5 : (1 - p) * size * 0.55;
          return (
            <span key={k} style={{ display: 'inline-block', opacity: Math.min(1, Math.max(0, g + 2) * 0.5), transform: done ? undefined : `translateY(${y}px)` }}>
              {c}
            </span>
          );
        })}
      </span>
    );
  }

  if (mode === 'rise') {
    // each letter floats up a short way while fading in: calm and readable
    return (
      <span style={wrap}>
        {chars.map((c, k) => {
          const g = f - k * 1.1;
          const p = spring({ frame: g, fps, config: { damping: 18, stiffness: 120, mass: 0.8 } });
          const done = g > 40 || p >= 0.999;
          return <span key={k} style={{ display: 'inline-block', opacity: done ? undefined : Math.min(1, Math.max(0, p * 1.4)), transform: done ? undefined : `translateY(${(1 - p) * size * 0.45}px)` }}>{c}</span>;
        })}
      </span>
    );
  }

  if (mode === 'focus') {
    // the word starts wide and out of focus and tightens into place
    const p = spring({ frame: f, fps, config: { damping: 22, stiffness: 100, mass: 1 } });
    if (p >= 0.999) return <span style={{ display: 'inline-block' }}>{word}</span>;
    return <span style={{ display: 'inline-block', opacity: Math.min(1, p * 1.6), letterSpacing: `${(1 - p) * 0.35}em`, filter: `blur(${(1 - p) * 18}px)` }}>{word}</span>;
  }

  if (mode === 'flip') {
    // the word flips up from the baseline like a split-flap board
    const p = spring({ frame: f, fps, config: { damping: 15, stiffness: 150, mass: 0.8 } });
    if (p >= 0.999) return <span style={{ display: 'inline-block' }}>{word}</span>;
    return <span style={{ display: 'inline-block', opacity: Math.min(1, p * 2), transform: `perspective(700px) rotateX(${(1 - p) * -88}deg)`, transformOrigin: '50% 100%' }}>{word}</span>;
  }

  if (mode === 'mask') {
    const p = spring({ frame: f, fps, config: { damping: 18, stiffness: 140, mass: 0.8 } });
    return (
      <span style={{ ...wrap, overflow: p >= 0.999 ? 'visible' : 'hidden', paddingBottom: '0.14em', marginBottom: '-0.14em', paddingTop: '0.06em', marginTop: '-0.06em' }}>
        <span style={{ display: 'inline-block', transform: p >= 0.999 ? undefined : `translateY(${(1 - p) * 115}%)` }}>{word}</span>
      </span>
    );
  }

  if (mode === 'blur') {
    const p = spring({ frame: f, fps, config: { damping: 20, stiffness: 110, mass: 1 } });
    const done = p >= 0.999;
    return <span style={{ display: 'inline-block', opacity: Math.min(1, p * 1.5), transform: done ? undefined : `scale(${1 + (1 - p) * 0.9})`, filter: done ? undefined : `blur(${(1 - p) * 26}px)` }}>{word}</span>;
  }

  if (mode === 'draw') {
    const wipe = interpolate(f, [0, 15], [0, 1], clamp);
    const fill = interpolate(f, [9, 24], [0, 1], clamp);
    if (fill >= 1) return <span style={{ display: 'inline-block' }}>{word}</span>;
    return (
      <span style={wrap}>
        <span style={{ opacity: fill, display: 'inline-block' }}>{word}</span>
        <span aria-hidden style={{ position: 'absolute', left: 0, top: 0, color: 'transparent', WebkitTextStroke: `${Math.max(2, size * 0.03)}px ${accent}`, clipPath: `inset(-10% ${(1 - wipe) * 100}% -10% 0)`, opacity: 1 - fill * 0.9, filter: `drop-shadow(0 0 8px ${accent})` }}>{word}</span>
      </span>
    );
  }

  if (mode === 'slice') {
    const p = spring({ frame: f, fps, config: { damping: 16, stiffness: 150, mass: 0.8 } });
    if (p >= 0.999) return <span style={{ display: 'inline-block' }}>{word}</span>;
    return (
      <span style={wrap}>
        <span style={{ display: 'inline-block', clipPath: 'inset(0 0 50% 0)', transform: `translateX(${-(1 - p) * 420}px)`, opacity: Math.min(1, p * 2) }}>{word}</span>
        <span aria-hidden style={{ position: 'absolute', left: 0, top: 0, clipPath: 'inset(50% 0 0 0)', transform: `translateX(${(1 - p) * 420}px)`, opacity: Math.min(1, p * 2) }}>{word}</span>
      </span>
    );
  }

  return <span style={{ display: 'inline-block' }}>{word}</span>;
};
