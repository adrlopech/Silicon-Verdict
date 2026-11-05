import React from 'react';
import { AbsoluteFill, Img, Loop, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { Accent, Burst, EASE_IO, EASE_OUT, Kicker, SafeBox, Words, clamp, fit, useTheme } from './primitives';
import { MONO, SANS } from './fonts';
import { BRAND_BLUE, MotionScene, SAFE_BOTTOM, SAFE_TOP } from './types';

type P = { scene: MotionScene };

export const BigText: React.FC<P> = ({ scene }) => (
  <SafeBox>
    <Kicker text={scene.kicker} />
    <Words text={scene.text} size={scene.text.length > 18 ? 150 : 190} upper />
    {scene.accentText && <Accent text={scene.accentText} size={150} delay={14} />}
  </SafeBox>
);

export const TextWithAccent: React.FC<P> = ({ scene }) => (
  <SafeBox gap={12}>
    <Kicker text={scene.kicker} />
    <Words text={scene.text} size={scene.text.split(' ').length > 3 ? 112 : 136} />
    <Accent text={scene.accentText} size={scene.text.split(' ').length > 3 ? 150 : 176} delay={12} />
  </SafeBox>
);

export const Counter: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const target = scene.value ?? 100;
  const p = spring({ frame: frame - 10, fps, config: { damping: 200, mass: 1.6 }, durationInFrames: Math.max(30, scene.durationInFrames - 26) });
  const shown = Math.round(target * p);
  const digits = Math.max(4, String(Math.round(target)).length);
  const dots = 12;
  const numSize = fit(210, digits + (scene.unit ? scene.unit.length * 0.55 + 0.4 : 0), 900, 0.62, 80);
  return (
    <SafeBox gap={40}>
      <Kicker text={scene.kicker} />
      <Words text={scene.text} size={104} />
      <Accent text={scene.accentText} size={132} delay={10} />
      <div style={{ fontFamily: MONO, fontWeight: 500, fontSize: numSize, letterSpacing: 6, color: light ? '#0A1220' : theme.text, textShadow: light ? 'none' : `0 0 40px ${theme.accent}55`, marginTop: 10 }}>
        {String(shown).padStart(digits, '0')}
        {scene.unit && <span style={{ fontSize: numSize * 0.38, color: theme.accent, marginLeft: 14 }}>{scene.unit}</span>}
      </div>
      <div style={{ display: 'flex', gap: 22 }}>
        {Array.from({ length: dots }).map((_, i) => {
          const lit = interpolate(p * dots, [i, i + 1], [0, 1], clamp);
          return <div key={i} style={{ width: 20, height: 20, transform: 'rotate(45deg)', background: theme.accent, opacity: 0.18 + 0.82 * lit, boxShadow: lit > 0.5 ? `0 0 18px ${theme.accent}` : 'none' }} />;
        })}
      </div>
    </SafeBox>
  );
};

export const ListScene: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const items = (scene.items ?? []).slice(0, 4);
  const itemSize = fit(70, Math.max(1, ...items.map((t) => t.length)), 760, 0.52, 42);
  return (
    <SafeBox gap={46}>
      <Kicker text={scene.kicker} />
      <Words text={scene.text} size={100} />
      <Accent text={scene.accentText} size={120} delay={8} />
      <div style={{ display: 'flex', flexDirection: 'column', gap: 30, alignItems: 'flex-start', marginTop: 16, maxWidth: 940 }}>
        {items.map((it, i) => {
          const s = spring({ frame: frame - 20 - i * 9, fps, config: { damping: 200 } });
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'baseline', gap: 28, opacity: s, transform: `translateX(${(1 - s) * -70}px)`, filter: `blur(${(1 - s) * 10}px)` }}>
              <span style={{ fontFamily: MONO, fontSize: 40, color: theme.accent }}>{String(i + 1).padStart(2, '0')}</span>
              <span style={{ fontFamily: SANS, fontWeight: 800, fontSize: itemSize, letterSpacing: -2, lineHeight: 1.1, color: light ? '#0A1220' : theme.text }}>{it}</span>
            </div>
          );
        })}
      </div>
    </SafeBox>
  );
};

