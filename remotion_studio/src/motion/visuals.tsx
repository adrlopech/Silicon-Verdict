import React from 'react';
import { AbsoluteFill, interpolate, random, useCurrentFrame } from 'remotion';
import { MONO } from './fonts';
import { useSceneCtx } from './looks';
import { EASE_IO, EASE_OUT, clamp, useTheme } from './primitives';
import { HEIGHT, MotionScene, SAFE_BOTTOM, SAFE_TOP, WIDTH } from './types';

/**
 * STAGE: a drawn, animated scene behind the text of a text scene (a crowd walking, memory cells filling, CPU cores under load, a network with packets...).
 * The audit of Nov 2026 found most scenes were a headline on a dark gradient with the lower half empty; every scene now also shows something that MOVES and that
 * illustrates what the narrator says. The visual is picked from the scene's words (or named by `scene.visual`), never the same one twice in a video while others are left.
 */
export type VisualName = 'crowd' | 'memory' | 'cores' | 'network' | 'bars' | 'wave' | 'gauge' | 'map' | 'city' | 'layers' | 'matrix' | 'radar' | 'orbit';
export const VISUAL_NAMES: VisualName[] = ['crowd', 'memory', 'cores', 'network', 'bars', 'wave', 'gauge', 'map', 'city', 'layers', 'matrix', 'radar', 'orbit'];

/** Scene types that carry a stage behind them (the others fill the frame by themselves). */
export const STAGE_SCENES = new Set(['bigText', 'textWithAccent', 'card', 'counter', 'progressBar', 'curve', 'verdict', 'list', 'codeBlock', 'timeline', 'headline']);

const RULES: [RegExp, VisualName][] = [
  [/\b(crowds?|npcs?|people|characters?|pedestrians?|players?|population|team|employees?|staff|citizens|everyone|audience)\b/i, 'crowd'],
  [/\b(memory|ram|storage|cache|disks?|duplicate|copies|copy|files?|download|install|buffer|vram|megabytes?|gigabytes?)\b/i, 'memory'],
  [/\b(cpu|cores?|threads?|processors?|zen|simulat\w*|compute|logic|workload|load)\b/i, 'cores'],
  [/\b(network|online|servers?|cloud|internet|streams?|multiplayer|connect\w*|packets?|wi-?fi|latency|data center)\b/i, 'network'],
  [/\b(map|world|region|country|global|continent|location|territory|open world)\b/i, 'map'],
  [/\b(city|urban|skyline|buildings?|streets?|florida|leonida|downtown|district)\b/i, 'city'],
  [/\b(speed|fps|frames?|performance|fast|slow|power|clock|ghz|milliseconds?|smooth|stutter)\b/i, 'gauge'],
  [/\b(sound|audio|voice|music|trailer|signal|noise|radio|hear)\b/i, 'wave'],
  [/\b(layers?|stack|render\w*|pipeline|engine|technique|retarget\w*|adjust\w*|system|graphics|pixels?|shaders?)\b/i, 'layers'],
  [/\b(code|bits?|algorithms?|software|ai|generat\w*|procedural|binary|digital|programs?|scripts?)\b/i, 'matrix'],
  [/\b(scan\w*|weather|storms?|hurricanes?|rain|detect\w*|search|track\w*|radar|clouds?|wind)\b/i, 'radar'],
  [/\b(grew|growth|bigger|larger|times|increase\w*|compare\w*|double\w*|record|views|million|thousand|more than|jump|up from|rise|rose)\b/i, 'bars'],
];
const FALLBACK: VisualName[] = ['orbit', 'bars', 'layers', 'radar', 'network'];

/** The stage of every scene: what the words name first, but never one the video already showed (a gauge behind the hook AND behind the takeaway reads as a template);
 *  only when all of them have been used, the rule falls back to "not within the last three scenes". */
export const pickVisuals = (scenes: MotionScene[]): (VisualName | null)[] => {
  const out: (VisualName | null)[] = [];
  scenes.forEach((s, i) => {
    if (!STAGE_SCENES.has(s.type)) { out.push(null); return; }
    const recent = out.slice(Math.max(0, i - 3), i);
    const named = (s.visual ?? '') as VisualName;
    if (VISUAL_NAMES.includes(named)) { out.push(named); return; }
    const hay = [s.text, s.accentText, s.kicker, s.narration, ...(s.items ?? [])].filter(Boolean).join(' ');
    const wanted = RULES.filter(([re]) => re.test(hay)).map(([, v]) => v);
    const pool = [...wanted, ...FALLBACK, ...VISUAL_NAMES];
    out.push(pool.find((v) => !out.includes(v)) ?? pool.find((v) => !recent.includes(v)) ?? pool[0]);
  });
  return out;
};

