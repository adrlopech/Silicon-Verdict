import React, { createContext, useContext } from 'react';
import { AbsoluteFill, Easing, interpolate, random, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { MONO, SANS, SERIF } from './fonts';
import { LookCtx, useLook, useSceneCtx } from './looks';
import { BRAND_BLUE, MotionTheme, SAFE_BOTTOM, SAFE_TOP } from './types';

export const ThemeCtx = createContext<{ theme: MotionTheme; light: boolean }>({ theme: { accent: '#00F0FF', background: '#05070C', text: '#FFF' }, light: false });
export const useTheme = () => useContext(ThemeCtx);
export { LookCtx };

/** Largest font size (<= size) at which `chars` characters still fit in `maxWidth` px (avg glyph width = factor * size). */
export const fit = (size: number, chars: number, maxWidth = 920, factor = 0.6, min = 40) => Math.max(min, Math.min(size, Math.floor(maxWidth / (Math.max(1, chars) * factor))));

export const EASE_OUT = Easing.bezier(0.16, 1, 0.3, 1); // expo-out style: fast start, long soft landing
export const EASE_IO = Easing.bezier(0.65, 0, 0.35, 1);
export const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;

/** The shared background of the video; its style comes from the look (glow, aurora, scanlines, stripes, dots, blueprint, mono). Slow and continuous. */
export const Background: React.FC<{ light: boolean; background: string; accent: string }> = ({ light, background, accent }) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const { theme } = useTheme();
  const a2 = theme.accent2 ?? BRAND_BLUE;
  const drift = Math.sin(frame / 55) * 70;
  const sweep = interpolate(frame % 120, [0, 120], [-20, 120]);
  const base = light && !look.light ? '#EAF1F8' : background;
  const vignette = <AbsoluteFill style={{ background: `radial-gradient(ellipse 75% 70% at 50% 50%, transparent 52%, ${light ? 'rgba(40,70,110,0.20)' : 'rgba(0,0,0,0.72)'} 100%)` }} />;
  if (look.bg === 'aurora') {
    const blob = (x: number, y: number, r: number, c: string, o: string) => <AbsoluteFill style={{ background: `radial-gradient(circle ${r}px at ${x}% ${y}%, ${c}${o} 0%, transparent 70%)` }} />;
    return (
      <AbsoluteFill style={{ background: base }}>
        {blob(25 + Math.sin(frame / 90) * 18, 30 + Math.cos(frame / 110) * 12, 760, accent, '40')}
        {blob(78 + Math.cos(frame / 80) * 14, 62 + Math.sin(frame / 100) * 14, 900, a2, '66')}
        {blob(50 + Math.sin(frame / 130) * 22, 92, 720, a2, '55')}
        {vignette}
      </AbsoluteFill>
    );
  }
  if (look.bg === 'mesh') {
    // a saturated cobalt gradient mesh: big soft blobs of blue drifting over a deep-to-bright diagonal, with a faint film grain
    const blob = (x: number, y: number, r: number, c: string, o: string) => <AbsoluteFill style={{ background: `radial-gradient(circle ${r}px at ${x}% ${y}%, ${c}${o} 0%, transparent 70%)` }} />;
    const grain = `url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/></filter><rect width='100%' height='100%' filter='url(%23n)' opacity='0.5'/></svg>")`;
    return (
      <AbsoluteFill style={{ background: `linear-gradient(165deg, #0E3FE0 0%, ${base} 48%, #030A2E 100%)` }}>
        {blob(20 + Math.sin(frame / 95) * 16, 22 + Math.cos(frame / 120) * 10, 820, '#38A8FF', '66')}
        {blob(84 + Math.cos(frame / 85) * 10, 48 + Math.sin(frame / 105) * 14, 760, a2, '77')}
        {blob(46 + Math.sin(frame / 140) * 20, 96, 880, '#1A3BFF', '88')}
        <AbsoluteFill style={{ background: 'linear-gradient(115deg, transparent 38%, rgba(255,255,255,0.07) 50%, transparent 62%)', transform: `translateX(${Math.sin(frame / 160) * 90}px)` }} />
        <AbsoluteFill style={{ backgroundImage: grain, opacity: 0.09, mixBlendMode: 'overlay' }} />
        {vignette}
      </AbsoluteFill>
    );
  }
  if (look.bg === 'orbs') {
    // frosted glass spheres drifting over midnight blue
    const orb = (x: number, y: number, d: number, i: number) => (
      <div key={i} style={{ position: 'absolute', left: `${x}%`, top: `${y}%`, width: d, height: d, marginLeft: -d / 2, marginTop: -d / 2, borderRadius: '50%', background: `radial-gradient(circle at 32% 28%, ${accent}55 0%, ${a2}33 38%, transparent 72%)`, border: '1.5px solid rgba(255,255,255,0.14)', boxShadow: `inset 0 0 ${d * 0.16}px rgba(255,255,255,0.10), 0 0 ${d * 0.3}px ${a2}33`, backdropFilter: 'blur(2px)' }} />
    );
    return (
      <AbsoluteFill style={{ background: `linear-gradient(180deg, ${base}, #071433)` }}>
        <AbsoluteFill style={{ background: `radial-gradient(ellipse 80% 30% at 50% 0%, ${accent}22 0%, transparent 70%)` }} />
        {orb(18 + Math.sin(frame / 110) * 8, 24 + Math.cos(frame / 90) * 6, 520, 0)}
        {orb(86 + Math.cos(frame / 100) * 7, 48 + Math.sin(frame / 120) * 8, 380, 1)}
        {orb(30 + Math.cos(frame / 95) * 9, 78 + Math.sin(frame / 105) * 6, 640, 2)}
        {orb(78 + Math.sin(frame / 130) * 6, 92 + Math.cos(frame / 80) * 4, 300, 3)}
        {vignette}
      </AbsoluteFill>
    );
  }
  if (look.bg === 'dots') {
    const dot = light ? 'rgba(10,18,32,0.14)' : `${accent}33`;
    return (
      <AbsoluteFill style={{ background: base }}>
        <AbsoluteFill style={{ backgroundImage: `radial-gradient(circle, ${dot} 2.4px, transparent 2.6px)`, backgroundSize: '44px 44px', backgroundPosition: `${(frame * 0.35) % 44}px ${(frame * 0.2) % 44}px` }} />
        <AbsoluteFill style={{ background: `radial-gradient(ellipse 70% 40% at 50% 100%, ${a2}${light ? '22' : '44'} 0%, transparent 70%)` }} />
        {vignette}
      </AbsoluteFill>
    );
  }
  if (look.bg === 'blueprint') {
    return (
      <AbsoluteFill style={{ background: `linear-gradient(160deg, ${base}, #06193F)` }}>
        <AbsoluteFill style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.07) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.07) 1px, transparent 1px)', backgroundSize: '27px 27px' }} />
        <AbsoluteFill style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.16) 2px, transparent 2px), linear-gradient(90deg, rgba(255,255,255,0.16) 2px, transparent 2px)', backgroundSize: '135px 135px', backgroundPosition: `0 ${(frame * 0.3) % 135}px` }} />
        <AbsoluteFill style={{ background: `radial-gradient(ellipse 70% 40% at 50% 100%, ${a2}66 0%, transparent 70%)` }} />
        {vignette}
      </AbsoluteFill>
    );
  }
  if (look.bg === 'mono') {
    return (
      <AbsoluteFill style={{ background: base }}>
        <AbsoluteFill style={{ background: `radial-gradient(ellipse 60% 35% at 50% 8%, rgba(255,255,255,0.10) 0%, transparent 70%)` }} />
        <AbsoluteFill style={{ background: `radial-gradient(ellipse 80% 30% at 50% 100%, rgba(143,168,192,0.14) 0%, transparent 70%)` }} />
        {vignette}
      </AbsoluteFill>
    );
  }
  return (
    <AbsoluteFill style={{ background: base }}>
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 80% 42% at ${50 + drift / 14}% 66%, ${a2}${light ? '30' : '66'} 0%, ${a2}${light ? '14' : '30'} 45%, transparent 72%)` }} />
      <AbsoluteFill style={{ background: `radial-gradient(ellipse 70% 30% at 50% 0%, ${a2}${light ? '14' : '26'} 0%, transparent 75%)` }} />
      {!light && <div style={{ position: 'absolute', top: 1180, left: `${sweep}%`, width: 520, height: 3, background: `linear-gradient(90deg, transparent, ${accent}, transparent)`, opacity: 0.35, filter: 'blur(1.5px)' }} />}
      {vignette}
    </AbsoluteFill>
  );
};

/** HUD of the video: label, timecode and a progress indicator, drawn in the look's style (mono line, story segments, corner brackets, ruler ticks). */
export const Hud: React.FC<{ index: number; total: number; label: string; segments: { start: number; len: number }[] }> = ({ index, total, label, segments }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const look = useLook();
  const s = Math.floor(frame / fps);
  const tc = `00:${String(s).padStart(2, '0')}:${String(frame % fps).padStart(2, '0')}`;
  const color = light ? 'rgba(10,18,32,0.5)' : 'rgba(255,255,255,0.42)';
  const row: React.CSSProperties = { position: 'absolute', top: SAFE_TOP + 16, fontFamily: MONO, fontSize: 24, letterSpacing: 3, color, textTransform: 'uppercase' };
  const name = label.length > 24 ? label.slice(0, 23) + '…' : label;
  const end = segments.length ? segments[segments.length - 1].start + segments[segments.length - 1].len : 1;
  const done = Math.min(1, frame / end);
  const track = light ? 'rgba(10,18,32,0.16)' : 'rgba(255,255,255,0.2)';
  if (look.hud === 'story') {
    return (
      <>
        <div style={{ position: 'absolute', left: 64, right: 64, top: SAFE_TOP + 8, display: 'flex', gap: 8 }}>
          {segments.map((seg, i) => (
            <div key={i} style={{ flex: seg.len, height: 7, borderRadius: 4, background: track, overflow: 'hidden' }}>
              <div style={{ width: `${Math.max(0, Math.min(1, (frame - seg.start) / seg.len)) * 100}%`, height: '100%', background: theme.accent, boxShadow: `0 0 12px ${theme.accent}99` }} />
            </div>
          ))}
        </div>
        <div style={{ ...row, left: 64, top: SAFE_TOP + 34 }}><span style={{ color: theme.accent }}>●</span> {name}</div>
      </>
    );
  }
  if (look.hud === 'brackets') {
    const arm = (pos: React.CSSProperties) => <div style={{ position: 'absolute', width: 54, height: 54, borderColor: theme.accent, borderStyle: 'solid', borderWidth: 0, opacity: 0.8, ...pos }} />;
    return (
      <>
        {arm({ left: 40, top: SAFE_TOP - 6, borderLeftWidth: 4, borderTopWidth: 4 })}
        {arm({ right: 40, top: SAFE_TOP - 6, borderRightWidth: 4, borderTopWidth: 4 })}
        {arm({ left: 40, bottom: 330, borderLeftWidth: 4, borderBottomWidth: 4 })}
        {arm({ right: 40, bottom: 330, borderRightWidth: 4, borderBottomWidth: 4 })}
        <div style={{ ...row, left: 96 }}>[{String(index + 1).padStart(2, '0')}/{String(total).padStart(2, '0')}] {name}</div>
        <div style={{ ...row, right: 96 }}>{tc}</div>
        <div style={{ position: 'absolute', left: 96, right: 96, top: SAFE_TOP + 60, height: 3, background: track }}><div style={{ width: `${done * 100}%`, height: '100%', background: theme.accent }} /></div>
      </>
    );
  }
  if (look.hud === 'ticks') {
    return (
      <>
        <div style={{ ...row, left: 64 }}>FIG. {String(index + 1).padStart(2, '0')} · {name}</div>
        <div style={{ position: 'absolute', left: 64, right: 64, top: SAFE_TOP + 58, height: 22, backgroundImage: `repeating-linear-gradient(90deg, ${color} 0 2px, transparent 2px 14px)`, maskImage: 'linear-gradient(180deg, #000 50%, transparent 50%)', WebkitMaskImage: 'linear-gradient(180deg, #000 50%, transparent 50%)' }} />
        <div style={{ position: 'absolute', left: 64 + done * 952 - 2, top: SAFE_TOP + 52, width: 4, height: 34, background: theme.accent, boxShadow: `0 0 12px ${theme.accent}` }} />
      </>
    );
  }
  return (
    <>
      <div style={{ ...row, left: 64 }}>
        <span style={{ color: theme.accent }}>●</span> SC {String(index + 1).padStart(2, '0')}/{String(total).padStart(2, '0')} · {name}
      </div>
      <div style={{ ...row, right: 64 }}>{tc}</div>
      <div style={{ position: 'absolute', left: 64, right: 64, top: SAFE_TOP + 56, height: 3, background: track }}><div style={{ width: `${done * 100}%`, height: '100%', background: theme.accent, boxShadow: `0 0 10px ${theme.accent}88` }} /></div>
    </>
  );
};

/** Content box that respects the Shorts/TikTok safe zones and centres its children. */
export const SafeBox: React.FC<{ children: React.ReactNode; gap?: number }> = ({ children, gap = 28 }) => {
  const look = useLook();
  const { captionSpace } = useSceneCtx(); // the caption strip takes room from the bottom of the scene when it is shown
  const left = look.align === 'left';
  return (
    <div style={{ position: 'absolute', left: 64, right: 64, top: SAFE_TOP + 130, bottom: SAFE_BOTTOM + captionSpace, display: 'flex', flexDirection: 'column', alignItems: left ? 'flex-start' : 'center', justifyContent: 'center', gap, textAlign: left ? 'left' : 'center' }}>
      {children}
    </div>
  );
};

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
export const Words: React.FC<{ text: string; size: number; delay?: number; stagger?: number; weight?: number; color?: string; upper?: boolean }> = ({ text, size, delay = 0, stagger = 4, weight = 900, color, upper: upperProp }) => {
  const look = useLook();
  const upper = upperProp ?? look.upper;
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const words = (upper ? text.toUpperCase() : text).split(/\s+/).filter(Boolean);
  const longest = Math.max(1, ...words.map((w) => w.length));
  size = fit(size * look.scale, longest, 900, upper ? 0.74 : 0.64, 36); // a long word must never overflow the 1080 px frame
  const lines = Math.ceil(words.join(' ').length / Math.max(6, Math.floor(900 / (size * 0.5))));
  if (lines > 3) size = Math.max(36, Math.floor(size * 0.82)); // very long lines shrink instead of growing taller than the safe area
  return (
    <div data-cursor="text" style={{ display: 'flex', flexWrap: 'wrap', justifyContent: look.align === 'left' ? 'flex-start' : 'center', columnGap: size * 0.28, rowGap: size * 0.06, fontFamily: look.sans, fontWeight: weight, fontSize: size, lineHeight: 1.04, letterSpacing: -size * 0.025, color: color ?? (light ? '#0A1220' : theme.text) }}>
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
  const look = useLook();
  const { scene } = useSceneCtx();
  if (!text) return null;
  const cue = scene?.accentCue != null ? Math.round(scene.accentCue * fps) : null;
  const pulse = cue != null ? interpolate(frame, [cue, cue + 5, cue + 16], [0, 1, 0], clamp) : 0; // the accent phrase pops as the narrator says it
  size = fit(size * look.scale, text.length, 900, 0.5, 44);
  const raw = spring({ frame: frame - delay, fps, config: { damping: 10, stiffness: 130, mass: 0.9 } });
  const s = Math.min(1, raw);
  return (
    <div data-cursor="accent" style={{ maxWidth: 940, fontFamily: SERIF, fontStyle: 'italic', fontWeight: 400, fontSize: size, lineHeight: 1.0, color: theme.accent, opacity: s, transformOrigin: look.align === 'left' ? '0% 50%' : '50% 50%', transform: `translateY(${(1 - raw) * size * 0.5}px) scale(${(0.6 + 0.4 * raw) * (1 + 0.14 * pulse)}) rotate(${(1 - raw) * -5}deg)`, filter: `blur(${(1 - s) * 10}px)`, textShadow: light ? 'none' : `0 0 ${size * (0.35 + pulse * 0.5)}px ${theme.accent}${pulse > 0.05 ? 'CC' : '66'}` }}>
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
