import React from 'react';
import { AbsoluteFill, Img, Loop, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { Accent, Burst, EASE_IO, EASE_OUT, Kicker, SafeBox, Words, clamp, fit, useTheme } from './primitives';
import { useLook } from './looks';
import { MONO, SANS } from './fonts';
import { BRAND_BLUE, MotionScene, SAFE_BOTTOM, SAFE_TOP } from './types';
import { VoteCards, voteOptions } from './polish';

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

/** A framed statement: the same fields as TextWithAccent (text + accentText), drawn inside a glass card with a quote mark and an accent bar. A visual change from the plain headlines for a key claim or the takeaway. */
export const Card: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const look = useLook();
  const pop = spring({ frame: frame - 3, fps, config: { damping: 15, stiffness: 140, mass: 0.8 } });
  const bar = interpolate(frame, [10, 34], [0, 1], { ...clamp, easing: EASE_OUT });
  const left = look.align === 'left';
  return (
    <SafeBox gap={30}>
      <Kicker text={scene.kicker} />
      <div style={{ position: 'relative', width: 936, padding: left ? '68px 56px 68px 76px' : '84px 56px 68px', borderRadius: 46, background: light ? 'rgba(255,255,255,0.86)' : 'rgba(10,22,48,0.62)', border: `2px solid ${theme.accent}55`, boxShadow: `0 40px 100px rgba(0,0,0,0.35), 0 0 60px ${theme.accent}22, inset 0 1px 0 rgba(255,255,255,0.12)`, opacity: Math.min(1, pop * 1.4), transform: `translateY(${(1 - Math.min(1, pop)) * 60}px) scale(${0.94 + 0.06 * Math.min(1, pop)})` }}>
        {left ? (
          <div style={{ position: 'absolute', left: 0, top: 44, bottom: 44, width: 10, borderRadius: 5, background: `linear-gradient(180deg, ${theme.accent}, ${theme.accent2 ?? theme.accent})`, transform: `scaleY(${bar})`, transformOrigin: '50% 0%' }} />
        ) : (
          <div style={{ position: 'absolute', left: '50%', top: -6, transform: 'translateX(-50%)', fontFamily: 'Georgia, serif', fontSize: 190, lineHeight: 1, color: theme.accent, textShadow: `0 0 40px ${theme.accent}88`, opacity: bar }}>&ldquo;</div>
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 14, alignItems: left ? 'flex-start' : 'center' }}>
          <Words text={scene.text} size={scene.text.split(' ').length > 3 ? 92 : 108} />
          <Accent text={scene.accentText} size={scene.text.split(' ').length > 3 ? 120 : 138} delay={12} />
        </div>
        {!left && <div style={{ margin: '30px auto 0', width: 180 * bar, height: 6, borderRadius: 3, background: `linear-gradient(90deg, transparent, ${theme.accent}, transparent)` }} />}
      </div>
    </SafeBox>
  );
};

