import React from 'react';
import { interpolate, random, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { EASE_IO, EASE_OUT, Kicker, SafeBox, Words, clamp, useTheme } from './primitives';
import { MONO, SANS } from './fonts';
import { MotionScene, uiAct } from './types';

/**
 * Building blocks of the `ui` presets: drawn interfaces (settings panels, graphs, controls) that the pointer uses with a purpose.
 * Generic look on purpose: the channel palette, no logos and no copy of any vendor's interface.
 * Every preset is data-driven (scene.items rows "a|b|c", value, accentText, leftValue, rightValue, code) and animates ONE change between uiAct().grab and uiAct().done;
 * the element the pointer holds or presses carries data-cursor="target", so the pointer measures it live.
 */

export const INK = '#E8EEF8';
export const MUTED = 'rgba(232,238,248,0.52)';
export const GOOD = '#35E08A';
export const BAD = '#FF5D6C';
export const WARN = '#FFD166';
export const WIN_W = 940;

export const parts = (row: string): string[] => row.split('|').map((x) => x.trim());
export const rows = (scene: MotionScene): string[][] => (scene.items ?? []).map(parts);
export const num = (text: string | undefined, fallback = 0): number => {
  const m = (text ?? '').replace(/,/g, '').match(/-?\d+(?:\.\d+)?/);
  return m ? parseFloat(m[0]) : fallback;
};
export const mix = (a: number, b: number, t: number) => a + (b - a) * t;
/** 0 -> 1 between two frames, eased. */
export const ease = (frame: number, from: number, to: number) => interpolate(frame, [from, to], [0, 1], { ...clamp, easing: EASE_IO });

/** The progress of the scene's one action: g = 0 before the grab, 1 once done; `grab` / `done` are frames. */
export const useAct = (scene: MotionScene) => {
  const frame = useCurrentFrame();
  const { grab, done } = uiAct(scene);
  return { frame, grab, done, g: ease(frame, grab, done), pressed: frame >= grab && frame < done + 4 };
};

/** Headline above the interface, same look as the other scenes. */
export const UiShell: React.FC<{ scene: MotionScene; children: React.ReactNode; gap?: number }> = ({ scene, children, gap = 34 }) => (
  <SafeBox gap={gap}>
    <Kicker text={scene.kicker} />
    <Words text={scene.text} size={74} />
    {children}
  </SafeBox>
);

/** Glass window with a title bar; it rises in with a soft spring. */
export const Win: React.FC<{ title: string; children: React.ReactNode; width?: number; padding?: string; mono?: boolean; style?: React.CSSProperties }> = ({ title, children, width = WIN_W, padding = '26px 34px 34px', mono, style }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme } = useTheme();
  const s = spring({ frame: frame - 4, fps, config: { damping: 18, stiffness: 120 } });
  return (
    <div style={{ width, borderRadius: 34, padding, textAlign: 'left', background: 'rgba(10,20,40,0.82)', border: `1px solid ${theme.accent}33`, boxShadow: `0 30px 90px rgba(0,0,0,0.5), 0 0 0 1px ${theme.accent}18`, opacity: Math.min(1, s * 1.5), transform: `translateY(${(1 - s) * 50}px) scale(${0.96 + 0.04 * s})`, fontFamily: mono ? MONO : SANS, color: INK, ...style }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        {[theme.accent2 ?? '#007AFF', theme.accent, 'rgba(255,255,255,0.45)'].map((c, i) => <div key={i} style={{ width: 16, height: 16, borderRadius: 8, background: c }} />)}
        <span style={{ marginLeft: 16, fontFamily: MONO, fontSize: 24, color: MUTED, letterSpacing: 1 }}>{title}</span>
      </div>
      {children}
    </div>
  );
};

/** A settings row: label on the left, anything on the right; `active` lights it in the accent colour. */
export const Row: React.FC<{ label: React.ReactNode; right?: React.ReactNode; active?: number; height?: number; target?: boolean; style?: React.CSSProperties }> = ({ label, right, active = 0, height = 84, target, style }) => {
  const { theme } = useTheme();
  return (
    <div data-cursor={target ? 'target' : undefined} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 20, minHeight: height, padding: '0 26px', borderRadius: 20, background: `rgba(255,255,255,${0.05 + 0.03 * active})`, border: `2px solid ${theme.accent}${Math.round(active * 170).toString(16).padStart(2, '0')}`, boxShadow: active > 0.01 ? `0 0 ${active * 34}px ${theme.accent}44` : 'none', fontSize: 34, fontWeight: 600, ...style }}>
      <span style={{ whiteSpace: 'nowrap' }}>{label}</span>
      <span style={{ color: MUTED, fontWeight: 500, display: 'flex', alignItems: 'center', gap: 14 }}>{right}</span>
    </div>
  );
};

/** Animated switch: on = 0..1. */
export const Switch: React.FC<{ on: number; target?: boolean }> = ({ on, target }) => {
  const { theme } = useTheme();
  return (
    <div data-cursor={target ? 'target' : undefined} style={{ width: 96, height: 54, borderRadius: 27, background: on > 0.5 ? theme.accent : 'rgba(255,255,255,0.2)', position: 'relative', transition: 'none', boxShadow: on > 0.5 ? `0 0 24px ${theme.accent}77` : 'none' }}>
      <div style={{ position: 'absolute', top: 5, left: 5 + on * 42, width: 44, height: 44, borderRadius: 22, background: '#fff', boxShadow: '0 3px 8px rgba(0,0,0,0.4)' }} />
    </div>
  );
};

