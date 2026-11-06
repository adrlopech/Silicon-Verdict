import React, { createContext, useContext } from 'react';
import { AbsoluteFill, Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { MONO, SANS, SERIF } from './fonts';
import { BRAND_BLUE, MotionTheme, SAFE_BOTTOM, SAFE_TOP } from './types';

export const ThemeCtx = createContext<{ theme: MotionTheme; light: boolean }>({ theme: { accent: '#00F0FF', background: '#05070C', text: '#FFF' }, light: false });
export const useTheme = () => useContext(ThemeCtx);

/** Largest font size (<= size) at which `chars` characters still fit in `maxWidth` px (avg glyph width = factor * size). */
export const fit = (size: number, chars: number, maxWidth = 920, factor = 0.6, min = 40) => Math.max(min, Math.min(size, Math.floor(maxWidth / (Math.max(1, chars) * factor))));

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1); // expo-out style: fast start, long soft landing
export const EASE_IO = Easing.bezier(0.65, 0, 0.35, 1);
export const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** Ember glow + vignette + a thin light line that sweeps across, all slow and continuous. */
export const Background: React.FC<{ light: boolean; background: string; accent: string }> = ({ light, background, accent }) => {
  const frame = useCurrentFrame();
  const drift = Math.sin(frame / 55) * 70;
  const sweep = interpolate(frame % 120, [0, 120], [-20, 120]);
  const base = light ? '#EAF1F8' : background;
  return (
    <AbsoluteFill style={{ background: base }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 80% 42% at ${50 + drift / 14}% 66%, ${BRAND_BLUE}${light ? '30' : '55'} 0%, ${accent}${light ? '14' : '1F'} 45%, transparent 72%)` }} />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 70% 30% at 50% 0%, ${BRAND_BLUE}${light ? '14' : '26'} 0%, transparent 75%)` }} />
      {!light && (
        <div style={{ position: 'absolute', top: 1180, left: `${sweep}%`, width: 520, height: 3, background: `linear-gradient(90deg, transparent, ${accent}, transparent)`, opacity: 0.35, filter: 'blur(1.5px)' }} />
      )}
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 75% 70% at 50% 50%, transparent 52%, ${light ? 'rgba(40,70,110,0.20)' : 'rgba(0,0,0,0.72)'} 100%)` }} />
    </AbsoluteFill>
  );
};

/** Tiny mono HUD in the corners (inside the safe zone): scene counter + running timecode. */
export const Hud: React.FC<{ index: number; total: number; label: string }> = ({ index, total, label }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const s = Math.floor(frame / fps);
  const tc = `00:${String(s).padStart(2, '0')}:${String(frame % fps).padStart(2, '0')}`;
  const color = light ? 'rgba(10,18,32,0.5)' : 'rgba(255,255,255,0.42)';
  const row: React.CSSProperties = { position: 'absolute', top: SAFE_TOP + 16, fontFamily: MONO, fontSize: 24, letterSpacing: 3, color, textTransform: 'uppercase' };
  return (
    <>
      <div style={{ ...row, left: 64 }}>
        <span style={{ color: theme.accent }}>●</span> SC {String(index + 1).padStart(2, '0')}/{String(total).padStart(2, '0')} · {label.length > 24 ? label.slice(0, 23) + '…' : label}
      </div>
      <div style={{ ...row, right: 64 }}>{tc}</div>
    </>
  );
};

/** Content box that respects the Shorts/TikTok safe zones and centres its children. */
export const SafeBox: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 28 }) => (
  <div style={{ position: 'absolute', left: 64, right: 64, top: SAFE_TOP + 130, bottom: SAFE_BOTTOM, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap, textAlign: 'center' }}>
    {children}
  </div>
);

export const Kicker: React.FC<{ text?: string; delay?: number }> = ({ text, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { theme, light } = useTheme();
  if (!text) return null;
  const p = interpolate(frame - delay, [0, 18], [0, 1], { ...clamp, easing: EASE_OUT });
  return (
    <div style={{ maxWidth: 940, fontFamily: MONO, fontSize: fit(30, text.length, 920, 0.95, 20), letterSpacing: 9, textTransform: 'uppercase', color: light ? 'rgba(10,18,32,0.6)' : 'rgba(255,255,255,0.55)', opacity: p, transform: `translateY(${(1 - p) * 14}px)` }}>
      <span style={{ color: theme.accent }}>/ </span>
      {text}
    </div>
  );
};

/** Word-by-word reveal: each word rises, un-blurs and fades in with a soft spring (no linear or abrupt motion). */
export const Words: React.FC<{ text: string; size: number; delay?: number; stagger?: number; weight?: number; color?: string; upper?: boolean }> = ({ text, size, delay = 0, stagger = 4, weight = 900, color, upper }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const words = (upper ? text.toUpperCase() : text).split(/\s+/).filter(Boolean);
  const longest = Math.max(1, ...words.map((w) => w.length));
  size = fit(size, longest, 900, upper ? 0.74 : 0.64, 36); // a long word must never overflow the 1080 px frame
  const lines = Math.ceil(words.join(' ').length / Math.max(6, Math.floor(900 / (size * 0.5))));
  if (lines > 3) size = Math.max(36, Math.floor(size * 0.82)); // very long lines shrink instead of growing taller than the safe area
  return (
    <div data-cursor="text" style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', columnGap: size * 0.28, rowGap: size * 0.06, fontFamily: SANS, fontWeight: weight, fontSize: size, lineHeight: 1.04, letterSpacing: -size * 0.025, color: color ?? (light ? '#0A1220' : theme.text) }}>
      {words.map((w, i) => {
        // bouncy pop: overshoots its size, tilts alternately and settles; the opacity/blur use the clamped value so nothing flickers
        const raw = spring({ frame: frame - delay - i * stagger, fps, config: { damping: 11, stiffness: 150, mass: 0.8 } });
        const s = Math.min(1, raw);
        return (
          <span key={i} style={{ display: 'inline-block', opacity: Math.min(1, s * 1.6), transform: `translateY(${(1 - raw) * size * 0.6}px) scale(${0.55 + 0.45 * raw}) rotate(${(1 - raw) * (i % 2 ? 7 : -7)}deg)`, filter: `blur(${(1 - s) * 12}px)` }}>
            {w}
          </span>
        );
      })}
    </div>
  );
};

/** The accent word: italic serif, accent colour, soft glow, drawn in from below. */
export const Accent: React.FC<{ text?: string; size: number; delay?: number }> = ({ text, size, delay = 0 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  if (!text) return null;
  size = fit(size, text.length, 900, 0.5, 44);
  const raw = spring({ frame: frame - delay, fps, config: { damping: 10, stiffness: 130, mass: 0.9 } });
  const s = Math.min(1, raw);
  return (
    <div data-cursor="accent" style={{ maxWidth: 940, fontFamily: SERIF, fontStyle: 'italic', fontWeight: 400, fontSize: size, lineHeight: 1.0, color: theme.accent, opacity: s, transform: `translateY(${(1 - raw) * size * 0.5}px) scale(${0.6 + 0.4 * raw}) rotate(${(1 - raw) * -5}deg)`, filter: `blur(${(1 - s) * 10}px)`, textShadow: light ? 'none' : `0 0 ${size * 0.35}px ${theme.accent}66` }}>
      {text}
    </div>
  );
};

/** Deterministic particles bursting from a point (used by the outro). */
export const Burst: React.FC<{ delay: number; color: string; count?: number; cy: number }> = ({ delay, color, count = 46, cy }) => {
  const frame = useCurrentFrame() - delay;
  if (frame < 0) return null;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      {Array.from({ length: count }).map((_, i) => {
        const angle = random(`a${i}`) * Math.PI * 2;
        const speed = 160 + random(`s${i}`) * 520;
        const t = interpolate(frame, [0, 60], [0, 1], { ...clamp, easing: EASE_OUT });
        const x = 540 + Math.cos(angle) * speed * t;
        const y = cy + Math.sin(angle) * speed * t + t * t * 60;
        const op = interpolate(frame, [0, 6, 55], [0, 1, 0], clamp);
        const size = 4 + random(`z${i}`) * 9;
        const c = i % 3 === 0 ? BRAND_BLUE : color;
        return <div key={i} style={{ position: 'absolute', left: x, top: y, width: size, height: size, borderRadius: '50%', background: c, opacity: op, boxShadow: `0 0 ${size * 2}px ${c}` }} />;
      })}
    </AbsoluteFill>
  );
};