type Ctx = { accent: string; accent2: string; ink: string; light: boolean; frame: number; seed: number };

// the region where the visuals live: from the middle of the frame down to the caption strip
const DH = 560; // design height of every visual: it is drawn in a 560 px band above the captions and scaled down when the text leaves less room
const bottomOf = (captionSpace: number) => HEIGHT - SAFE_BOTTOM - captionSpace + 10;

const Person: React.FC<{ x: number; y: number; h: number; color: string; lit: number; sway: number }> = ({ x, y, h, color, lit, sway }) => {
  const w = h * 0.42;
  return (
    <g transform={`translate(${x + sway} ${y})`} opacity={0.42 + 0.58 * lit}>
      <circle cx={0} cy={-h} r={w * 0.34} fill={color} />
      <rect x={-w / 2} y={-h * 0.82} width={w} height={h * 0.82} rx={w * 0.4} fill={color} />
      {lit > 0.5 && <circle cx={0} cy={-h} r={w * 0.34 + 10 * lit} fill="none" stroke={color} strokeWidth={2} opacity={0.6} />}
    </g>
  );
};

const Crowd: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, seed, bottom, top }) => {
  const rows = [
    { y: bottom - 20, h: 150, n: 8, c: accent, k: 1 },
    { y: bottom - 150, h: 112, n: 10, c: accent2, k: 0.7 },
    { y: bottom - 250, h: 82, n: 13, c: accent, k: 0.5 },
    { y: bottom - 330, h: 58, n: 17, c: accent2, k: 0.35 },
  ];
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      {rows.map((r, ri) =>
        Array.from({ length: r.n }).map((_, i) => {
          const hv = r.h * (0.84 + random(`h${seed}${ri}${i}`) * 0.3); // people of different heights
          const walk = ((frame * (0.5 + r.k) * (ri % 2 ? -1 : 1) + i * (WIDTH / r.n) + random(`o${ri}${i}`) * 60) % (WIDTH + 140) + WIDTH + 140) % (WIDTH + 140) - 70;
          const sweep = interpolate(((frame * 7 + ri * 120) % 1500) - walk, [-60, 0, 60], [0, 1, 0], clamp); // a light sweeping along the row
          return <Person key={`${ri}-${i}`} x={walk} y={r.y} h={hv} color={r.c} lit={sweep} sway={Math.sin(frame / 7 + i + ri) * 4} />;
        }),
      )}
    </svg>
  );
};

const Memory: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, seed, bottom, top }) => {
  const cols = 12, rows = 6, cw = 70, ch = 46, gap = 12;
  const x0 = (WIDTH - (cols * (cw + gap) - gap)) / 2, y0 = bottom - rows * (ch + gap) - 40;
  const fill = interpolate(frame, [4, 90], [0, 1], { ...clamp, easing: EASE_IO });
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      {Array.from({ length: cols * rows }).map((_, i) => {
        const c = i % cols, r = Math.floor(i / cols);
        const order = (c + r * 1.4) / (cols + rows * 1.4);
        const on = interpolate(fill, [order, order + 0.08], [0, 1], clamp);
        const flick = random(`f${seed}${i}${Math.floor(frame / 10)}`) > 0.93 ? 1 : 0;
        const color = flick ? accent2 : accent;
        return <rect key={i} x={x0 + c * (cw + gap)} y={y0 + r * (ch + gap)} width={cw} height={ch} rx={8} fill={on > 0.5 ? color : 'none'} fillOpacity={0.28 + 0.5 * flick} stroke={color} strokeOpacity={0.25 + 0.55 * on} strokeWidth={2.5} />;
      })}
      <rect x={x0} y={y0 - 34} width={cols * (cw + gap) - gap} height={10} rx={5} fill="none" stroke={accent} strokeOpacity={0.45} strokeWidth={2} />
      <rect x={x0} y={y0 - 34} width={(cols * (cw + gap) - gap) * fill} height={10} rx={5} fill={accent} fillOpacity={0.8} />
    </svg>
  );
};

