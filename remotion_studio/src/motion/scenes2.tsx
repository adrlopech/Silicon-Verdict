import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { Accent, EASE_OUT, Kicker, SafeBox, Words, clamp, fit, useTheme } from './primitives';
import { MONO, SANS } from './fonts';
import { useLook } from './looks';
import { MotionScene, SAFE_TOP } from './types';

/** Scenes of the newer formats: Top 5 countdown (rank), Tech Quiz (quiz) and the news bulletin (headline). Same data-only contract as the rest of the engine. */
type P = { scene: MotionScene };

/* ───────────── RANK (Top 5) ───────────── */

/** One entry of a countdown: a giant position number, the item and the one-line why. The five positions are shown as a strip so the viewer sees how far the countdown has got. */
export const Rank: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const look = useLook();
  const n = Math.round(scene.value ?? 1);
  const pop = spring({ frame: frame - 2, fps, config: { damping: 11, stiffness: 150, mass: 0.9 } });
  const glow = 0.5 + 0.5 * Math.sin(frame / 9);
  const left = look.align === 'left';
  const ink = light ? '#0A1220' : theme.text;
  return (
    <SafeBox gap={26}>
      <Kicker text={scene.kicker ?? 'top 5'} />
      <div style={{ display: 'flex', gap: 18, alignItems: 'center' }}>
        {[5, 4, 3, 2, 1].map((k) => {
          const now = k === n;
          const done = k > n;
          return <div key={k} style={{ width: now ? 74 : 52, height: now ? 74 : 52, borderRadius: 18, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: MONO, fontWeight: 700, fontSize: now ? 40 : 28, color: now ? '#05070C' : ink, background: now ? theme.accent : 'transparent', border: `2px solid ${theme.accent}${done ? '99' : '44'}`, opacity: done ? 0.55 : 1, boxShadow: now ? `0 0 34px ${theme.accent}99` : 'none' }}>{done ? '✓' : k}</div>;
        })}
      </div>
      <div style={{ position: 'relative', fontFamily: SANS, fontWeight: 900, fontSize: 560, lineHeight: 0.84, letterSpacing: -26, color: 'transparent', WebkitTextStroke: `10px ${theme.accent}`, textShadow: light ? 'none' : `0 0 ${60 + glow * 40}px ${theme.accent}77`, opacity: Math.min(1, pop * 1.6), transform: `scale(${0.55 + 0.45 * Math.min(1.06, pop)}) rotate(${(1 - Math.min(1, pop)) * -8}deg)`, margin: '6px 0 -16px' }}>{n}</div>
      <Words text={scene.text} size={scene.text.split(' ').length > 3 ? 104 : 126} delay={10} />
      <Accent text={scene.accentText} size={scene.text.split(' ').length > 3 ? 120 : 140} delay={18} />
    </SafeBox>
  );
};

/* ───────────── QUIZ ───────────── */

/** A question with three options. A countdown runs over the first half of the scene; then the right answer lights up and the others fade. */
export const Quiz: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const options = (scene.items ?? []).slice(0, 3);
  const right = Math.max(1, Math.min(3, Math.round(scene.value ?? 1))) - 1;
  const reveal = Math.round(scene.durationInFrames * 0.56);
  const secs = Math.max(1, Math.ceil((reveal - 14) / fps));
  const left = Math.max(0, secs - Math.floor(Math.max(0, frame - 14) / fps));
  const live = frame < reveal;
  const ring = interpolate(frame, [14, reveal], [1, 0], clamp);
  const slam = spring({ frame: frame - reveal, fps, config: { damping: 10, stiffness: 180, mass: 0.8 } });
  const ink = light ? '#0A1220' : theme.text;
  const R = 62;
  return (
    <SafeBox gap={34}>
      <Kicker text={scene.kicker ?? 'tech quiz'} />
      <div style={{ display: 'flex', alignItems: 'center', gap: 30, width: 940, justifyContent: 'center' }}>
        <div style={{ flex: 1 }}><Words text={scene.text} size={scene.text.split(' ').length > 5 ? 84 : 98} /></div>
        <div style={{ position: 'relative', width: R * 2 + 16, height: R * 2 + 16, flex: '0 0 auto', opacity: live ? 1 : Math.max(0, 1 - (frame - reveal) / 8) }}>
          <svg width={R * 2 + 16} height={R * 2 + 16} style={{ transform: 'rotate(-90deg)' }}>
            <circle cx={R + 8} cy={R + 8} r={R} fill="none" stroke={`${theme.accent}33`} strokeWidth={10} />
            <circle cx={R + 8} cy={R + 8} r={R} fill="none" stroke={theme.accent} strokeWidth={10} strokeLinecap="round" strokeDasharray={2 * Math.PI * R} strokeDashoffset={2 * Math.PI * R * (1 - ring)} style={{ filter: `drop-shadow(0 0 10px ${theme.accent})` }} />
          </svg>
          <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: MONO, fontWeight: 700, fontSize: 64, color: theme.accent }}>{left}</div>
        </div>
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 24, width: 940 }}>
        {options.map((o, i) => {
          const s = spring({ frame: frame - 10 - i * 7, fps, config: { damping: 200 } });
          const isRight = i === right;
          const revealed = frame >= reveal;
          const hit = isRight && revealed ? Math.min(1, slam) : 0;
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 28, padding: '26px 34px', borderRadius: 28, background: hit ? theme.accent : light ? 'rgba(10,18,32,0.07)' : 'rgba(10,22,44,0.7)', border: `3px solid ${hit ? theme.accent : theme.accent + '44'}`, boxShadow: hit ? `0 0 60px ${theme.accent}99` : 'none', opacity: (revealed && !isRight ? 0.32 : 1) * s, transform: `translateX(${(1 - s) * -80}px) scale(${1 + 0.05 * hit})` }}>
              <div style={{ width: 70, height: 70, borderRadius: 20, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: MONO, fontWeight: 700, fontSize: 40, color: hit ? theme.accent : '#05070C', background: hit ? '#05070C' : theme.accent }}>{hit ? '✓' : 'ABC'[i]}</div>
              <div style={{ fontFamily: SANS, fontWeight: 800, fontSize: fit(64, o.length, 700, 0.5, 40), letterSpacing: -1.5, color: hit ? '#05070C' : ink }}>{o}</div>
            </div>
          );
        })}
      </div>
    </SafeBox>
  );
};