const KEYWORDS = /\b(const|let|return|import|from|export|function|async|await|if|else|for|new|class|true|false|def|print)\b/g;
const highlight = (line: string, accent: string): React.ReactNode[] => {
  const parts = line.split(/("[^"]*"|'[^']*'|\/\/.*$|#.*$|\b\d+(?:\.\d+)?\b)/g);
  return parts.map((part, i) => {
    if (!part) return null;
    if (/^["']/.test(part)) return <span key={i} style={{ color: '#7CFFB2' }}>{part}</span>;
    if (/^(\/\/|#)/.test(part)) return <span key={i} style={{ color: 'rgba(255,255,255,0.35)' }}>{part}</span>;
    if (/^\d/.test(part)) return <span key={i} style={{ color: '#8FC6FF' }}>{part}</span>;
    const sub = part.split(KEYWORDS);
    return sub.map((s, j) => (KEYWORDS.test(s) && (KEYWORDS.lastIndex = 0, true) ? <span key={`${i}-${j}`} style={{ color: accent }}>{s}</span> : <span key={`${i}-${j}`}>{s}</span>));
  });
};

export const CodeBlock: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { theme } = useTheme();
  const lines = (scene.code ?? []).slice(0, 8);
  const codeSize = fit(32, Math.max(1, ...lines.map((l) => l.length)) + 4, 800, 0.6, 22);
  const total = lines.join('\n').length || 1;
  const typed = Math.floor(interpolate(frame, [8, Math.max(24, scene.durationInFrames - 30)], [0, total], { ...clamp, easing: EASE_IO }));
  let left = typed;
  const panel = interpolate(frame, [0, 16], [0, 1], { ...clamp, easing: EASE_OUT });
  return (
    <SafeBox gap={52}>
      <div style={{ width: 920, borderRadius: 30, padding: '30px 38px 38px', background: 'rgba(10,22,44,0.72)', border: `1px solid ${theme.accent}33`, boxShadow: `0 30px 90px rgba(0,0,0,0.5), 0 0 0 1px ${theme.accent}22`, opacity: panel, transform: `translateY(${(1 - panel) * 40}px) scale(${0.97 + 0.03 * panel})`, textAlign: 'left' }}>
        <div style={{ display: 'flex', gap: 12, marginBottom: 26 }}>
          {['#007AFF', '#00F0FF', 'rgba(255,255,255,0.45)'].map((c) => <div key={c} style={{ width: 16, height: 16, borderRadius: 8, background: c }} />)}
          <span style={{ marginLeft: 18, fontFamily: MONO, fontSize: 22, color: 'rgba(255,255,255,0.4)' }}>{scene.kicker ?? 'script.ts'}</span>
        </div>
        {lines.map((line, i) => {
          const shownChars = Math.max(0, Math.min(line.length, left));
          left -= line.length + 1;
          const cursor = shownChars > 0 && shownChars < line.length;
          return (
            <div key={i} style={{ fontFamily: MONO, fontSize: codeSize, lineHeight: 1.6, color: '#E8EEF8', whiteSpace: 'pre', overflow: 'hidden', minHeight: 50 }}>
              <span style={{ color: 'rgba(255,255,255,0.25)', marginRight: 24 }}>{i + 1}</span>
              {highlight(line.slice(0, shownChars), theme.accent)}
              {cursor && <span style={{ background: theme.accent, color: 'transparent' }}>▌</span>}
            </div>
          );
        })}
      </div>
      <Words text={scene.text} size={92} delay={18} />
      <Accent text={scene.accentText} size={116} delay={26} />
    </SafeBox>
  );
};

export const ProgressBar: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const target = Math.max(0, Math.min(100, scene.value ?? 100));
  const p = spring({ frame: frame - 14, fps, config: { damping: 200, mass: 1.8 }, durationInFrames: Math.max(30, scene.durationInFrames - 30) });
  return (
    <SafeBox gap={44}>
      <Kicker text={scene.kicker} />
      <Words text={scene.text} size={112} />
      <Accent text={scene.accentText} size={150} delay={10} />
      <div style={{ width: 860, height: 22, borderRadius: 11, background: light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)', overflow: 'hidden', marginTop: 24 }}>
        <div style={{ width: `${target * p}%`, height: '100%', borderRadius: 11, background: `linear-gradient(90deg, ${BRAND_BLUE}, ${theme.accent})`, boxShadow: `0 0 28px ${theme.accent}` }} />
      </div>
      <div style={{ fontFamily: MONO, fontSize: 120, fontWeight: 500, color: light ? '#0A1220' : theme.text }}>
        {Math.round(target * p)}
        <span style={{ color: theme.accent }}>{scene.unit ?? '%'}</span>
      </div>
    </SafeBox>
  );
};

/** Eased S-curve drawn on a chart, with a glowing dot riding it: "every curve" in the reference. */
export const Curve: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { theme, light } = useTheme();
  const t = interpolate(frame, [10, Math.max(30, scene.durationInFrames - 20)], [0, 1], { ...clamp, easing: EASE_IO });
  const w = 760, h = 420;
  const P0 = [0, h], P1 = [w * 0.55, h], P2 = [w * 0.45, 0], P3 = [w, 0];
  const bez = (a: number, b: number, c: number, d: number) => (1 - t) ** 3 * a + 3 * (1 - t) ** 2 * t * b + 3 * (1 - t) * t * t * c + t ** 3 * d;
  const dx = bez(P0[0], P1[0], P2[0], P3[0]);
  const dy = bez(P0[1], P1[1], P2[1], P3[1]);
  const stroke = light ? '#0A1220' : theme.accent;
  return (
    <SafeBox gap={40}>
      <Kicker text={scene.kicker} />
      <Words text={scene.text} size={112} />
      <Accent text={scene.accentText} size={150} delay={10} />
      <svg width={w + 80} height={h + 80} viewBox={`-40 -40 ${w + 80} ${h + 80}`} style={{ marginTop: 20, overflow: 'visible' }}>
        {[0, 0.5, 1].map((g) => <line key={g} x1={0} x2={w} y1={h * g} y2={h * g} stroke={light ? 'rgba(0,0,0,0.12)' : 'rgba(255,255,255,0.12)'} strokeWidth={2} />)}
        <path d={`M ${P0} C ${P1} ${P2} ${P3}`} fill="none" stroke={stroke} strokeWidth={9} strokeLinecap="round" pathLength={1} strokeDasharray={1} strokeDashoffset={1 - t} style={{ filter: light ? 'none' : `drop-shadow(0 0 14px ${theme.accent})` }} />
        <circle cx={dx} cy={dy} r={16} fill="#fff" style={{ filter: `drop-shadow(0 0 18px ${theme.accent})` }} />
      </svg>
    </SafeBox>
  );
};

/** Whole-screen colour flash with one word: a rhythm break between scenes. */
export const Flash: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { theme } = useTheme();
  const wipe = interpolate(frame, [0, 8], [0, 1], { ...clamp, easing: EASE_OUT });
  return (
    <AbsoluteFill style={{ background: theme.accent, opacity: wipe, alignItems: 'center', justifyContent: 'center', paddingTop: SAFE_TOP - SAFE_BOTTOM }}>
      <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: fit(340, scene.text.length, 920, 0.7, 90), letterSpacing: -8, maxWidth: 940, color: '#05070C', transform: `scale(${0.8 + 0.2 * wipe})` }}>{scene.text}</div>
    </AbsoluteFill>
  );
};