const Cores: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, seed, bottom, top }) => {
  const n = 4, cell = 112, gap = 18;
  const x0 = (WIDTH - (n * cell + (n - 1) * gap)) / 2, y0 = bottom - n * (cell + gap) + 10;
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      {Array.from({ length: n * n }).map((_, i) => {
        const c = i % n, r = Math.floor(i / n);
        const load = 0.25 + 0.75 * (0.5 + 0.5 * Math.sin(frame / (9 + random(`p${seed}${i}`) * 9) + i * 1.7));
        const hot = load > 0.8;
        const col = hot ? accent2 : accent;
        const x = x0 + c * (cell + gap), y = y0 + r * (cell + gap);
        return (
          <g key={i}>
            <rect x={x} y={y} width={cell} height={cell} rx={16} fill="none" stroke={col} strokeOpacity={0.55} strokeWidth={3} />
            <rect x={x + 18} y={y + cell - 18 - (cell - 36) * load} width={cell - 36} height={(cell - 36) * load} rx={6} fill={col} fillOpacity={0.35 + 0.45 * load} />
            <text x={x + 14} y={y + 30} fontFamily={MONO} fontSize={22} fill={col} fillOpacity={0.8}>{`C${String(i).padStart(2, '0')}`}</text>
            {hot && <rect x={x - 6} y={y - 6} width={cell + 12} height={cell + 12} rx={20} fill="none" stroke={col} strokeOpacity={0.5} strokeWidth={2} />}
          </g>
        );
      })}
    </svg>
  );
};

const NODES: [number, number][] = [[0.12, 0.2], [0.34, 0.05], [0.6, 0.18], [0.88, 0.08], [0.22, 0.55], [0.5, 0.5], [0.78, 0.46], [0.1, 0.92], [0.4, 0.88], [0.7, 0.95], [0.92, 0.78]];
const EDGES: [number, number][] = [[0, 1], [1, 2], [2, 3], [0, 4], [1, 5], [2, 5], [3, 6], [4, 5], [5, 6], [4, 7], [5, 8], [6, 9], [6, 10], [8, 9], [7, 8], [9, 10]];
const Network: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, bottom, top }) => {
  const h = bottom - top - 40;
  const pt = (i: number): [number, number] => [60 + NODES[i][0] * (WIDTH - 120), top + 40 + NODES[i][1] * h];
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      {EDGES.map(([a, b], i) => {
        const [x1, y1] = pt(a), [x2, y2] = pt(b);
        const t = ((frame / (38 + (i % 5) * 9) + i * 0.37) % 1);
        return (
          <g key={i}>
            <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={accent} strokeOpacity={0.3} strokeWidth={2.5} />
            <circle cx={x1 + (x2 - x1) * t} cy={y1 + (y2 - y1) * t} r={9} fill={i % 3 ? accent : accent2} style={{ filter: `drop-shadow(0 0 10px ${accent})` }} />
          </g>
        );
      })}
      {NODES.map((_, i) => {
        const [x, y] = pt(i);
        const pulse = 0.5 + 0.5 * Math.sin(frame / 12 + i * 2);
        return (
          <g key={i}>
            <circle cx={x} cy={y} r={26 + pulse * 8} fill="none" stroke={accent2} strokeOpacity={0.4 * pulse} strokeWidth={2} />
            <circle cx={x} cy={y} r={15} fill="#05070C" stroke={accent} strokeWidth={4} />
          </g>
        );
      })}
    </svg>
  );
};