/* ───────────── HEADLINE (news bulletin) ───────────── */

/** A story of the bulletin as a broadcast graphic: a "briefing" tag with a live dot, the outlet chip, the headline, what it means, and a scrolling ticker band at the foot. */
export const Headline: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const look = useLook();
  const bar = interpolate(frame, [0, 22], [0, 1], { ...clamp, easing: EASE_OUT });
  const pop = spring({ frame: frame - 6, fps, config: { damping: 15, stiffness: 140, mass: 0.8 } });
  const blink = Math.floor(frame / 15) % 2 === 0;
  const ink = light ? '#0A1220' : theme.text;
  const strip = '   ///   TECH BRIEFING   ///   SILICON VERDICT   ///   ';
  const x = -((frame * 5) % (strip.length * 24));
  const left = look.align === 'left';
  return (
    <>
      <div style={{ position: 'absolute', left: 64, top: SAFE_TOP + 20, display: 'flex', alignItems: 'center', gap: 16, opacity: bar, transform: `translateX(${(1 - bar) * -80}px)` }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '10px 26px', borderRadius: 14, background: theme.accent, color: '#05070C', fontFamily: MONO, fontWeight: 700, fontSize: 34, letterSpacing: 6 }}>
          <span style={{ width: 16, height: 16, borderRadius: 8, background: '#05070C', opacity: blink ? 1 : 0.25 }} />
          BRIEFING
        </div>
        {scene.unit && <div style={{ fontFamily: MONO, fontSize: 30, letterSpacing: 6, color: ink, opacity: 0.8 }}>{scene.unit.toUpperCase()}</div>}
      </div>
      <SafeBox gap={34}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, alignSelf: left ? 'flex-start' : 'center', opacity: Math.min(1, pop * 1.5), transform: `translateY(${(1 - Math.min(1, pop)) * 30}px)` }}>
          <div style={{ width: 8, height: 54, borderRadius: 4, background: theme.accent, boxShadow: `0 0 20px ${theme.accent}` }} />
          <div style={{ fontFamily: MONO, fontWeight: 700, fontSize: fit(48, (scene.kicker ?? '').length, 760, 0.7, 30), letterSpacing: 7, color: theme.accent }}>{(scene.kicker ?? '').toUpperCase()}</div>
        </div>
        <div style={{ width: 952, padding: '44px 46px', borderRadius: 38, background: light ? 'rgba(255,255,255,0.9)' : 'rgba(8,18,42,0.78)', border: `2px solid ${theme.accent}55`, boxShadow: `0 40px 100px rgba(0,0,0,0.4), 0 0 60px ${theme.accent}22`, opacity: Math.min(1, pop * 1.4), transform: `scale(${0.95 + 0.05 * Math.min(1, pop)})` }}>
          <Words text={scene.text} size={scene.text.split(' ').length > 6 ? 82 : 96} />
        </div>
        <Accent text={scene.accentText} size={112} delay={14} />
      </SafeBox>
      <AbsoluteFill style={{ pointerEvents: 'none' }}>
        <div style={{ position: 'absolute', left: 0, right: 0, bottom: 560, height: 56, overflow: 'hidden', borderTop: `2px solid ${theme.accent}55`, borderBottom: `2px solid ${theme.accent}55`, background: light ? 'rgba(255,255,255,0.7)' : 'rgba(5,10,24,0.7)', opacity: bar }}>
          <div style={{ position: 'absolute', left: x, top: 8, whiteSpace: 'nowrap', fontFamily: MONO, fontWeight: 500, fontSize: 30, letterSpacing: 5, color: theme.accent }}>{strip.repeat(6)}</div>
        </div>
      </AbsoluteFill>
    </>
  );
};
