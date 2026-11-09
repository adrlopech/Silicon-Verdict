import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { Accent, EASE_IO, EASE_OUT, Kicker, SafeBox, Words, clamp, fit, useTheme } from './primitives';
import { MONO, SANS } from './fonts';
import { BRAND_BLUE, MotionScene, TIER_DROP, TIER_GRAB } from './types';

/** Scenes of the content formats: tier list, versus, myth-vs-fact verdict and timeline. Same data-only contract as the rest of the engine. */
type P = { scene: MotionScene };

const splitPipe = (it: string): [string, string] => {
  const i = it.indexOf('|');
  return i > 0 ? [it.slice(0, i).trim(), it.slice(i + 1).trim()] : ['', it.trim()];
};

/* ───────────── TIER LIST ───────────── */

const TIERS = ['S', 'A', 'B', 'C', 'D', 'F'];
const TIER_COLORS: Record<string, string> = { S: '#7DF9FF', A: '#4DC3FF', B: '#3D93FF', C: '#4E6FF2', D: '#5B55E6', F: '#7A5CE0' };

/**
 * The board fills up over several consecutive tier scenes: every scene repeats the items already placed and adds ONE more at the end
 * (the newest chip pops in with a glow, the rest are already on the board). items: "S|DDR5".
 */