const Bars: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, seed, bottom, top }) => {
  const n = 9, bw = 74, gap = 28;
  const x0 = (WIDTH - (n * (bw + gap) - gap)) / 2;
  const max = bottom - top - 120;
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      <line x1={x0 - 20} y1={bottom - 20} x2={WIDTH - x0 + 20} y2={bottom - 20} stroke={accent} strokeOpacity={0.5} strokeWidth={3} />
      {Array.from({ length: n }).map((_, i) => {
        const target = 0.18 + (i / (n - 1)) * 0.7 + random(`b${seed}${i}`) * 0.12; // a rising trend with noise
        const grow = interpolate(frame, [4 + i * 5, 30 + i * 5], [0, 1], { ...clamp, easing: EASE_OUT });
        const live = 1 + Math.sin(frame / 14 + i) * 0.035;
        const h = max * Math.min(1, target) * grow * live;
        const col = i === n - 1 ? accent2 : accent;
        return (
          <g key={i}>
            <rect x={x0 + i * (bw + gap)} y={bottom - 20 - h} width={bw} height={h} rx={10} fill={col} fillOpacity={0.3 + 0.45 * (i / n)} stroke={col} strokeWidth={3} />
            <rect x={x0 + i * (bw + gap)} y={bottom - 20 - h} width={bw} height={8} rx={4} fill={col} />
          </g>
        );
      })}
    </svg>
  );
};

const Wave: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, bottom, top }) => {
  const cy = (top + bottom) / 2 + 60;
  const line = (amp: number, freq: number, speed: number, ph: number) => {
    const pts: string[] = [];
    for (let x = 0; x <= WIDTH; x += 12) pts.push(`${x},${cy + Math.sin((x / WIDTH) * Math.PI * 2 * freq + frame / speed + ph) * amp * (0.55 + 0.45 * Math.sin(x / 140 - frame / 26))}`);
    return pts.join(' ');
  };
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      <polyline points={line(130, 2.2, 8, 0)} fill="none" stroke={accent} strokeWidth={6} strokeLinecap="round" />
      <polyline points={line(90, 3.1, 11, 1.7)} fill="none" stroke={accent2} strokeWidth={4} strokeOpacity={0.8} strokeLinecap="round" />
      <polyline points={line(60, 4.4, 6, 3.1)} fill="none" stroke={accent} strokeWidth={3} strokeOpacity={0.5} strokeLinecap="round" />
      {Array.from({ length: 40 }).map((_, i) => {
        const h = 18 + 70 * Math.abs(Math.sin(frame / 7 + i * 0.7) * Math.cos(frame / 19 + i * 0.3));
        return <rect key={i} x={30 + i * 25} y={bottom - 40 - h} width={13} height={h} rx={6} fill={i % 5 === 0 ? accent2 : accent} fillOpacity={0.6} />;
      })}
    </svg>
  );
};