/** Slider with a round knob; v = 0..1. The knob is the pointer's target when `target` is set. */
export const Slider: React.FC<{ v: number; width?: number; target?: boolean }> = ({ v, width = 470, target }) => {
  const { theme } = useTheme();
  return (
    <div style={{ position: 'relative', width, height: 44 }}>
      <div style={{ position: 'absolute', left: 0, right: 0, top: 17, height: 10, borderRadius: 5, background: 'rgba(255,255,255,0.16)' }} />
      <div style={{ position: 'absolute', left: 0, top: 17, width: v * width, height: 10, borderRadius: 5, background: `linear-gradient(90deg, ${theme.accent2 ?? '#007AFF'}, ${theme.accent})` }} />
      <div data-cursor={target ? 'target' : undefined} style={{ position: 'absolute', left: v * width - 22, top: 0, width: 44, height: 44, borderRadius: 22, background: '#fff', border: `5px solid ${theme.accent}`, boxShadow: `0 0 20px ${theme.accent}99, 0 4px 10px rgba(0,0,0,0.45)` }} />
    </div>
  );
};

/** Signal-bars glyph (1-4 bars lit). */
export const Bars: React.FC<{ level: number; color?: string }> = ({ level, color }) => {
  const { theme } = useTheme();
  const c = color ?? theme.accent;
  return (
    <svg width={46} height={38} viewBox="0 0 46 38">
      {[0, 1, 2, 3].map((i) => <rect key={i} x={i * 12} y={30 - i * 9} width={8} height={8 + i * 9} rx={2} fill={c} opacity={level > i + 0.01 ? 1 : 0.22} />)}
    </svg>
  );
};

/** A small pill/chip. */
export const Chip: React.FC<{ children: React.ReactNode; color?: string; bg?: string; size?: number; target?: boolean; style?: React.CSSProperties }> = ({ children, color = '#05070C', bg, size = 30, target, style }) => {
  const { theme } = useTheme();
  return (
    <div data-cursor={target ? 'target' : undefined} style={{ display: 'inline-flex', alignItems: 'center', padding: '10px 22px', borderRadius: 16, fontSize: size, fontWeight: 800, color, background: bg ?? theme.accent, whiteSpace: 'nowrap', ...style }}>
      {children}
    </div>
  );
};

/** Line graph (SVG) from a deterministic noise series; `calm` 0..1 smooths it out. */
export const Graph: React.FC<{ seed: string; width: number; height: number; level: number; calm?: number; points?: number; reveal?: number; spikeAt?: number; spike?: number; fill?: boolean }> = ({ seed, width, height, level, calm = 0, points = 60, reveal = 1, spikeAt, spike = 0, fill = true }) => {
  const { theme } = useTheme();
  const vals: number[] = [];
  for (let i = 0; i < points; i++) {
    const n = (random(`${seed}${i}`) - 0.5) * 2;
    let v = level + n * 0.22 * (1 - calm * 0.92);
    if (spikeAt !== undefined && Math.abs(i - spikeAt) <= 1) v = level + spike * (i === spikeAt ? 1 : 0.45);
    vals.push(Math.max(0.02, Math.min(1, v)));
  }
  const shown = Math.max(2, Math.round(points * reveal));
  const pts = vals.slice(0, shown).map((v, i) => `${(i / (points - 1)) * width},${height - v * height}`);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} style={{ overflow: 'visible' }}>
      {[0.25, 0.5, 0.75].map((y) => <line key={y} x1={0} x2={width} y1={height * y} y2={height * y} stroke="rgba(255,255,255,0.08)" strokeWidth={2} />)}
      {fill && <polygon points={`0,${height} ${pts.join(' ')} ${(shown - 1) / (points - 1) * width},${height}`} fill={`${theme.accent}22`} />}
      <polyline points={pts.join(' ')} fill="none" stroke={theme.accent} strokeWidth={5} strokeLinejoin="round" strokeLinecap="round" style={{ filter: `drop-shadow(0 0 8px ${theme.accent}99)` }} />
    </svg>
  );
};

/** Little line icons used by several presets. */
export const Glyph: React.FC<{ name: 'mic' | 'camera' | 'pin' | 'check' | 'cross' | 'file' | 'folder' | 'battery'; color?: string; size?: number }> = ({ name, color = INK, size = 40 }) => {
  const p = { fill: 'none', stroke: color, strokeWidth: 3.2, strokeLinecap: 'round', strokeLinejoin: 'round' } as const;
  const body = {
    mic: <><rect x="17" y="6" width="14" height="24" rx="7" {...p} /><path d="M10 24a14 14 0 0 0 28 0M24 38v6" {...p} /></>,
    camera: <><rect x="5" y="14" width="38" height="26" rx="6" {...p} /><circle cx="24" cy="27" r="7" {...p} /><path d="M17 14l3-6h8l3 6" {...p} /></>,
    pin: <><path d="M24 44s-14-14-14-24a14 14 0 0 1 28 0c0 10-14 24-14 24z" {...p} /><circle cx="24" cy="20" r="5" {...p} /></>,
    check: <path d="M8 26l11 11L40 12" {...p} strokeWidth={5} />,
    cross: <path d="M10 10l28 28M38 10L10 38" {...p} strokeWidth={5} />,
    file: <><path d="M10 4h20l10 10v30H10z" {...p} /><path d="M30 4v10h10" {...p} /></>,
    folder: <path d="M4 12h14l4 6h22v24H4z" {...p} />,
    battery: <><rect x="4" y="12" width="36" height="24" rx="6" {...p} /><path d="M44 20v8" {...p} /></>,
  }[name];
  return <svg width={size} height={size} viewBox="0 0 48 48">{body}</svg>;
};

export { EASE_OUT };