export const Counter: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const target = scene.value ?? 100;
  const p = spring({ frame: frame - 10, fps, config: { damping: 200, mass: 1.6 }, durationInFrames: Math.max(30, scene.durationInFrames - 26) });
  const shown = Math.round(target * p);
  const digits = Math.max(1, Math.round(target).toLocaleString('en-US').length); // no zero padding: "0047 MB" read as a glitch
  const dots = 12;
  const numSize = fit(210, digits + (scene.unit ? scene.unit.length * 0.55 + 0.4 : 0), 900, 0.62, 80);
  return (
    <SafeBox gap={40}>
      <Kicker text={scene.kicker} />
      <Words text={scene.text} size={104} />
      <Accent text={scene.accentText} size={132} delay={10} />
      <div data-cursor="number" style={{ fontFamily: MONO, fontWeight: 500, fontSize: numSize, letterSpacing: 6, color: light ? '#0A1220' : theme.text, textShadow: light ? 'none' : `0 0 40px ${theme.accent}55`, marginTop: 10 }}>
        {shown.toLocaleString('en-US')}
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
            <div key={i} data-cursor="item" style={{ display: 'flex', alignItems: 'baseline', gap: 28, opacity: s, transform: `translateX(${(1 - s) * -70}px)`, filter: `blur(${(1 - s) * 10}px)` }}>
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
  // "KEY = meaning" lines (a label split into its parts) are drawn as key / value rows instead of typed code: the key is a pill, the meaning is plain text
  const pairs = lines.map((l) => l.match(/^(\S.{0,17}?)\s=\s+(\S.*)$/));
  if (lines.length >= 2 && pairs.every(Boolean)) {
    return (
      <SafeBox gap={52}>
        <div data-cursor="code" style={{ width: 920, borderRadius: 30, padding: '34px 38px', background: 'rgba(10,22,44,0.72)', border: `1px solid ${theme.accent}33`, boxShadow: `0 30px 90px rgba(0,0,0,0.5), 0 0 0 1px ${theme.accent}22`, opacity: panel, display: 'flex', flexDirection: 'column', gap: 18 }}>
          {pairs.map((m, i) => {
            const p = interpolate(frame, [10 + i * 9, 24 + i * 9], [0, 1], { ...clamp, easing: EASE_OUT });
            const key = m![1].trim();
            const val = m![2].trim();
            return (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 22, opacity: p, transform: `translateX(${(1 - p) * -60}px)` }}>
                <span style={{ flex: '0 0 auto', padding: '8px 22px', borderRadius: 16, background: theme.accent, color: '#05070C', fontFamily: MONO, fontWeight: 700, fontSize: fit(44, key.length, 330, 0.62, 28), letterSpacing: 0.5, boxShadow: `0 0 26px ${theme.accent}55` }}>{key}</span>
                <span style={{ color: theme.accent, fontFamily: MONO, fontSize: 38, opacity: 0.8 }}>=</span>
                <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: fit(46, val.length, 470, 0.5, 28), lineHeight: 1.1, color: '#FFFFFF' }}>{val}</span>
              </div>
            );
          })}
        </div>
        <Words text={scene.text} size={92} delay={18} />
        <Accent text={scene.accentText} size={116} delay={26} />
      </SafeBox>
    );
  }
  return (
    <SafeBox gap={52}>
      <div data-cursor="code" style={{ width: 920, borderRadius: 30, padding: '30px 38px 38px', background: 'rgba(10,22,44,0.72)', border: `1px solid ${theme.accent}33`, boxShadow: `0 30px 90px rgba(0,0,0,0.5), 0 0 0 1px ${theme.accent}22`, opacity: panel, transform: `translateY(${(1 - panel) * 40}px) scale(${0.97 + 0.03 * panel})`, textAlign: 'left' }}>
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
      <div style={{ position: 'relative', width: 860, marginTop: 24 }}>
        <div data-cursor="bar" style={{ width: '100%', height: 22, borderRadius: 11, background: light ? 'rgba(0,0,0,0.1)' : 'rgba(255,255,255,0.1)', overflow: 'hidden' }}>
          <div style={{ width: `${target * p}%`, height: '100%', borderRadius: 11, background: `linear-gradient(90deg, ${theme.accent2 ?? BRAND_BLUE}, ${theme.accent})`, boxShadow: `0 0 28px ${theme.accent}` }} />
        </div>
        {scene.cursor === 'drag' && (
          // the knob the pointer grabs: it sits at the end of the fill, so pulling it is what makes the bar grow
          <div data-cursor="fill" style={{ position: 'absolute', left: `${target * p}%`, top: 11, width: 44, height: 44, marginLeft: -22, marginTop: -22, borderRadius: 22, background: '#FFFFFF', border: `5px solid ${theme.accent}`, boxShadow: `0 0 26px ${theme.accent}, 0 6px 14px rgba(0,0,0,0.5)`, opacity: Math.min(1, p * 8) }} />
        )}
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
  const words = scene.text.split(/\s+/).filter(Boolean);
  const flashSize = fit(words.length > 1 ? 300 : 340, Math.max(...words.map((w) => w.length), Math.ceil(scene.text.length / 2)), 920, 0.7, 90); // long phrases wrap on two lines instead of shrinking to one tiny row
  return (
    <AbsoluteFill style={{ background: theme.accent, opacity: wipe, alignItems: 'center', justifyContent: 'center', paddingTop: SAFE_TOP - SAFE_BOTTOM }}>
      <div style={{ fontFamily: SANS, fontWeight: 900, fontSize: flashSize, letterSpacing: -flashSize * 0.03, wordSpacing: flashSize * 0.12, lineHeight: 0.98, textAlign: 'center', maxWidth: 940, color: '#05070C', transform: `scale(${0.8 + 0.2 * wipe})` }}>{scene.text}</div>
    </AbsoluteFill>
  );
};

