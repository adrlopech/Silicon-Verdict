import React, { useEffect, useRef } from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { MONO, SANS } from './fonts';
import { Accent, EASE_OUT, SafeBox, Words, clamp, fit, useTheme } from './primitives';
import { BRAND_BLUE, MotionScene } from './types';

type P = { scene: MotionScene };

const fmt = (v: number) => (Math.abs(v) >= 100 || Number.isInteger(v) ? Math.round(v).toLocaleString('en-US') : v.toFixed(1));

/* ───────────── SPLIT: two panels compared one above the other ───────────── */

/** A/B comparison in two stacked panels with the labels of each side on its corner and a divider chip between them.
 *  `demo` chooses what each panel draws: bars (default: a big figure and a proportional bar), res (the same shape drawn with few and with many pixels), speed (two runners racing at the two speeds),
 *  size (two squares whose AREAS follow the figures) or ago (a counter that counts up to how long ago, for then-versus-now). The figures come from leftValue / rightValue and `unit`. */
export const Split: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const demo = scene.demo ?? 'bars';
  const a = Math.max(0, scene.leftValue ?? 0);
  const b = Math.max(0, scene.rightValue ?? 0);
  const max = Math.max(a, b, 1e-9);
  const p = spring({ frame: frame - 10, fps, config: { damping: 200, mass: 1.3 }, durationInFrames: Math.max(30, scene.durationInFrames - 34) });
  const text = light ? '#0A1220' : theme.text;
  const accents = [theme.accent, theme.accent2 ?? BRAND_BLUE];
  const H = 290;
  const enter = (i: number) => interpolate(frame, [i * 8, 16 + i * 8], [0, 1], { ...clamp, easing: EASE_OUT });

  const Res: React.FC<{ n: number; color: string }> = ({ n, color }) => {
    const ref = useRef<HTMLCanvasElement>(null);
    useEffect(() => {
      const c = ref.current;
      if (!c) return;
      const ctx = c.getContext('2d');
      if (!ctx) return;
      ctx.clearRect(0, 0, c.width, c.height);
      ctx.strokeStyle = color;
      ctx.fillStyle = color;
      ctx.lineWidth = Math.max(1, c.width / 14);
      ctx.beginPath();
      ctx.arc(c.width / 2, c.height / 2, c.width * 0.36, 0, Math.PI * 2);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(c.width * 0.22, c.height * 0.78);
      ctx.lineTo(c.width * 0.78, c.height * 0.22);
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(c.width * 0.5, c.height * 0.5, c.width * 0.09, 0, Math.PI * 2);
      ctx.fill();
    });
    return <canvas ref={ref} width={n} height={n} style={{ width: 250, height: 250, imageRendering: 'pixelated', borderRadius: 16, background: 'rgba(255,255,255,0.05)' }} />;
  };

  const panel = (label: string | undefined, v: number, side: 0 | 1) => {
    const color = accents[side];
    const win = v === max && a !== b;
    const e = enter(side);
    let body: React.ReactNode;
    if (demo === 'res') {
      const n = Math.max(6, Math.min(120, Math.round((v / max) * 96)));
      body = (
        <div style={{ display: 'flex', alignItems: 'center', gap: 40 }}>
          <Res n={n} color={color} />
          <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: fit(92, fmt(v).length, 380, 0.62, 48), color: text }}>{fmt(v)}<span style={{ fontSize: 40, color, marginLeft: 8 }}>{scene.unit}</span></div>
        </div>
      );
    } else if (demo === 'speed') {
      const lap = Math.max(24, scene.durationInFrames - 40);
      const run = interpolate(frame, [14, 14 + (lap * 0.8) * (max / Math.max(v, 1e-9))], [0, 1], clamp);
      body = (
        <div style={{ width: 800, position: 'relative', height: 150 }}>
          <div style={{ position: 'absolute', left: 0, right: 0, top: 86, height: 8, borderRadius: 4, background: 'rgba(255,255,255,0.14)' }} />
          <div style={{ position: 'absolute', left: 0, top: 86, width: `${run * 100}%`, height: 8, borderRadius: 4, background: color, boxShadow: `0 0 18px ${color}` }} />
          <div style={{ position: 'absolute', right: 0, top: 54, width: 6, height: 72, background: text, opacity: 0.6 }} />
          <div style={{ position: 'absolute', left: `calc(${run * 100}% - 28px)`, top: 58, width: 56, height: 56, borderRadius: 28, background: color, boxShadow: `0 0 34px ${color}` }} />
          <div style={{ position: 'absolute', left: 0, top: -4, fontFamily: MONO, fontWeight: 600, fontSize: 64, color: text }}>{fmt(v)}<span style={{ fontSize: 34, color, marginLeft: 8 }}>{scene.unit}</span></div>
          {run >= 1 && <div style={{ position: 'absolute', right: 20, top: -2, fontFamily: MONO, fontSize: 40, color }}>✓ done</div>}
        </div>
      );
    } else if (demo === 'size') {
      const side2 = Math.max(40, Math.sqrt(v / max) * 250 * p);
      body = (
        <div style={{ display: 'flex', alignItems: 'center', gap: 44 }}>
          <div style={{ width: 260, height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <div style={{ width: side2, height: side2, borderRadius: 18, background: `linear-gradient(145deg, ${color}, ${color}55)`, boxShadow: `0 0 36px ${color}66` }} />
          </div>
          <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: fit(88, fmt(v).length, 420, 0.62, 48), color: text }}>{fmt(v)}<span style={{ fontSize: 38, color, marginLeft: 8 }}>{scene.unit}</span></div>
        </div>
      );
    } else if (demo === 'ago') {
      body = (
        <div style={{ textAlign: 'center' }}>
          <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: fit(150, fmt(v).length, 800, 0.62, 70), color: text, textShadow: win ? `0 0 40px ${color}` : 'none' }}>{fmt(v * p)}</div>
          <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: 44, color, letterSpacing: 2, textTransform: 'uppercase' }}>{scene.unit ?? 'days ago'}</div>
        </div>
      );
    } else {
      body = (
        <div style={{ width: 820 }}>
          <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: fit(104, fmt(v).length + (scene.unit ? scene.unit.length * 0.5 : 0), 820, 0.62, 56), color: text, textShadow: win ? `0 0 36px ${color}` : 'none' }}>
            {fmt(v * p)}{scene.unit && <span style={{ fontSize: 44, color, marginLeft: 10 }}>{scene.unit}</span>}
          </div>
          <div style={{ marginTop: 18, height: 26, borderRadius: 13, background: 'rgba(255,255,255,0.12)', overflow: 'hidden' }}>
            <div style={{ width: `${(v / max) * 100 * p}%`, height: '100%', borderRadius: 13, background: `linear-gradient(90deg, ${color}, ${color}88)`, boxShadow: `0 0 22px ${color}88` }} />
          </div>
        </div>
      );
    }
    return (
      <div key={side} style={{ position: 'relative', width: 920, height: H, borderRadius: 28, background: light ? 'rgba(255,255,255,0.8)' : 'rgba(10,22,44,0.7)', border: `2px solid ${color}${win ? 'EE' : '55'}`, boxShadow: win ? `0 0 46px ${color}55` : 'none', display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: e, transform: `translateX(${(1 - e) * (side ? 120 : -120)}px)` }}>
        <div style={{ position: 'absolute', left: 26, top: 20, padding: '6px 22px', borderRadius: 999, background: color, color: '#05070C', fontFamily: SANS, fontWeight: 900, fontSize: fit(40, (label ?? '').length, 520, 0.6, 24), textTransform: 'uppercase', letterSpacing: 1 }}>{label}</div>
        {body}
      </div>
    );
  };

  return (
    <SafeBox gap={20}>
      <Words text={scene.text} size={64} />
      <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: 24, alignItems: 'center' }}>
        {panel(scene.left, a, 0)}
        <div style={{ position: 'absolute', left: '50%', top: H + 12, transform: 'translate(-50%, -50%)', width: 76, height: 76, borderRadius: 38, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#05070C', border: `2px solid ${theme.accent}`, fontFamily: MONO, fontWeight: 700, fontSize: 28, color: theme.accent, zIndex: 2 }}>VS</div>
        {panel(scene.right, b, 1)}
      </div>
      <Accent text={scene.accentText} size={72} delay={10} />
    </SafeBox>
  );
};

