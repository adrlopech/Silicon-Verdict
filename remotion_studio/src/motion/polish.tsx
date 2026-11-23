import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { clamp, EASE_OUT, fit, useTheme } from './primitives';
import { useLook } from './looks';
import { MONO, SANS } from './fonts';
import { MotionScene } from './types';

/** Finishing touches of the Nov 2026 pass: drawn product icons, glass-style cards, the price card of a tier scene, the A/B vote cards of the outro, film grain + vignette and the breath before a data reveal. */

/* ───────────── drawn product icons (no photos, no brands) ───────────── */

export type IconKind = 'cpu' | 'gpu' | 'ram' | 'ssd' | 'chip';

/** Which drawn icon fits a product name ("Ryzen 7 9800X3D" -> cpu, "RTX 5070" -> gpu, "DDR5-6000" -> ram, "NVMe" -> ssd). */
export const iconKindFor = (text: string): IconKind => {
  const t = text.toLowerCase();
  if (/\b(rtx|gtx|radeon|arc|geforce|gpu|graphics|rx ?\d|\d{4} ?(ti|super|xt))\b/.test(t) || /\brx ?\d{4}/.test(t)) return 'gpu';
  if (/\b(ddr\d?|ram|dimm|memory)\b/.test(t)) return 'ram';
  if (/\b(ssd|nvme|m\.2|hdd|drive|storage|sata)\b/.test(t)) return 'ssd';
  if (/\b(ryzen|core|i[3579]|intel|amd|cpu|processor|threadripper|xeon|x3d)\b/.test(t) || /\b\d{4,5}x3d\b/.test(t)) return 'cpu';
  return 'chip';
};

export const ProductIcon: React.FC<{ kind: IconKind; size: number; color: string; fill?: string }> = ({ kind, size, color, fill = 'none' }) => {
  const s = { stroke: color, strokeWidth: 3, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' };
  let body: React.ReactNode;
  if (kind === 'gpu') {
    body = (
      <>
        <rect x="4" y="16" width="56" height="30" rx="4" {...s} fill={fill} />
        <circle cx="24" cy="31" r="9" {...s} />
        <circle cx="44" cy="31" r="9" {...s} />
        <path d="M24 22v18M15 31h18M44 22v18M35 31h18" {...s} strokeWidth={1.8} />
        <path d="M10 46v6M18 46v6M26 46v6" {...s} />
      </>
    );
  } else if (kind === 'ram') {
    body = (
      <>
        <rect x="3" y="20" width="58" height="24" rx="3" {...s} fill={fill} />
        <rect x="10" y="26" width="9" height="12" rx="1.5" {...s} strokeWidth={2} />
        <rect x="24" y="26" width="9" height="12" rx="1.5" {...s} strokeWidth={2} />
        <rect x="38" y="26" width="9" height="12" rx="1.5" {...s} strokeWidth={2} />
        <path d="M9 44v6M17 44v6M25 44v6M33 44v6M41 44v6M49 44v6M57 44v6" {...s} strokeWidth={2.4} />
      </>
    );
  } else if (kind === 'ssd') {
    body = (
      <>
        <rect x="6" y="18" width="52" height="28" rx="5" {...s} fill={fill} />
        <rect x="14" y="26" width="16" height="12" rx="2" {...s} strokeWidth={2} />
        <path d="M38 27h12M38 32h12M38 37h8" {...s} strokeWidth={2.4} />
        <circle cx="52" cy="22.5" r="1.6" fill={color} />
      </>
    );
  } else {
    // cpu (a square package with pins) and the generic chip share the same drawing; the cpu gets the heat-spreader inner square
    body = (
      <>
        <rect x="16" y="16" width="32" height="32" rx="5" {...s} fill={fill} />
        <rect x="24" y="24" width="16" height="16" rx="2.5" {...s} strokeWidth={2} />
        <path d="M24 6v10M32 6v10M40 6v10M24 48v10M32 48v10M40 48v10M6 24h10M6 32h10M6 40h10M48 24h10M48 32h10M48 40h10" {...s} strokeWidth={2.6} />
        {kind === 'chip' && <path d="M29 32h6M32 29v6" {...s} strokeWidth={2.2} />}
      </>
    );
  }
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" style={{ display: 'block', overflow: 'visible' }}>
      {body}
    </svg>
  );
};

