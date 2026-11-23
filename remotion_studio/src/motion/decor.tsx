import React from 'react';
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { MONO } from './fonts';
import { CAPTION_SPACE, useLook, useSceneCtx } from './looks';
import { EASE_OUT, clamp, useTheme } from './primitives';
import { STAGE_SCENES } from './visuals';
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
  if (look.decor === 'bars') {
    // an equalizer in the empty lower-right corner
    return (
      <AbsoluteFill style={{ pointerEvents: 'none', opacity: p }}>
        {Array.from({ length: 14 }).map((_, i) => {
          const h = 40 + (0.5 + 0.5 * Math.sin(frame / 6 + i * 0.8) * Math.cos(frame / 13 + i * 0.5)) * 210;
          return <div key={i} style={{ position: 'absolute', left: 560 + i * 34, bottom: bottom - 10, width: 20, height: h, borderRadius: 8, background: i % 3 ? theme.accent : theme.accent2 ?? theme.accent, opacity: 0.24 }} />;
        })}
      </AbsoluteFill>
    );
  }
  if (look.decor === 'arcs') {
    // quarter arcs growing out of the lower-left corner, slowly turning
    return (
      <AbsoluteFill style={{ pointerEvents: 'none', opacity: p }}>
        <svg width={1080} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
          {[170, 290, 410, 530].map((r, i) => (
            <path key={r} d={`M ${-10} ${HEIGHT - bottom - r} A ${r} ${r} 0 0 1 ${r - 10} ${HEIGHT - bottom}`} fill="none" stroke={i % 2 ? theme.accent2 ?? theme.accent : theme.accent} strokeWidth={5 - i} opacity={0.34 - i * 0.06} strokeDasharray={`${40 + i * 30} ${24}`} strokeDashoffset={-frame * (1 + i * 0.6)} />
          ))}
        </svg>
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
  const { captionSpace } = useSceneCtx();
  if (!scene.callout || scene.calloutCue == null) return null;
  const at = Math.round(scene.calloutCue * fps);
  const f = frame - at;
  if (f < -2 || f > 84) return null;
  const pop = spring({ frame: f, fps, config: { damping: 11, stiffness: 190, mass: 0.7 } });
  const fade = interpolate(f, [66, 84], [1, 0], clamp);
  const left = look.align === 'left';
  // over a stage the tag is an annotation: a thin leader line runs from it up to a pulsing ring on the visual, as in a magnified illustration
  const staged = STAGE_SCENES.has(scene.type);
  const tagTop = HEIGHT - SAFE_BOTTOM - captionSpace - 118;
  const tagX = left ? 760 : 540;
  const ringX = left ? 560 : 540 + (scene.durationInFrames % 2 ? 170 : -170);
  const ringY = tagTop - 250;
  const draw = interpolate(f, [4, 22], [0, 1], { ...clamp, easing: EASE_OUT });
  const ringPulse = 1 + 0.18 * Math.sin(f / 4);
  const lineLen = Math.hypot(tagX - ringX, tagTop - ringY - 34);
  return (
    <>
    {staged && (
      <svg width={1080} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0, pointerEvents: 'none', opacity: fade }}>
        <line x1={ringX} y1={ringY + 30} x2={tagX} y2={tagTop} stroke={theme.accent} strokeWidth={3} strokeLinecap="round" strokeDasharray={lineLen} strokeDashoffset={lineLen * (1 - draw)} style={{ filter: `drop-shadow(0 0 6px ${theme.accent})` }} />
        <circle cx={ringX} cy={ringY} r={26 * ringPulse} fill="none" stroke={theme.accent} strokeWidth={4} opacity={draw} style={{ filter: `drop-shadow(0 0 10px ${theme.accent})` }} />
        <circle cx={ringX} cy={ringY} r={7} fill={theme.accent} opacity={draw} />
      </svg>
    )}
    <div style={{ position: 'absolute', ...(STAGE_SCENES.has(scene.type) ? { top: HEIGHT - SAFE_BOTTOM - captionSpace - 118 } : { top: SAFE_TOP + 96 }), right: left ? 64 : undefined, left: left ? undefined : '50%', transform: `${left ? '' : 'translateX(-50%) '}translateY(${(1 - Math.min(1, pop)) * -26}px) scale(${0.7 + 0.3 * pop})`, opacity: Math.min(1, pop * 1.6) * fade, display: 'flex', alignItems: 'center', gap: 14, padding: '12px 28px', borderRadius: 999, background: light ? 'rgba(255,255,255,0.92)' : 'rgba(6,14,36,0.78)', border: `2px solid ${theme.accent}`, boxShadow: `0 0 34px ${theme.accent}66`, fontFamily: MONO, fontWeight: 500, fontSize: 52, letterSpacing: 1, color: light ? '#0A1220' : '#FFFFFF', whiteSpace: 'nowrap' }}>
      <span style={{ color: theme.accent, fontSize: 38 }}>▲</span>
      {scene.callout}
    </div>
    </>
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