/* ───────────── UNITS: a price or size converted into a unit ───────────── */

type Glyph = 'card' | 'chip' | 'ram' | 'drive' | 'phone' | 'coin' | 'bolt' | 'console' | 'cube';

const glyphFor = (unit: string): Glyph => {
  const u = unit.toLowerCase();
  if (/gpu|graphics|card|rtx|radeon/.test(u)) return 'card';
  if (/cpu|chip|processor|ryzen|core/.test(u)) return 'chip';
  if (/ram|memory|dimm|stick/.test(u)) return 'ram';
  if (/ssd|drive|disk|nvme|storage/.test(u)) return 'drive';
  if (/phone|iphone|galaxy|pixel/.test(u)) return 'phone';
  if (/\$|dollar|coin|cent|euro|buck/.test(u)) return 'coin';
  if (/watt|power|battery|charg/.test(u)) return 'bolt';
  if (/console|ps5|playstation|xbox|switch|deck/.test(u)) return 'console';
  return 'cube';
};

const GlyphSvg: React.FC<{ kind: Glyph; color: string; size: number; fill?: number }> = ({ kind, color, size, fill = 1 }) => {
  const id = `g${kind}${size}${Math.round(fill * 100)}`;
  const body: Record<Glyph, React.ReactNode> = {
    card: (
      <>
        <rect x="2" y="12" width="60" height="30" rx="4" fill="none" stroke={color} strokeWidth="3" />
        <circle cx="22" cy="27" r="9" fill="none" stroke={color} strokeWidth="3" />
        <circle cx="44" cy="27" r="9" fill="none" stroke={color} strokeWidth="3" />
        <path d="M10 42v6h14v-6" fill="none" stroke={color} strokeWidth="3" />
      </>
    ),
    chip: (
      <>
        <rect x="14" y="14" width="36" height="36" rx="5" fill="none" stroke={color} strokeWidth="3" />
        <rect x="24" y="24" width="16" height="16" rx="2" fill={color} />
        {[20, 32, 44].map((v) => <path key={v} d={`M${v} 6v8M${v} 50v8M6 ${v}h8M50 ${v}h8`} stroke={color} strokeWidth="3" />)}
      </>
    ),
    ram: (
      <>
        <rect x="2" y="16" width="60" height="26" rx="3" fill="none" stroke={color} strokeWidth="3" />
        {[12, 24, 36, 48].map((v) => <rect key={v} x={v} y="22" width="8" height="12" fill={color} />)}
        <path d="M8 42v6M20 42v6M32 42v6M44 42v6M56 42v6" stroke={color} strokeWidth="3" />
      </>
    ),
    drive: (
      <>
        <rect x="6" y="10" width="52" height="44" rx="6" fill="none" stroke={color} strokeWidth="3" />
        <circle cx="32" cy="32" r="12" fill="none" stroke={color} strokeWidth="3" />
        <circle cx="32" cy="32" r="3" fill={color} />
      </>
    ),
    phone: (
      <>
        <rect x="18" y="4" width="28" height="56" rx="6" fill="none" stroke={color} strokeWidth="3" />
        <path d="M28 52h8" stroke={color} strokeWidth="3" />
      </>
    ),
    coin: (
      <>
        <circle cx="32" cy="32" r="26" fill="none" stroke={color} strokeWidth="3" />
        <path d="M32 16v32M40 22c-2-3-12-4-14 1s6 6 10 8 8 5 4 9-12 3-14 0" fill="none" stroke={color} strokeWidth="3" strokeLinecap="round" />
      </>
    ),
    bolt: <path d="M36 4L14 36h16l-4 24 24-34H34z" fill="none" stroke={color} strokeWidth="3" strokeLinejoin="round" />,
    console: (
      <>
        <path d="M14 22c-6 0-10 8-10 20 0 8 4 10 8 7l8-8h24l8 8c4 3 8 1 8-7 0-12-4-20-10-20z" fill="none" stroke={color} strokeWidth="3" strokeLinejoin="round" />
        <path d="M18 29v10M13 34h10" stroke={color} strokeWidth="3" strokeLinecap="round" />
        <circle cx="44" cy="31" r="2.6" fill={color} />
        <circle cx="50" cy="36" r="2.6" fill={color} />
      </>
    ),
    cube: (
      <>
        <path d="M32 6l24 12v28L32 58 8 46V18z" fill="none" stroke={color} strokeWidth="3" strokeLinejoin="round" />
        <path d="M8 18l24 12 24-12M32 30v28" fill="none" stroke={color} strokeWidth="3" strokeLinejoin="round" />
      </>
    ),
  };
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" style={{ overflow: 'visible' }}>
      <defs>
        <clipPath id={id}><rect x="0" y="0" width={64 * fill} height="64" /></clipPath>
      </defs>
      <g clipPath={fill < 1 ? `url(#${id})` : undefined} style={{ filter: `drop-shadow(0 0 5px ${color}88)` }}>{body[kind]}</g>
    </svg>
  );
};