/* ───────────── glass-style card ───────────── */

/** A card that reads as frosted glass without a blur filter (which is slow to render): translucent gradient, a bright top edge and a soft inner sheen. */
export const glass = (accent: string, light: boolean, radius = 28): React.CSSProperties => ({
  borderRadius: radius,
  background: light
    ? 'linear-gradient(160deg, rgba(255,255,255,0.92), rgba(235,242,255,0.78))'
    : `linear-gradient(160deg, rgba(120,160,255,0.16), rgba(20,40,90,0.34) 55%, rgba(8,16,40,0.5))`,
  border: `1px solid ${light ? 'rgba(10,18,32,0.12)' : 'rgba(190,215,255,0.22)'}`,
  boxShadow: light
    ? '0 18px 50px rgba(10,18,32,0.14)'
    : `inset 0 1px 0 rgba(255,255,255,0.28), inset 0 -24px 40px rgba(0,0,0,0.18), 0 22px 60px rgba(0,0,0,0.38), 0 0 40px ${accent}1f`,
});

/* ───────────── price / product card of a tier scene ───────────── */

/** Under the board: the chip that just landed (drawn icon, name, its tier) and, when the scene carries a price (`value` + `unit`), a counter that runs up to it. */
export const ProductCard: React.FC<{ scene: MotionScene; label: string; tier: string; tierColor: string; delay: number }> = ({ scene, label, tier, tierColor, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const enter = spring({ frame: frame - delay, fps, config: { damping: 15, stiffness: 120 } });
  const run = interpolate(frame, [delay + 6, delay + 40], [0, 1], { ...clamp, easing: EASE_OUT });
  const hasValue = typeof scene.value === 'number' && scene.value > 0;
  const shown = hasValue ? Math.round((scene.value as number) * run) : 0;
  const ink = light ? '#0A1220' : theme.text;
  const kind = iconKindFor(`${label} ${scene.text} ${scene.accentText ?? ''}`);
  return (
    <div style={{ ...glass(theme.accent, light, 26), width: 888, boxSizing: 'border-box', display: 'flex', alignItems: 'center', gap: 22, padding: '16px 28px', opacity: Math.min(1, enter * 1.3), transform: `translateY(${(1 - Math.min(1, enter)) * 30}px)` }}>
      <div style={{ flex: '0 0 auto', width: 78, height: 78, borderRadius: 20, background: `${tierColor}26`, border: `1px solid ${tierColor}66`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <ProductIcon kind={kind} size={52} color={tierColor} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: MONO, fontSize: 22, letterSpacing: 4, textTransform: 'uppercase', color: light ? 'rgba(10,18,32,0.55)' : 'rgba(255,255,255,0.55)' }}>just placed</div>
        <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: fit(44, label.length, 430, 0.58, 28), color: ink, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{label}</div>
      </div>
      <div style={{ flex: '0 0 auto', textAlign: 'right' }}>
        {hasValue ? (
          <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 60, lineHeight: 1, color: theme.accent, textShadow: light ? 'none' : `0 0 28px ${theme.accent}66`, fontVariantNumeric: 'tabular-nums' }}>
            {shown.toLocaleString('en-US')}
            <span style={{ fontSize: 34, marginLeft: 6, opacity: 0.85 }}>{scene.unit ?? ''}</span>
          </div>
        ) : (
          <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: 60, lineHeight: 1, color: tierColor }}>{tier}</div>
        )}
        {hasValue && <div style={{ fontFamily: MONO, fontSize: 22, letterSpacing: 3, color: tierColor, marginTop: 4 }}>{tier} TIER</div>}
      </div>
    </div>
  );
};

/* ───────────── A / B vote cards (outro) ───────────── */

/** "Which would you buy, A or B?" -> ['A', 'B'] (null when the closing line does not ask that). Only what the video says: no invented poll results. */
export const voteOptions = (scene: MotionScene): [string, string] | null => {
  const fromItems = scene.items && scene.items.length === 2 ? ([scene.items[0], scene.items[1]] as [string, string]) : null;
  if (fromItems) return fromItems;
  const m = (scene.narration ?? '').match(/([^,.?!:;]{2,28}?) or ([^,.?!:;]{2,28})\?\s*$/i);
  if (!m) return null;
  const clean = (x: string) => x.trim().replace(/^(the|a|an)\s+/i, '');
  const a = clean(m[1]);
  const b = clean(m[2]);
  if (!a || !b || a.split(/\s+/).length > 3 || b.split(/\s+/).length > 3) return null;
  return [a, b];
};

