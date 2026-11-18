import React from 'react';
import { AbsoluteFill, interpolate, random, useCurrentFrame } from 'remotion';
import { ICONS, pickIcons } from './props';
import { EASE_OUT, clamp, useTheme } from './primitives';
import { BigFxName } from './anim';
import { HEIGHT, MotionScene, WIDTH } from './types';

/**
 * BIG elements added to the picture: large, soft shapes that move behind the text (never over it): radar rings, a sunburst, a hand-drawn circle, giant arrows, a huge icon,
 * viewfinder brackets, a scanning laser, speed lines, sparkles, a diamond tunnel, a ring that fills, a crosshair, a wave of dots and a border that draws itself.
 * They live in the camera layer, so the camera moves them too. All use the look's own colours.
 */
export const BigFx: React.FC<{ name: BigFxName; scene: MotionScene; index: number }> = ({ name, scene, index }) => {
  const frame = useCurrentFrame();
  const { theme, light } = useTheme();
  const a = theme.accent;
  const b = theme.accent2 ?? a;
  const dur = Math.max(1, scene.durationInFrames);
  const prog = frame / dur;
  const enter = interpolate(frame, [0, 16], [0, 1], { ...clamp, easing: EASE_OUT });
  const cx = WIDTH / 2;
  const cy = 790;
  const fill: React.CSSProperties = { position: 'absolute', left: 0, top: 0, width: WIDTH, height: HEIGHT, overflow: 'visible', pointerEvents: 'none' };
  const seed = (k: string) => random(`${name}${index}${k}`);

  if (name === 'rings') {
    return (
      <svg style={fill}>
        {[0, 1, 2].map((i) => {
          const t = ((frame + i * 24) % 72) / 72;
          return <circle key={i} cx={cx} cy={cy} r={120 + t * 560} fill="none" stroke={i % 2 ? b : a} strokeWidth={7 * (1 - t) + 1.5} opacity={0.5 * (1 - t) * enter} />;
        })}
        <circle cx={cx} cy={cy} r={16} fill={a} opacity={0.5 * enter} />
      </svg>
    );
  }
  if (name === 'rays') {
    const rot = frame * 0.35 + seed('r') * 90;
    return (
      <AbsoluteFill style={{ pointerEvents: 'none', opacity: 0.2 * enter, WebkitMaskImage: 'radial-gradient(circle at 50% 42%, #000 0%, transparent 68%)', maskImage: 'radial-gradient(circle at 50% 42%, #000 0%, transparent 68%)' }}>
        <div style={{ position: 'absolute', left: cx - 1400, top: cy - 1400, width: 2800, height: 2800, background: `repeating-conic-gradient(from ${rot}deg at 50% 50%, ${a} 0deg 7deg, transparent 7deg 22deg)` }} />
      </AbsoluteFill>
    );
  }
  if (name === 'scribble') {
    const d1 = 'M 130 760 C 120 520, 420 440, 700 470 C 960 500, 1010 760, 900 960 C 790 1130, 330 1150, 190 1000 C 110 910, 150 720, 330 600';
    const L1 = 3600;
    const p1 = interpolate(frame, [4, 34], [0, 1], { ...clamp, easing: EASE_OUT });
    const d2 = 'M 150 1190 C 330 1150, 420 1230, 560 1190 S 800 1150, 940 1200';
    const p2 = interpolate(frame, [26, 44], [0, 1], { ...clamp, easing: EASE_OUT });
    return (
      <svg style={{ ...fill, opacity: 0.55 }}>
        <path d={d1} fill="none" stroke={a} strokeWidth={11} strokeLinecap="round" strokeDasharray={L1} strokeDashoffset={L1 * (1 - p1)} style={{ filter: `drop-shadow(0 0 10px ${a})` }} />
        <path d={d2} fill="none" stroke={b} strokeWidth={9} strokeLinecap="round" strokeDasharray={900} strokeDashoffset={900 * (1 - p2)} />
      </svg>
    );
  }
  if (name === 'arrow') {
    const chev = (x: number, o: number, k: number) => <path key={k} d={`M ${x} 1130 l 150 110 l -150 110 l 70 0 l 150 -110 l -150 -110 z`} fill={k % 2 ? b : a} opacity={o} />;
    const slide = ((frame * 9) % 1500) - 300;
    return <svg style={{ ...fill, opacity: 0.4 * enter }}>{[0, 1, 2, 3].map((k) => chev(slide + k * 300 - 450, 0.5 + k * 0.12, k))}</svg>;
  }
  if (name === 'giantIcon') {
    const names = pickIcons(scene, []);
    const key = names[0] && ICONS[names[0]] ? names[0] : 'chip';
    const rot = (seed('i') > 0.5 ? 1 : -1) * (frame * 0.25 + 12);
    const right = seed('p') > 0.5;
    return (
      <AbsoluteFill style={{ pointerEvents: 'none', opacity: 0.2 * enter }}>
        <svg viewBox="0 0 48 48" width={820} height={820} style={{ position: 'absolute', left: right ? 520 : -300, top: 760, transform: `rotate(${rot}deg) scale(${0.9 + 0.1 * enter})`, overflow: 'visible' }} fill="none" stroke={a} strokeWidth={1.1} strokeLinecap="round" strokeLinejoin="round">
          {ICONS[key]}
        </svg>
      </AbsoluteFill>
    );
  }
  if (name === 'brackets') {
    const k = interpolate(frame, [0, 22], [1.28, 1], { ...clamp, easing: EASE_OUT });
    const arm = (x: number, y: number, sx: number, sy: number) => <path d={`M ${x} ${y + sy * 130} L ${x} ${y} L ${x + sx * 130} ${y}`} fill="none" stroke={a} strokeWidth={9} strokeLinecap="square" />;
    const L = 70, R = 1010, T = 330, B = 1450;
    return (
      <svg style={{ ...fill, opacity: 0.55 * enter, transformOrigin: `${cx}px ${(T + B) / 2}px`, transform: `scale(${k})` }}>
        {arm(L, T, 1, 1)}{arm(R, T, -1, 1)}{arm(L, B, 1, -1)}{arm(R, B, -1, -1)}
        <circle cx={cx} cy={(T + B) / 2} r={7} fill={a} opacity={0.6 + 0.4 * Math.sin(frame / 5)} />
      </svg>
    );
  }
  if (name === 'laser') {
    const y = 330 + (((frame * 14) % 1250) / 1250) * 1150;
    return (
      <AbsoluteFill style={{ pointerEvents: 'none', opacity: 0.55 * enter }}>
        <div style={{ position: 'absolute', left: 0, right: 0, top: y - 150, height: 150, background: `linear-gradient(180deg, transparent, ${a}33)` }} />
        <div style={{ position: 'absolute', left: 0, right: 0, top: y, height: 5, background: a, boxShadow: `0 0 30px 6px ${a}` }} />
      </AbsoluteFill>
    );
  }
  if (name === 'speed') {
    return (
      <AbsoluteFill style={{ pointerEvents: 'none', opacity: 0.4 * enter }}>
        {Array.from({ length: 18 }).map((_, i) => {
          const sp = 26 + seed(`s${i}`) * 34;
          const len = 220 + seed(`l${i}`) * 560;
          const x = (((frame * sp + seed(`x${i}`) * 2600) % 2800) - 500);
          return <div key={i} style={{ position: 'absolute', left: x, top: 340 + seed(`y${i}`) * 1100, width: len, height: 3 + seed(`h${i}`) * 4, borderRadius: 3, background: `linear-gradient(90deg, transparent, ${i % 3 ? a : b})` }} />;
        })}
      </AbsoluteFill>
    );
  }
  if (name === 'stars') {
    const star = (s: number) => `M 0 ${-s} Q 0 0 ${s} 0 Q 0 0 0 ${s} Q 0 0 ${-s} 0 Q 0 0 0 ${-s} Z`;
    return (
      <svg style={{ ...fill, opacity: enter }}>
        {Array.from({ length: 6 }).map((_, i) => {
          const tw = 0.5 + 0.5 * Math.sin(frame / (7 + i * 2) + i * 2);
          const s = 70 + seed(`z${i}`) * 150;
          const x = 80 + seed(`x${i}`) * 920;
          const y = 360 + seed(`y${i}`) * 1060;
          return <path key={i} d={star(s)} transform={`translate(${x} ${y}) rotate(${frame * 0.4 * (i % 2 ? 1 : -1)}) scale(${0.35 + 0.65 * tw})`} fill={i % 2 ? b : a} opacity={0.2 + 0.4 * tw} />;
        })}
      </svg>
    );
  }
  if (name === 'diamonds') {
    return (
      <svg style={{ ...fill, opacity: 0.4 * enter }}>
        {[0, 1, 2, 3].map((i) => {
          const t = ((frame * 0.7 + i * 30) % 120) / 120;
          const s = 120 + t * 640;
          return <rect key={i} x={cx - s / 2} y={cy - s / 2} width={s} height={s} transform={`rotate(${45 + frame * 0.3} ${cx} ${cy})`} fill="none" stroke={i % 2 ? b : a} strokeWidth={6 * (1 - t) + 1} opacity={1 - t} />;
        })}
      </svg>
    );
  }
  if (name === 'pie') {
    const R = 430;
    const C = 2 * Math.PI * R;
    const p = interpolate(prog, [0, 0.85], [0.04, 1], clamp);
    return (
      <svg style={{ ...fill, opacity: 0.4 * enter }}>
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={light ? '#0A1220' : '#FFFFFF'} strokeOpacity={0.12} strokeWidth={26} />
        <circle cx={cx} cy={cy} r={R} fill="none" stroke={a} strokeWidth={26} strokeLinecap="round" strokeDasharray={C} strokeDashoffset={C * (1 - p)} transform={`rotate(-90 ${cx} ${cy})`} style={{ filter: `drop-shadow(0 0 14px ${a})` }} />
      </svg>
    );
  }
  if (name === 'crosshair') {
    const s = 1 + 0.06 * Math.sin(frame / 9);
    return (
      <svg style={{ ...fill, opacity: 0.45 * enter }}>
        <g transform={`translate(${cx} ${cy}) rotate(${Math.sin(frame / 40) * 6}) scale(${s})`} stroke={a} strokeWidth={5} fill="none">
          <circle r={300} /><circle r={170} strokeDasharray="22 16" />
          <path d="M -460 0 H -230 M 230 0 H 460 M 0 -460 V -230 M 0 230 V 460" />
        </g>
      </svg>
    );
  }
  if (name === 'dotwave') {
    const cols = 11;
    const rows = 17;
    return (
      <svg style={{ ...fill, opacity: 0.55 * enter }}>
        {Array.from({ length: cols * rows }).map((_, n) => {
          const c = n % cols;
          const r = Math.floor(n / cols);
          const x = 70 + c * 94;
          const y = 360 + r * 66;
          const d = Math.hypot(x - cx, y - cy);
          const w = 0.5 + 0.5 * Math.sin(d / 70 - frame / 6);
          return <circle key={n} cx={x} cy={y} r={3 + w * 8} fill={w > 0.7 ? a : b} opacity={0.15 + 0.5 * w} />;
        })}
      </svg>
    );
  }
  // frameDraw: a double border that draws itself around the screen
  const per = 2 * (900 + 1380);
  const p = interpolate(frame, [0, 34], [0, 1], { ...clamp, easing: EASE_OUT });
  return (
    <svg style={{ ...fill, opacity: 0.6 }}>
      <rect x={90} y={330} width={900} height={1130} rx={30} fill="none" stroke={a} strokeWidth={6} strokeDasharray={per} strokeDashoffset={per * (1 - p)} style={{ filter: `drop-shadow(0 0 10px ${a})` }} />
      <rect x={112} y={352} width={856} height={1086} rx={22} fill="none" stroke={b} strokeWidth={3} strokeDasharray={per} strokeDashoffset={per * (1 - p)} />
    </svg>
  );
};