/** The cost (or size) of something in units of another thing: a header names the unit, a grid of icons fills up one by one, a big "x5" counts, and the item and its price sit under it.
 *  text = the item, value = how many units (decimals under 1 draw part of one icon), unit = the unit's name, accentText = the item's own price or size, kicker = the header (default "cost in units of"). */
export const Units: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const v = Math.max(0, scene.value ?? 0);
  const unit = scene.unit ?? 'units';
  const kind = glyphFor(unit);
  const shown = Math.min(60, Math.ceil(v));
  const cell = shown <= 6 ? 190 : shown <= 12 ? 150 : shown <= 24 ? 118 : shown <= 40 ? 94 : 76;
  const cols = Math.max(1, Math.min(shown, Math.floor(920 / cell)));
  const p = spring({ frame: frame - 8, fps, config: { damping: 200, mass: 1.2 }, durationInFrames: Math.max(24, Math.min(80, scene.durationInFrames - 30)) });
  const count = v * p;
  const text = light ? '#0A1220' : theme.text;
  const color = theme.accent;
  const bigTxt = v >= 1 ? `×${Math.round(count)}` : `×${(count).toFixed(2).replace(/0+$/, '').replace(/\.$/, '')}`;
  return (
    <SafeBox gap={22}>
      <div style={{ fontFamily: MONO, fontSize: 34, letterSpacing: 5, textTransform: 'uppercase', color: light ? 'rgba(10,18,32,0.65)' : 'rgba(255,255,255,0.7)' }}>{scene.kicker ?? 'cost in units of'}</div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 22 }}>
        <GlyphSvg kind={kind} color={color} size={86} />
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: fit(84, unit.length, 520, 0.6, 40), color, textTransform: 'uppercase', letterSpacing: -1 }}>{unit}</div>
      </div>
      <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: 190, lineHeight: 1, color: text, textShadow: `0 0 50px ${color}99` }}>{bigTxt}</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', width: cols * cell, minHeight: Math.ceil(shown / cols) * cell, gap: 0 }}>
        {Array.from({ length: shown }).map((_, i) => {
          const at = 8 + (i / Math.max(1, shown)) * Math.min(60, scene.durationInFrames - 36);
          const e = interpolate(frame, [at, at + 10], [0, 1], { ...clamp, easing: EASE_OUT });
          const last = i === shown - 1 && v % 1 !== 0 && v < shown + 1e-9;
          return (
            <div key={i} style={{ width: cell, height: cell, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: e, transform: `scale(${0.5 + 0.5 * e})` }}>
              <GlyphSvg kind={kind} color={i % 2 ? theme.accent2 ?? BRAND_BLUE : color} size={cell * 0.74} fill={last ? v % 1 : 1} />
            </div>
          );
        })}
      </div>
      {v > 60 && <div style={{ fontFamily: MONO, fontSize: 34, color }}>+ {Math.round(v - 60)} more</div>}
      <Words text={scene.text} size={78} delay={8} />
      <Accent text={scene.accentText} size={86} delay={14} />
    </SafeBox>
  );
};
