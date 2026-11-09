import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { MONO } from './fonts';
import { CAPTION_SPACE, useLook, useSceneCtx } from './looks';
import { EASE_OUT, clamp, useTheme } from './primitives';
import { HEIGHT, MotionScene, SAFE_BOTTOM, SAFE_TOP } from './types';

/** Scenes whose layout leaves the lower part of the frame empty: the look's decor fills it. */
const DECOR_SCENES = new Set(['bigText', 'textWithAccent', 'counter', 'list', 'progressBar', 'outro', 'curve']);

/** A design element of the look behind the text of the scene (a giant outlined scene number, concentric rings, a dimension line). It fills the empty lower part of text scenes. */
export const Decor: React.FC<{ scene: MotionScene; index: number; total: number }> = ({ scene, index, total }) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const { theme, light } = useTheme();
  const { captionSpace } = useSceneCtx();
  if (look.decor === 'none' || !DECOR_SCENES.has(scene.type)) return null;
  const p = interpolate(frame, [4, 26], [0, 1], { ...clamp, easing: EASE_OUT });
  const bottom = SAFE_BOTTOM + captionSpace + 24;
  const n = String(index + 1).padStart(2, '0');
  if (look.decor === 'number') {
    return (
      <AbsoluteFill style={{ pointerEvents: 'none' }}>
        <div style={{ position: 'absolute', right: 36 - (1 - p) * 60, bottom: bottom - 40, fontFamily: look.sans, fontWeight: 900, fontSize: 470, lineHeight: 0.78, letterSpacing: -20, color: 'transparent', WebkitTextStroke: `4px ${theme.accent}`, opacity: 0.2 * p }}>{n}</div>
      </AbsoluteFill>
    );
  }
  if (look.decor === 'ring') {
    return (
      <AbsoluteFill style={{ pointerEvents: 'none' }}>
        {[190, 310, 440].map((r, i) => (
          <div key={r} style={{ position: 'absolute', left: 900 - r, top: HEIGHT - bottom - 240 - r, width: r * 2, height: r * 2, borderRadius: '50%', border: `${3 - i * 0.6}px solid ${i === 0 ? theme.accent : theme.accent2 ?? theme.accent}`, opacity: (0.34 - i * 0.1) * p, transform: `scale(${0.85 + 0.15 * p + Math.sin((frame + i * 30) / 40) * 0.015})` }} />
        ))}
      </AbsoluteFill>
    );
  }
  // dimension: a technical drawing's dimension line with the scene counter
  const y = HEIGHT - bottom - 40;
  const c = light ? 'rgba(10,18,32,0.55)' : 'rgba(255,255,255,0.55)';
  return (
    <AbsoluteFill style={{ pointerEvents: 'none', opacity: p }}>
      <div style={{ position: 'absolute', left: 64, right: 64, top: y, height: 2, background: c }} />
      {[64, 1016].map((x) => <div key={x} style={{ position: 'absolute', left: x - 1, top: y - 16, width: 2, height: 34, background: c }} />)}
      <div style={{ position: 'absolute', left: 0, right: 0, top: y - 40, textAlign: 'center', fontFamily: MONO, fontSize: 26, letterSpacing: 6, color: c }}>
        <span style={{ background: look.light ? '#EAF2FF' : theme.background, padding: '0 20px' }}>{n} / {String(total).padStart(2, '0')}</span>
      </div>
    </AbsoluteFill>
  );
};

/** A short tag (a figure or a key term) that pops up in the corner mid-scene, as the narrator says it: a second visual beat inside a long scene. */
export const Callout: React.FC<{ scene: MotionScene }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const look = useLook();
  if (!scene.callout || scene.calloutCue == null) return null;
  const at = Math.round(scene.calloutCue * fps);
  const f = frame - at;
  if (f < -2 || f > 84) return null;
  const pop = spring({ frame: f, fps, config: { damping: 11, stiffness: 190, mass: 0.7 } });
  const fade = interpolate(f, [66, 84], [1, 0], clamp);
  const left = look.align === 'left';
  return (
    <div style={{ position: 'absolute', top: SAFE_TOP + 96, right: left ? 64 : undefined, left: left ? undefined : '50%', transform: `${left ? '' : 'translateX(-50%) '}translateY(${(1 - Math.min(1, pop)) * -26}px) scale(${0.7 + 0.3 * pop})`, opacity: Math.min(1, pop * 1.6) * fade, display: 'flex', alignItems: 'center', gap: 14, padding: '12px 28px', borderRadius: 999, background: light ? 'rgba(255,255,255,0.92)' : 'rgba(6,14,36,0.78)', border: `2px solid ${theme.accent}`, boxShadow: `0 0 34px ${theme.accent}66`, fontFamily: MONO, fontWeight: 500, fontSize: 52, letterSpacing: 1, color: light ? '#0A1220' : '#FFFFFF', whiteSpace: 'nowrap' }}>
      <span style={{ color: theme.accent, fontSize: 38 }}>▲</span>
      {scene.callout}
    </div>
  );
};

/** The midpoint "re-hook": a flash and a wide ring as the scene lands, so the middle of the video gets a second jolt. */
export const Shock: React.FC = () => {
  const frame = useCurrentFrame();
  const { theme } = useTheme();
  if (frame > 20) return null;
  const p = interpolate(frame, [0, 18], [0, 1], { ...clamp, easing: EASE_OUT });
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <AbsoluteFill style={{ background: `radial-gradient(circle at 50% 46%, ${theme.accent}${Math.round((1 - p) * 110).toString(16).padStart(2, '0')} 0%, transparent 62%)` }} />
      <div style={{ position: 'absolute', left: 540 - p * 900, top: 880 - p * 900, width: p * 1800, height: p * 1800, borderRadius: '50%', border: `${14 * (1 - p) + 2}px solid ${theme.accent}`, opacity: 1 - p * 0.9 }} />
    </AbsoluteFill>
  );
};