export const Tier: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const entries = (scene.items ?? []).slice(0, 10).map((it) => {
    const [t, label] = splitPipe(it);
    return { tier: TIERS.includes(t.toUpperCase()) ? t.toUpperCase() : 'C', label };
  });
  const newest = entries.length - 1;
  const drag = scene.cursor === 'drag'; // the pointer carries the new chip from the tray (below the board) into its row
  const pop = drag ? spring({ frame: frame - TIER_DROP, fps, config: { damping: 12, stiffness: 190 } }) : spring({ frame: frame - 16, fps, config: { damping: 11, stiffness: 150 } });
  const carry = drag ? interpolate(frame, [TIER_GRAB, TIER_DROP], [0, 1], { ...clamp, easing: EASE_IO }) : 1; // 0 = in the tray, 1 = in its row
  const rowH = 104;
  return (
    <SafeBox gap={30}>
      <Kicker text={scene.kicker ?? 'tier list'} />
      <Words text={scene.text} size={88} />
      <Accent text={scene.accentText} size={104} delay={8} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10, width: 952, marginTop: 8 }}>
        {TIERS.map((t) => {
          const color = TIER_COLORS[t];
          return (
            <div key={t} style={{ display: 'flex', alignItems: 'stretch', minHeight: rowH, borderRadius: 20, overflow: drag ? 'visible' : 'hidden', background: light ? 'rgba(10,18,32,0.07)' : 'rgba(255,255,255,0.06)', border: `1px solid ${color}33` }}>
              <div style={{ width: rowH, flex: '0 0 auto', borderRadius: '20px 0 0 20px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: color, fontFamily: SANS, fontWeight: 900, fontSize: 68, color: '#05070C' }}>{t}</div>
              <div style={{ flex: 1, display: 'flex', flexWrap: 'wrap', alignContent: 'center', gap: 10, padding: '10px 16px' }}>
                {entries.map((e, i) => {
                  if (e.tier !== t) return null;
                  const isNew = i === newest;
                  const s = isNew ? pop : 1;
                  const rowIndex = TIERS.indexOf(t);
                  const trayDy = (TIERS.length - rowIndex) * (rowH + 10) + 70; // from below the board up to its row
                  const flying = isNew && drag;
                  return (
                    <div
                      key={i}
                      data-cursor={isNew ? 'newitem' : undefined}
                      style={{
                        padding: '10px 20px',
                        borderRadius: 14,
                        fontFamily: SANS,
                        fontWeight: 800,
                        fontSize: fit(34, e.label.length, 400, 0.56, 22),
                        whiteSpace: 'nowrap',
                        color: isNew ? '#05070C' : light ? '#0A1220' : theme.text,
                        background: isNew ? color : light ? 'rgba(10,18,32,0.1)' : 'rgba(255,255,255,0.12)',
                        boxShadow: flying ? `0 18px 40px rgba(0,0,0,0.5), 0 0 34px ${color}aa` : isNew ? `0 0 34px ${color}aa` : 'none',
                        opacity: flying ? Math.min(1, frame / 6) : Math.min(1, s * 1.4),
                        transform: flying
                          ? `translate(${(1 - carry) * 190}px, ${(1 - carry) * trayDy}px) rotate(${(1 - carry) * -3}deg) scale(${1.06 - 0.06 * carry + 0.1 * Math.max(0, s - 1)})`
                          : `scale(${0.4 + 0.6 * s}) translateY(${(1 - s) * -60}px)`,
                        position: flying ? 'relative' : undefined,
                        zIndex: flying ? 5 : undefined,
                      }}
                    >
                      {e.label}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </SafeBox>
  );
};

/* ───────────── VERSUS ───────────── */

const fmtNum = (v: number) => (Math.abs(v) >= 100 || Number.isInteger(v) ? String(Math.round(v)) : v.toFixed(1));

/** One metric, two contenders: bars grow to scale, the winner glows. `winner` defaults to the bigger value (use it for "lower is better" metrics). */
export const Versus: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const a = Math.max(0, scene.leftValue ?? 0);
  const b = Math.max(0, scene.rightValue ?? 0);
  const max = Math.max(a, b, 1e-9);
  const winner = scene.winner ?? (a === b ? 'none' : a > b ? 'left' : 'right');
  const p = spring({ frame: frame - 14, fps, config: { damping: 200, mass: 1.4 }, durationInFrames: Math.max(30, scene.durationInFrames - 34) });
  const crown = interpolate(frame, [Math.max(20, scene.durationInFrames - 46), Math.max(30, scene.durationInFrames - 30)], [0, 1], { ...clamp, easing: EASE_OUT });
  const barMax = 500;
  const text = light ? '#0A1220' : theme.text;
  const col = (label: string | undefined, v: number, side: 'left' | 'right') => {
    const isWin = winner === side;
    const color = side === 'left' ? theme.accent : theme.accent2 ?? BRAND_BLUE;
    const h = Math.max(10, (v / max) * barMax * p);
    const glow = isWin ? crown : 0;
    return (
      <div style={{ width: 400, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'flex-end', height: barMax + 150 }}>
        <div style={{ fontFamily: MONO, fontWeight: 600, fontSize: fit(88, fmtNum(v).length + (scene.unit ? scene.unit.length * 0.5 : 0), 380, 0.62, 52), color: text, textShadow: glow ? `0 0 40px ${color}` : 'none', marginBottom: 14 }}>
          {fmtNum(v * p)}
          {scene.unit && <span style={{ fontSize: 40, color, marginLeft: 8 }}>{scene.unit}</span>}
        </div>
        <div style={{ width: 230, height: h, borderRadius: '22px 22px 6px 6px', background: `linear-gradient(180deg, ${color}, ${color}55)`, boxShadow: glow ? `0 0 ${60 * glow}px ${color}` : `0 0 18px ${color}44`, opacity: winner === 'none' || isWin ? 1 : 1 - 0.35 * crown }} />
        <div style={{ marginTop: 18, height: 50, fontFamily: SANS, fontWeight: 900, fontSize: fit(46, (label ?? '').length, 380, 0.6, 26), textTransform: 'uppercase', letterSpacing: 1, color: text, textAlign: 'center' }}>{label}</div>
      </div>
    );
  };
  return (
    <SafeBox gap={26}>
      <Kicker text={scene.kicker ?? 'versus'} />
      <Words text={scene.text} size={86} />
      <Accent text={scene.accentText} size={104} delay={8} />
      <div style={{ position: 'relative', display: 'flex', alignItems: 'flex-end', justifyContent: 'center', gap: 40, marginTop: 6 }}>
        {col(scene.left, a, 'left')}
        <div style={{ position: 'absolute', left: '50%', top: 300, transform: 'translateX(-50%)', width: 96, height: 96, borderRadius: 48, display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#05070C', border: `2px solid ${theme.accent}`, boxShadow: `0 0 30px ${theme.accent}77`, fontFamily: SANS, fontWeight: 900, fontSize: 40, color: theme.accent, zIndex: 2 }}>VS</div>
        {col(scene.right, b, 'right')}
      </div>
    </SafeBox>
  );
};

/* ───────────── MYTH vs FACT VERDICT ───────────── */

const VERDICTS = {
  myth: { label: 'MYTH', color: '#7C8CFF' },
  fact: { label: 'FACT', color: '#00F0FF' },
  partly: { label: 'PARTLY TRUE', color: '#9CCBFF' },
} as const;

/** A claim on screen, then a stamp slams down: MYTH / FACT / PARTLY TRUE. The accent text is the one-line correction. */
export const Verdict: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const v = VERDICTS[scene.verdict ?? 'myth'];
  const hit = Math.min(44, Math.max(30, Math.round(scene.durationInFrames * 0.4)));
  const slam = spring({ frame: frame - hit, fps, config: { damping: 9, stiffness: 170, mass: 0.8 } });
  const shake = frame >= hit && frame < hit + 10 ? Math.sin((frame - hit) * 3.2) * (10 - (frame - hit)) * 1.6 : 0;
  const claimOpacity = scene.verdict === 'myth' ? 1 - 0.45 * Math.min(1, slam) : 1;
  const size = fit(v.label.length > 5 ? 120 : 190, v.label.length, 820, 0.78, 80);
  return (
    <SafeBox gap={44}>
      <div style={{ transform: `translate(${shake}px, ${shake * 0.6}px)`, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 44 }}>
        <Kicker text={scene.kicker ?? 'the claim'} />
        <div style={{ opacity: claimOpacity, width: 940, padding: '36px 34px', borderRadius: 30, background: light ? 'rgba(10,18,32,0.06)' : 'rgba(10,22,44,0.7)', border: `1px solid ${theme.accent}33`, boxShadow: '0 30px 90px rgba(0,0,0,0.45)' }}>
          <span style={{ fontFamily: SANS, fontWeight: 900, fontSize: 130, lineHeight: 0.6, color: theme.accent, display: 'block', textAlign: 'left', height: 56 }}>“</span>
          <Words text={scene.text} size={96} />
        </div>
        <div style={{ height: size * 1.3, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: size, letterSpacing: 6, color: v.color, border: `12px solid ${v.color}`, borderRadius: 22, padding: '4px 36px', textShadow: `0 0 40px ${v.color}88`, boxShadow: `0 0 50px ${v.color}55, inset 0 0 30px ${v.color}33`, opacity: Math.min(1, slam * 3), transform: `rotate(-7deg) scale(${2.8 - 1.8 * Math.min(1.08, slam)})` }}>{v.label}</div>
        </div>
        <Accent text={scene.accentText} size={96} delay={hit + 16} />
      </div>
    </SafeBox>
  );
};

/* ───────────── TIMELINE ───────────── */

/** Evolution over time. items: "1996|3dfx Voodoo". Nodes appear one after another along a growing line; the latest one is the bright one. */
export const Timeline: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const entries = (scene.items ?? []).slice(0, 5).map(splitPipe);
  const n = Math.max(1, entries.length);
  const step = Math.max(10, Math.floor((scene.durationInFrames - 44) / n));
  const rowH = 128;
  const lineH = (n - 1) * rowH;
  const progress = interpolate(frame, [14, 14 + step * (n - 1)], [0, 1], { ...clamp, easing: EASE_OUT });
  const text = light ? '#0A1220' : theme.text;
  return (
    <SafeBox gap={34}>
      <Kicker text={scene.kicker ?? 'timeline'} />
      <Words text={scene.text} size={88} />
      <Accent text={scene.accentText} size={104} delay={8} />
      <div style={{ position: 'relative', width: 900, height: lineH + 90, marginTop: 14 }}>
        <div style={{ position: 'absolute', left: 250, top: 22, width: 6, height: lineH, borderRadius: 3, background: light ? 'rgba(10,18,32,0.12)' : 'rgba(255,255,255,0.12)' }} />
        <div style={{ position: 'absolute', left: 250, top: 22, width: 6, height: lineH * progress, borderRadius: 3, background: `linear-gradient(180deg, ${BRAND_BLUE}, ${theme.accent})`, boxShadow: `0 0 18px ${theme.accent}` }} />
        {entries.map(([year, label], i) => {
          const s = spring({ frame: frame - 14 - i * step, fps, config: { damping: 16, stiffness: 120 } });
          const latest = frame >= 14 + i * step && (i === n - 1 || frame < 14 + (i + 1) * step);
          return (
            <div key={i} style={{ position: 'absolute', left: 0, top: i * rowH, width: 900, height: 56, display: 'flex', alignItems: 'center', opacity: Math.min(1, s * 1.5), transform: `translateX(${(1 - s) * 60}px)` }}>
              <div style={{ width: 230, textAlign: 'right', fontFamily: MONO, fontWeight: 600, fontSize: fit(52, year.length, 220, 0.62, 30), color: latest ? theme.accent : light ? 'rgba(10,18,32,0.55)' : 'rgba(255,255,255,0.55)' }}>{year}</div>
              <div style={{ width: 46, display: 'flex', justifyContent: 'center' }}>
                <div style={{ width: latest ? 30 : 20, height: latest ? 30 : 20, borderRadius: '50%', background: latest ? theme.accent : theme.accent2 ?? BRAND_BLUE, boxShadow: latest ? `0 0 30px ${theme.accent}` : 'none', border: '4px solid #05070C', marginLeft: 0 }} />
              </div>
              <div style={{ marginLeft: 26, flex: 1, fontFamily: SANS, fontWeight: 800, fontSize: fit(46, label.length, 560, 0.55, 26), lineHeight: 1.05, color: latest ? text : light ? 'rgba(10,18,32,0.7)' : 'rgba(255,255,255,0.72)', textAlign: 'left' }}>{label}</div>
            </div>
          );
        })}
      </div>
    </SafeBox>
  );
};