export const VoteCards: React.FC<{ a: string; b: string; delay: number }> = ({ a, b, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const look = useLook();
  const ink = light ? '#0A1220' : theme.text;
  const card = (label: string, letter: string, k: number) => {
    const s = spring({ frame: frame - delay - k * 7, fps, config: { damping: 12, stiffness: 140 } });
    const pulse = 0.5 + 0.5 * Math.sin((frame - delay) / 9 + k * Math.PI);
    return (
      <div key={letter} style={{ ...glass(theme.accent, light, 30), flex: 1, boxSizing: 'border-box', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, padding: '26px 18px 24px', opacity: Math.min(1, s * 1.4), transform: `translateY(${(1 - Math.min(1, s)) * 50}px) scale(${0.92 + 0.08 * Math.min(1, s)})`, boxShadow: `${glass(theme.accent, light).boxShadow}, 0 0 ${24 + pulse * 26}px ${theme.accent}${light ? '22' : '40'}` }}>
        <div style={{ width: 74, height: 74, borderRadius: 999, background: theme.accent, color: '#05070C', fontFamily: look.sans, fontWeight: 900, fontSize: 46, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>{letter}</div>
        <div style={{ fontFamily: look.sans, fontWeight: 800, fontSize: fit(46, label.length, 360, 0.58, 28), color: ink, textAlign: 'center', lineHeight: 1.05, maxWidth: 380 }}>{label}</div>
      </div>
    );
  };
  const tag = interpolate(frame, [delay + 22, delay + 34], [0, 1], clamp);
  return (
    <div style={{ width: 888 }}>
      <div style={{ display: 'flex', gap: 22, alignItems: 'stretch' }}>
        {card(a, 'A', 0)}
        {card(b, 'B', 1)}
      </div>
      <div style={{ marginTop: 20, textAlign: 'center', fontFamily: MONO, fontSize: 26, letterSpacing: 5, textTransform: 'uppercase', color: light ? 'rgba(10,18,32,0.6)' : 'rgba(255,255,255,0.6)', opacity: tag }}>vote in the comments</div>
    </div>
  );
};

/* ───────────── film finish: grain, vignette and the breath before a data reveal ───────────── */

const GRAIN = `url("data:image/svg+xml;utf8,${encodeURIComponent("<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 0.55 0'/></filter><rect width='220' height='220' filter='url(#n)'/></svg>")}")`;

const REVEAL_TYPES = new Set(['counter', 'versus', 'verdict', 'timeline', 'units', 'split']);

/** Over every scene except real footage (which is shown untouched): a soft vignette, a faint moving grain (hides banding in the dark gradients) and, in the last frames before a data
 *  reveal, a short dip of the light so the number lands on a held breath. */
export const FilmFinish: React.FC<{ scenes: MotionScene[]; starts: number[]; current: number }> = ({ scenes, starts, current }) => {
  const frame = useCurrentFrame();
  const { light } = useTheme();
  if (scenes[current].type === 'footage') return null;
  let breath = 0;
  for (let i = 1; i < scenes.length; i++) {
    if (!REVEAL_TYPES.has(scenes[i].type)) continue;
    const at = starts[i];
    breath = Math.max(breath, interpolate(frame, [at - 9, at - 1, at + 6], [0, 1, 0], clamp));
  }
  const dark = light ? 0.1 : 0.34;
  const jx = (frame * 37) % 220;
  const jy = (frame * 61) % 220;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 85% 70% at 50% 46%, transparent 52%, rgba(0,0,0,${dark}) 100%)` }} />
      <AbsoluteFill style={{ backgroundImage: GRAIN, backgroundSize: '220px 220px', backgroundPosition: `${jx}px ${jy}px`, opacity: light ? 0.035 : 0.05 }} />
      {breath > 0.001 && <AbsoluteFill style={{ background: `rgba(0,0,0,${0.3 * breath})` }} />}
    </AbsoluteFill>
  );
};