export const Outro: React.FC<P> = ({ scene }) => {
  const vote = voteOptions(scene);
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
        <Accent text={scene.accentText} size={vote ? 96 : 120} delay={16} />
        {vote && <VoteCards a={vote[0]} b={vote[1]} delay={26} />}
      </SafeBox>
    </>
  );
};


/** Real game footage (screenshot or trailer clip) shown as it is, in a rounded card over a blurred copy of itself, with a game tag. */
export const Footage: React.FC<P> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme } = useTheme();
  const W = 920, H = 518;
  const enter = spring({ frame, fps, config: { damping: 200, mass: 0.9 } });
  const progress = Math.min(1, frame / Math.max(1, scene.durationInFrames));
  const zoom = interpolate(progress, [0, 1], [1.04, 1.14]);
  const panX = interpolate(progress, [0, 1], [-12, 12]);
  const media: React.CSSProperties = { position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover' }; // the footage is shown exactly as it is: no grade, tint, scan lines or vignette
  // the same picture, blurred and darkened, fills the whole frame behind the 16:9 card: no empty bars above and below it
  const fill: React.CSSProperties = { position: 'absolute', inset: -60, width: 'calc(100% + 120px)', height: 'calc(100% + 120px)', objectFit: 'cover', filter: 'blur(34px) brightness(0.62)', transform: `scale(${1.08 + 0.05 * progress})` };
  return (
    <>
      <AbsoluteFill style={{ overflow: 'hidden', opacity: enter }}>
        {scene.mediaSrc && scene.mediaKind === 'video' ? (
          <Loop durationInFrames={Math.max(1, Math.round((scene.mediaSeconds ?? 3) * fps))}>
            <OffthreadVideo src={staticFile(scene.mediaSrc)} muted style={fill} />
          </Loop>
        ) : scene.mediaSrc ? (
          <Img src={staticFile(scene.mediaSrc)} style={fill} />
        ) : null}
        <AbsoluteFill style={{ background: `linear-gradient(180deg, rgba(5,7,12,0.4) 0%, rgba(5,7,12,0.05) 40%, rgba(5,7,12,0.45) 100%)` }} />
      </AbsoluteFill>
    <SafeBox gap={36}>
      <div style={{ position: 'relative', width: W, height: H, borderRadius: 26, overflow: 'hidden', background: '#05070C', boxShadow: '0 30px 90px rgba(0,0,0,0.55)', opacity: enter, transform: `translateY(${(1 - enter) * 50}px) scale(${0.96 + 0.04 * enter})` }}>
        {scene.mediaSrc && scene.mediaKind === 'video' ? (
          <Loop durationInFrames={Math.max(1, Math.round((scene.mediaSeconds ?? 3) * fps))}>
            <OffthreadVideo src={staticFile(scene.mediaSrc)} muted style={media} />
          </Loop>
        ) : scene.mediaSrc ? (
          <Img src={staticFile(scene.mediaSrc)} style={{ ...media, transform: `scale(${zoom}) translateX(${panX}px)` }} />
        ) : null}
        {scene.credit && (
          <div style={{ position: 'absolute', left: 34, bottom: 30, padding: '8px 18px', borderRadius: 999, background: 'rgba(5,7,12,0.72)', border: `1px solid ${theme.accent}66`, fontFamily: MONO, fontSize: fit(24, scene.credit.length, 560, 0.62, 16), letterSpacing: 2, color: theme.accent, textTransform: 'uppercase', maxWidth: 640, whiteSpace: 'nowrap', overflow: 'hidden' }}>
            ● {scene.credit}
          </div>
        )}
      </div>
      <Words text={scene.text} size={86} delay={10} upper />
      <Accent text={scene.accentText} size={110} delay={18} />
    </SafeBox>
    </>
  );
};