const Gauge: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, bottom, top }) => {
  const cx = WIDTH / 2, cy = bottom - 90, r = 400;
  const sweep = interpolate(frame, [4, 60], [0, 1], { ...clamp, easing: EASE_OUT });
  const needle = -Math.PI + Math.PI * Math.min(1, sweep * 0.78 + Math.sin(frame / 9) * 0.03 * sweep);
  const arc = (a0: number, a1: number, rr: number) => `M ${cx + Math.cos(a0) * rr} ${cy + Math.sin(a0) * rr} A ${rr} ${rr} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${cx + Math.cos(a1) * rr} ${cy + Math.sin(a1) * rr}`;
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      <path d={arc(-Math.PI, 0, r)} fill="none" stroke={accent} strokeOpacity={0.3} strokeWidth={26} strokeLinecap="round" />
      <path d={arc(-Math.PI, needle, r)} fill="none" stroke={accent} strokeWidth={26} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 16px ${accent})` }} />
      <path d={arc(-Math.PI, 0, r - 54)} fill="none" stroke={accent2} strokeOpacity={0.35} strokeWidth={4} strokeDasharray="4 18" />
      {Array.from({ length: 21 }).map((_, i) => {
        const a = -Math.PI + (i / 20) * Math.PI;
        return <line key={i} x1={cx + Math.cos(a) * (r + 30)} y1={cy + Math.sin(a) * (r + 30)} x2={cx + Math.cos(a) * (r + (i % 5 === 0 ? 62 : 46))} y2={cy + Math.sin(a) * (r + (i % 5 === 0 ? 62 : 46))} stroke={accent} strokeOpacity={0.6} strokeWidth={i % 5 === 0 ? 5 : 2.5} />;
      })}
      <line x1={cx} y1={cy} x2={cx + Math.cos(needle) * (r - 40)} y2={cy + Math.sin(needle) * (r - 40)} stroke={accent2} strokeWidth={9} strokeLinecap="round" />
      <circle cx={cx} cy={cy} r={22} fill="#05070C" stroke={accent2} strokeWidth={7} />
    </svg>
  );
};

const MapGrid: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, seed, bottom, top }) => {
  const cx = WIDTH / 2, cy = (top + bottom) / 2 + 40, rx = 470, ry = 290;
  const scan = ((frame * 5) % (rx * 2 + 200)) - rx - 100;
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      <ellipse cx={cx} cy={cy} rx={rx} ry={ry} fill="none" stroke={accent} strokeOpacity={0.5} strokeWidth={3} />
      {[-0.66, -0.33, 0, 0.33, 0.66].map((k) => <ellipse key={k} cx={cx} cy={cy} rx={rx} ry={Math.abs(ry * (1 - Math.abs(k) * 0.18))} transform={`translate(0 ${k * ry * 0.9}) scale(1 ${0.2 + 0.1 * (1 - Math.abs(k))})`} style={{ transformOrigin: `${cx}px ${cy}px` }} fill="none" stroke={accent} strokeOpacity={0.22} strokeWidth={2} />)}
      {[-0.7, -0.35, 0, 0.35, 0.7].map((k) => <ellipse key={`m${k}`} cx={cx + k * 120 * Math.sin(frame / 80)} cy={cy} rx={Math.abs(rx * (1 - Math.abs(k)) * 0.5) + 14} ry={ry} fill="none" stroke={accent} strokeOpacity={0.2} strokeWidth={2} />)}
      {Array.from({ length: 90 }).map((_, i) => {
        const a = random(`a${seed}${i}`) * Math.PI * 2, d = Math.sqrt(random(`d${seed}${i}`));
        const x = cx + Math.cos(a) * d * rx * 0.94, y = cy + Math.sin(a) * d * ry * 0.94;
        const near = Math.max(0, 1 - Math.abs(x - cx - scan) / 90);
        return <circle key={i} cx={x} cy={y} r={3 + near * 6} fill={near > 0.2 ? accent2 : accent} fillOpacity={0.3 + near * 0.7} />;
      })}
      <line x1={cx + scan} y1={cy - ry} x2={cx + scan} y2={cy + ry} stroke={accent2} strokeOpacity={0.55} strokeWidth={3} />
      {[0, 1, 2].map((i) => {
        const x = cx + (random(`px${seed}${i}`) - 0.5) * rx * 1.3, y = cy + (random(`py${seed}${i}`) - 0.5) * ry * 1.2;
        const p = ((frame / 40 + i * 0.33) % 1);
        return (
          <g key={i}>
            <circle cx={x} cy={y} r={12} fill={accent2} />
            <circle cx={x} cy={y} r={14 + p * 60} fill="none" stroke={accent2} strokeOpacity={1 - p} strokeWidth={3} />
          </g>
        );
      })}
    </svg>
  );
};

const City: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, seed, bottom, top }) => {
  const n = 15, bw = 64;
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      {Array.from({ length: n }).map((_, i) => {
        const h = 120 + random(`c${seed}${i}`) * 380 * (0.5 + 0.5 * Math.sin(i * 0.45 + 1) ** 2 + 0.3);
        const grow = interpolate(frame, [3 + i * 3, 28 + i * 3], [0, 1], { ...clamp, easing: EASE_OUT });
        const x = 10 + i * (bw + 5), top = bottom - 12 - h * grow;
        const col = i % 4 === 0 ? accent2 : accent;
        const rows = Math.floor(h / 36), cols = 2;
        return (
          <g key={i}>
            <rect x={x} y={top} width={bw} height={h * grow} fill={col} fillOpacity={0.14} stroke={col} strokeOpacity={0.7} strokeWidth={2.5} />
            {Array.from({ length: rows * cols }).map((_, k) => {
              const wy = top + 14 + Math.floor(k / cols) * 36;
              if (wy > bottom - 30) return null;
              const lit = random(`w${seed}${i}${k}${Math.floor(frame / 24)}`) > 0.55;
              return <rect key={k} x={x + 10 + (k % cols) * 26} y={wy} width={14} height={18} rx={2} fill={col} fillOpacity={lit ? 0.85 : 0.14} />;
            })}
          </g>
        );
      })}
      <line x1={0} y1={bottom - 12} x2={WIDTH} y2={bottom - 12} stroke={accent} strokeWidth={4} />
    </svg>
  );
};

const Layers: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, bottom, top }) => {
  const cy = (top + bottom) / 2 + 80;
  return (
    <div style={{ position: 'absolute', left: 0, top: 0, width: WIDTH, height: HEIGHT, perspective: 1400 }}>
      {[0, 1, 2, 3].map((i) => {
        const slide = interpolate(frame, [4 + i * 7, 34 + i * 7], [0, 1], { ...clamp, easing: EASE_OUT });
        const float = Math.sin(frame / 18 + i * 1.3) * 12;
        const col = i % 2 ? accent2 : accent;
        return (
          <div key={i} style={{ position: 'absolute', left: WIDTH / 2 - 330, top: cy - 100 - i * 88 + float + (1 - slide) * 150, width: 660, height: 360, borderRadius: 28, border: `4px solid ${col}`, background: `${col}${i === 3 ? '30' : '16'}`, boxShadow: `0 0 40px ${col}33`, transform: `rotateX(64deg) rotateZ(${-24 + Math.sin(frame / 40) * 4}deg)`, opacity: 0.35 + 0.65 * slide }}>
            <div style={{ position: 'absolute', left: 30, top: 28, fontFamily: MONO, fontSize: 30, letterSpacing: 6, color: col }}>{`LAYER ${String(4 - i).padStart(2, '0')}`}</div>
            <div style={{ position: 'absolute', left: 30, right: 30, bottom: 34, height: 10, borderRadius: 5, background: `${col}55` }}><div style={{ width: `${30 + ((frame * 1.4 + i * 30) % 70)}%`, height: 10, borderRadius: 5, background: col }} /></div>
          </div>
        );
      })}
    </div>
  );
};

const Matrix: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, seed, bottom, top }) => {
  const cols = 24;
  const GL = '01ABCDEF01{}<>/=+';
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      {Array.from({ length: cols }).map((_, c) => {
        const speed = 3 + random(`s${seed}${c}`) * 5, off = random(`o${seed}${c}`) * 1400;
        const head = ((frame * speed + off) % (bottom - top + 300)) + top - 150;
        return Array.from({ length: 9 }).map((__, k) => {
          const y = head - k * 44;
          if (y < top - 20 || y > bottom) return null;
          const ch = GL[Math.floor(random(`g${seed}${c}${k}${Math.floor(frame / 6)}`) * GL.length)];
          return <text key={`${c}-${k}`} x={20 + c * 43} y={y} fontFamily={MONO} fontSize={36} fill={k === 0 ? accent2 : accent} fillOpacity={k === 0 ? 1 : 0.7 - k * 0.07}>{ch}</text>;
        });
      })}
    </svg>
  );
};

const Radar: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, seed, bottom, top }) => {
  const cx = WIDTH / 2, cy = (top + bottom) / 2, R = Math.min(300, (bottom - top) / 2 - 20);
  const a = (frame * 0.07) % (Math.PI * 2);
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      {[0.25, 0.5, 0.75, 1].map((k) => <circle key={k} cx={cx} cy={cy} r={R * k} fill="none" stroke={accent} strokeOpacity={0.3} strokeWidth={2.5} />)}
      <line x1={cx - R} y1={cy} x2={cx + R} y2={cy} stroke={accent} strokeOpacity={0.25} strokeWidth={2} />
      <line x1={cx} y1={cy - R} x2={cx} y2={cy + R} stroke={accent} strokeOpacity={0.25} strokeWidth={2} />
      {Array.from({ length: 28 }).map((_, i) => {
        const t = 1 - i / 28;
        const aa = a - i * 0.035;
        return <line key={i} x1={cx} y1={cy} x2={cx + Math.cos(aa) * R} y2={cy + Math.sin(aa) * R} stroke={accent} strokeOpacity={0.5 * t * t} strokeWidth={9} />;
      })}
      {Array.from({ length: 9 }).map((_, i) => {
        const ang = random(`ra${seed}${i}`) * Math.PI * 2, d = 0.2 + random(`rd${seed}${i}`) * 0.75;
        const diff = ((a - ang) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
        const vis = Math.max(0, 1 - diff / 3);
        return <circle key={i} cx={cx + Math.cos(ang) * R * d} cy={cy + Math.sin(ang) * R * d} r={10 + vis * 8} fill={accent2} fillOpacity={vis} style={{ filter: `drop-shadow(0 0 12px ${accent2})` }} />;
      })}
    </svg>
  );
};

const Orbit: React.FC<Ctx & { bottom: number; top: number }> = ({ accent, accent2, frame, bottom, top }) => {
  const cx = WIDTH / 2, cy = (top + bottom) / 2 + 40;
  return (
    <svg width={WIDTH} height={HEIGHT} style={{ position: 'absolute', left: 0, top: 0 }}>
      {[150, 255, 360].map((r, ri) => <ellipse key={r} cx={cx} cy={cy} rx={r * 1.25} ry={r * 0.62} fill="none" stroke={ri === 1 ? accent2 : accent} strokeOpacity={0.35} strokeWidth={2.5} strokeDasharray={ri === 2 ? '3 14' : undefined} />)}
      <circle cx={cx} cy={cy} r={46 + Math.sin(frame / 10) * 5} fill={accent} fillOpacity={0.25} stroke={accent} strokeWidth={4} />
      {[0, 1, 2, 3, 4].map((i) => {
        const ri = i % 3, r = [150, 255, 360][ri];
        const ang = frame / (34 + ri * 16) * (ri % 2 ? -1 : 1) + i * 1.9;
        const x = cx + Math.cos(ang) * r * 1.25, y = cy + Math.sin(ang) * r * 0.62;
        return (
          <g key={i}>
            <line x1={cx} y1={cy} x2={x} y2={y} stroke={accent} strokeOpacity={0.18} strokeWidth={2} />
            <circle cx={x} cy={y} r={20} fill="#05070C" stroke={i % 2 ? accent2 : accent} strokeWidth={5} style={{ filter: `drop-shadow(0 0 12px ${accent})` }} />
          </g>
        );
      })}
    </svg>
  );
};

const STAGES: Record<VisualName, React.FC<Ctx & { bottom: number; top: number }>> = { crowd: Crowd, memory: Memory, cores: Cores, network: Network, bars: Bars, wave: Wave, gauge: Gauge, map: MapGrid, city: City, layers: Layers, matrix: Matrix, radar: Radar, orbit: Orbit };

/** The stage behind the text of one scene. `avail` = the room (px) between the bottom of the text and the caption strip, measured by the scene shell: the visual is drawn in a 560 px band
 *  and scaled down to fit it, so it never runs behind the text; with less than half the band free it is left out. It fades in, keeps moving and stays at moderate opacity. */
export const Stage: React.FC<{ scene: MotionScene; name: VisualName | null; index: number; avail: number }> = ({ scene, name, index, avail }) => {
  const frame = useCurrentFrame();
  const { theme, light } = useTheme();
  const { captionSpace } = useSceneCtx();
  if (!name || !STAGE_SCENES.has(scene.type)) return null;
  const k = Math.min(1, avail / DH);
  if (k < 0.5) return null;
  const C = STAGES[name];
  const p = interpolate(frame, [0, 22], [0, 1], { ...clamp, easing: EASE_OUT });
  const bottom = bottomOf(captionSpace);
  const top = bottom - DH;
  const ctx: Ctx = { accent: light ? '#0A5CFF' : theme.accent, accent2: light ? '#00A3E0' : theme.accent2 ?? theme.accent, ink: light ? '#0A1220' : '#FFFFFF', light, frame, seed: index * 17 + 3 };
  return (
    <AbsoluteFill style={{ pointerEvents: 'none', opacity: (light ? 0.7 : 0.9) * p * (k < 0.7 ? 0.85 : 1), transform: `translateY(${(1 - p) * 70}px)` }}>
      <AbsoluteFill style={{ transform: `scale(${k})`, transformOrigin: `50% ${bottom}px`, WebkitMaskImage: `linear-gradient(to bottom, transparent ${top}px, #000 ${top + 70}px)` }}>
        <C {...ctx} bottom={bottom} top={top} />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** Room under the text of a scene: from `textBottom` (+ a margin) down to the caption strip. */
export const stageRoom = (textBottom: number, captionSpace: number): number => bottomOf(captionSpace) - 20 - (textBottom + 36);
export const STAGE_TEXT_MAX_BOTTOM = 760; // the text block is lifted (up to just under the HUD) until it ends above this line, which leaves the stage 450 px or more
export const STAGE_TEXT_MIN_TOP = 340; // never lifted into the HUD / progress strip