export const Outro: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme } = useTheme();
  const s = spring({ frame: frame - 4, fps, config: { damping: 14, stiffness: 90 } });
  const longest = Math.max(1, ...scene.text.split(/\s+/).map((w) => w.length));
  const outroSize = fit(scene.text.length > 8 ? 170 : 230, longest, 900, 0.74, 70);
  return (
    <>
      <Burst delay={8} color={theme.accent} cy={SAFE_TOP + 560} />
      <SafeBox gap={26}>
        <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: outroSize, letterSpacing: -outroSize * 0.025, maxWidth: 940, lineHeight: 1.02, color: theme.text, textTransform: 'uppercase', transform: `scale(${0.7 + 0.3 * s})`, opacity: Math.min(1, s * 1.5), textShadow: `0 0 60px ${theme.accent}77` }}>{scene.text}</div>
        <Accent text={scene.accentText} size={120} delay={16} />
      </SafeBox>
    </>
  );
};


/** Real game footage (screenshot or trailer clip) in the channel look: blue/cyan grade, scan line, corner brackets, game tag and a callout. */
export const Footage: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme } = useTheme();
  const W = 920, H = 518;
  const enter = spring({ frame, fps, config: { damping: 200, mass: 0.9 } });
  const progress = Math.min(1, frame / Math.max(1, scene.durationInFrames));
  const zoom = interpolate(progress, [0, 1], [1.04, 1.14]);
  const panX = interpolate(progress, [0, 1], [-12, 12]);
  const sweep = ((frame / fps) % 2.4) / 2.4;
  const grade = 'grayscale(0.55) contrast(1.1) brightness(0.9) saturate(1.1)';
  const media: React.CSSProperties = { position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', filter: grade };
  const bracket = (pos: React.CSSProperties) => <div style={{ position: 'absolute', width: 38, height: 38, borderColor: theme.accent, borderStyle: 'solid', borderWidth: 0, filter: `drop-shadow(0 0 6px ${theme.accent})`, ...pos }} />;
  return (
    <SafeBox gap={36}>
      <div style={{ position: 'relative', width: W, height: H, borderRadius: 26, overflow: 'hidden', background: '#05070C', boxShadow: `inset 0 0 0 1px ${theme.accent}55, 0 30px 90px rgba(0,0,0,0.55), 0 0 60px ${BRAND_BLUE}44`, opacity: enter, transform: `translateY(${(1 - enter) * 50}px) scale(${0.96 + 0.04 * enter})` }}>
        {scene.mediaSrc && scene.mediaKind === 'video' ? (
          <Loop durationInFrames={Math.max(1, Math.round((scene.mediaSeconds ?? 3) * fps))}>
            <OffthreadVideo src={staticFile(scene.mediaSrc)} muted style={media} />
          </Loop>
        ) : scene.mediaSrc ? (
          <Img src={staticFile(scene.mediaSrc)} style={{ ...media, transform: `scale(${zoom}) translateX(${panX}px)` }} />
        ) : null}
        <AbsoluteFill style={{ background: `linear-gradient(160deg, ${BRAND_BLUE}66 0%, ${BRAND_BLUE}33 55%, ${theme.accent}33 100%)`, mixBlendMode: 'color' }} />
        <AbsoluteFill style={{ background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 48%, rgba(3,8,18,0.8) 100%)' }} />
        <AbsoluteFill style={{ opacity: 0.1, backgroundImage: 'linear-gradient(rgba(255,255,255,0.7) 1px, transparent 1px)', backgroundSize: '100% 6px' }} />
        <div style={{ position: 'absolute', left: 0, right: 0, top: `${sweep * 100}%`, height: 3, background: `linear-gradient(90deg, transparent, ${theme.accent}, transparent)`, opacity: 0.55 }} />
        {bracket({ top: 18, left: 18, borderTopWidth: 4, borderLeftWidth: 4 })}
        {bracket({ top: 18, right: 18, borderTopWidth: 4, borderRightWidth: 4 })}
        {bracket({ bottom: 18, left: 18, borderBottomWidth: 4, borderLeftWidth: 4 })}
        {bracket({ bottom: 18, right: 18, borderBottomWidth: 4, borderRightWidth: 4 })}
        {scene.credit && (
          <div style={{ position: 'absolute', left: 34, bottom: 30, padding: '8px 18px', borderRadius: 999, background: 'rgba(5,7,12,0.72)', border: `1px solid ${theme.accent}66`, fontFamily: MONO, fontSize: fit(24, scene.credit.length, 560, 0.62, 16), letterSpacing: 2, color: theme.accent, textTransform: 'uppercase', maxWidth: 640, whiteSpace: 'nowrap', overflow: 'hidden' }}>
            ● {scene.credit}
          </div>
        )}
      </div>
      <Words text={scene.text} size={86} delay={10} upper />
      <Accent text={scene.accentText} size={110} delay={18} />
    </SafeBox>
  );
};
