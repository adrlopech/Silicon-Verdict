import React from 'react';
import { AbsoluteFill, interpolate, random, useCurrentFrame } from 'remotion';
import { EASE_OUT, clamp, useTheme } from './primitives';
import { BRAND_BLUE } from './types';

/** Rising dust + a few bigger glowing orbs, parallaxed by depth. Global, deterministic, runs under every scene. */
export const Particles: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      {Array.from({ length: 46 }).map((_, i) => {
        const depth = 0.3 + random(`d${i}`) * 1.2;
        const speed = 0.5 + depth * 1.6;
        const y = 1920 - (((frame * speed + random(`y${i}`) * 2200) % 2200) - 140);
        const x = random(`x${i}`) * 1080 + Math.sin(frame / (40 + i) + i) * 26 * depth;
        const size = (i % 9 === 0 ? 16 : 3.5) * depth;
        const c = i % 4 === 0 ? BRAND_BLUE : accent;
        return <div key={i} style={{ position: 'absolute', left: x, top: y, width: size, height: size, borderRadius: '50%', background: c, opacity: (light ? 0.18 : 0.32) * Math.min(1, depth), boxShadow: light ? 'none' : `0 0 ${size * 3}px ${c}`, filter: size > 12 ? 'blur(2px)' : 'none' }} />;
      })}
    </AbsoluteFill>
  );
};

/** A perspective grid that scrolls toward the camera at the bottom of the frame: constant forward motion. */
export const Grid: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const off = (frame * 3.2) % 120;
  const c = light ? 'rgba(10,18,32,0.07)' : `${accent}44`;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', left: -700, right: -700, bottom: -80, height: 900, transform: 'perspective(620px) rotateX(64deg)', transformOrigin: '50% 100%', backgroundImage: `linear-gradient(${c} 2px, transparent 2px), linear-gradient(90deg, ${c} 2px, transparent 2px)`, backgroundSize: '120px 120px', backgroundPosition: `0 ${off}px`, WebkitMaskImage: 'linear-gradient(to top, #000 0%, transparent 85%)', opacity: 0.9 }} />
    </AbsoluteFill>
  );
};

/** Expanding ring + a short burst of speed lines the moment a scene lands: a visible beat on every cut. */
export const Impact: React.FC<{ seed: number }> = ({ seed }) => {
  const frame = useCurrentFrame();
  const { theme, light } = useTheme();
  if (frame > 34) return null;
  const p = interpolate(frame, [0, 30], [0, 1], { ...clamp, easing: EASE_OUT });
  const cy = 860;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <div style={{ position: 'absolute', left: 540 - p * 700, top: cy - p * 700, width: p * 1400, height: p * 1400, borderRadius: '50%', border: `${6 * (1 - p) + 1}px solid ${light ? '#0A1220' : theme.accent}`, opacity: (1 - p) * 0.7, boxShadow: light ? 'none' : `0 0 40px ${theme.accent}88, inset 0 0 40px ${theme.accent}44` }} />
      {Array.from({ length: 14 }).map((_, i) => {
        const a = (i / 14) * Math.PI * 2 + random(`l${seed}${i}`) * 0.3;
        const r0 = 160 + p * 420;
        const r1 = r0 + 90 + random(`m${seed}${i}`) * 220 * (1 - p * 0.4);
        return <div key={i} style={{ position: 'absolute', left: 540 + Math.cos(a) * r0, top: cy + Math.sin(a) * r0, width: r1 - r0, height: 4, transformOrigin: '0 50%', transform: `rotate(${a}rad)`, background: `linear-gradient(90deg, ${light ? '#0A1220' : theme.accent}, transparent)`, opacity: (1 - p) * 0.8 }} />;
      })}
    </AbsoluteFill>
  );
};
