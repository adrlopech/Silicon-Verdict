import React from 'react';
import { AbsoluteFill, interpolate, random, useCurrentFrame } from 'remotion';
import { EASE_IO, EASE_OUT, clamp, useTheme } from './primitives';
import { ICONS } from './props';
import { HEIGHT, MotionScene, SAFE_BOTTOM, SAFE_TOP, SceneFx, WIDTH } from './types';

/**
 * Scene effects: one animated element that illustrates WHAT THE NARRATION SAYS (an airplane crossing the screen on "airplane mode", signal waves on "Wi-Fi",
 * lightning on "charging", embers on "heat"...). They are picked from the scene's own words, never repeated in two consecutive scenes, and stay behind the text.
 */
const FX_RULES: [RegExp, SceneFx][] = [
  [/\b(air ?planes?|aeroplanes?|planes?|flights?|flying|fly|flies|airlines?|airports?|aircraft|aviation|jets?|takeoff|landing)\b/i, 'plane'],
  [/\b(rockets?|launch\w*|lift ?off|spacecraft|space ?x)\b/i, 'rocket'],
  [/\b(satellites?|gps|orbit\w*)\b/i, 'satellite'],
  [/\b(wi-?fi|wireless|signals?|bluetooth|radio|cellular|5g|4g|antenna\w*|router\w*|broadcast\w*)\b/i, 'waves'],
  [/\b(charg\w*|voltage|electric\w*|lightning|power surge|current|volts?|spark\w*|shock\w*)\b/i, 'bolts'],
  [/\b(heat\w*|hot|warm\w*|thermal|overheat\w*|fire|flames?|burn\w*|melt\w*|throttl\w*)\b/i, 'embers'],
  [/\b(cold|freez\w*|ice|frozen|frost\w*|snow)\b/i, 'snow'],
  [/\b(water|rain\w*|liquid|coolant|drops?|flood\w*|wet)\b/i, 'drops'],
  [/\b(packets?|downloads?|uploads?|bandwidth|internet|network\w*|data ?cent\w*|streaming|transfer\w*|traffic|cables?)\b/i, 'packets'],
  [/\b(money|costs?|prices?|cheap\w*|expensive|dollars?|pays?|paid|cash)\b/i, 'coins'],
  [/\b(sound|audio|music|noise|voices?|echo|speakers?|headphones?|earbuds?|bass|volume)\b/i, 'equalizer'],
  [/\b(cellular|reception|bars|mobile network|carrier|lte|sim card)\b/i, 'signalbars'],
  [/\b(notifications?|messages?|texts?|alerts?|calls?|emails?|ringtone)\b/i, 'notifications'],
  [/\b(batter(?:y|ies)|percent|charged|power bank)\b/i, 'batteryfill'],
  [/\b(latency|delay\w*|milliseconds?|nanoseconds?|clock|waits?|waiting|ticks?|lag\w*)\b/i, 'clock'],
  [/\b(lock\w*|passwords?|encrypt\w*|secur\w*|privacy|private|hack\w*)\b/i, 'padlock'],
  [/\b(search\w*|finds?|found|scan\w*|looks? for|detect\w*|inspect\w*)\b/i, 'magnify'],
  [/\b(bits?|bytes?|binary|zeros?|digital)\b/i, 'bits'],
];

const ONCE = new Set<SceneFx>(['plane', 'rocket', 'satellite']); // the big fly-bys appear once per video: they stop being special when repeated

/** Effects named by a scene, in the order the viewer hears them. */
const fxCandidates = (scene: MotionScene): SceneFx[] => {
  if (scene.type === 'flash' || scene.type === 'footage' || scene.type === 'outro') return [];
  if (scene.fx) return [scene.fx];
  const hay = [scene.narration, scene.text, scene.accentText, scene.kicker].filter(Boolean).join(' ');
  const found: { fx: SceneFx; at: number }[] = [];
  for (const [re, fx] of FX_RULES) {
    const m = re.exec(hay);
    if (m) found.push({ fx, at: m.index });
  }
  return found.sort((a, b) => a.at - b.at).map((x) => x.fx);
};

/** Effect of each scene: what is named first, but never the same one within three scenes and each fly-by only once per video, so the video keeps showing something new. */
export const sceneFx = (scenes: MotionScene[]): (SceneFx | null)[] => {
  const out: (SceneFx | null)[] = [];
  const used = new Set<SceneFx>();
  scenes.forEach((s, i) => {
    const recent = out.slice(Math.max(0, i - 3), i);
    const explicit = !!s.fx;
    if (s.type === 'ui') { out.push(null); return; } // a drawn interface fills the scene: no fly-bys or icons over it
    const pick = fxCandidates(s).find((fx) => explicit || (!recent.includes(fx) && !(ONCE.has(fx) && used.has(fx))));
    out.push(pick ?? null);
    if (pick) used.add(pick);
  });
  return out;
};

const Icon: React.FC<{ name: string; size: number; color: string; rotate?: number; glow?: number }> = ({ name, size, color, rotate = 0, glow = 14 }) => (
  <svg width={size} height={size} viewBox="0 0 48 48" fill="none" stroke={color} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" style={{ transform: `rotate(${rotate}deg)`, filter: `drop-shadow(0 0 ${glow}px ${color})` }}>
    {ICONS[name]}
  </svg>
);

/** One pass across the screen: progress 0..1 with ease; repeats while the scene lasts (alternating direction). */
const passes = (frame: number, start: number, len: number, gap: number) => {
  const k = Math.floor((frame - start) / (len + gap));
  const local = frame - start - k * (len + gap);
  return { k: Math.max(0, k), p: interpolate(local, [0, len], [0, 1], { ...clamp, easing: EASE_IO }), live: frame >= start && local >= 0 && local <= len };
};

const Plane: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const { k, p, live } = passes(frame, 6, 78, 70);
  if (!live) return null;
  const dir = k % 2 === 0 ? 1 : -1;
  const y = SAFE_TOP + 340 + (k % 2) * 90 - Math.sin(p * Math.PI) * 60;
  const x = dir > 0 ? -160 + p * (WIDTH + 320) : WIDTH + 160 - p * (WIDTH + 320);
  const bank = (dir > 0 ? -1 : 1) * Math.cos(p * Math.PI) * 9;
  const trail = 520;
  return (
    <>
      <div style={{ position: 'absolute', left: dir > 0 ? x - trail : x + 40, top: y - 2, width: trail, height: 4, borderRadius: 2, background: `linear-gradient(${dir > 0 ? 90 : 270}deg, transparent, ${col}AA)`, opacity: 0.8, filter: `blur(1.5px)` }} />
      <div style={{ position: 'absolute', left: dir > 0 ? x - trail : x + 40, top: y + 16, width: trail * 0.7, height: 3, borderRadius: 2, background: `linear-gradient(${dir > 0 ? 90 : 270}deg, transparent, ${col}66)`, opacity: 0.6 }} />
      <div style={{ position: 'absolute', left: x - 80, top: y - 80 }}>
        <Icon name="plane" size={160} color={col} rotate={(dir > 0 ? 90 : -90) + bank} glow={18} />
      </div>
    </>
  );
};

const Rocket: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const { k, p, live } = passes(frame, 8, 70, 80);
  if (!live) return null;
  const side = k % 2 === 0 ? 1 : -1;
  const x = 540 + side * (330 - p * 120);
  const y = HEIGHT - SAFE_BOTTOM + 80 - p * (HEIGHT - SAFE_BOTTOM - SAFE_TOP + 240);
  return (
    <>
      <div style={{ position: 'absolute', left: x - 6, top: y + 70, width: 12, height: 420, borderRadius: 6, background: `linear-gradient(0deg, transparent, ${col}99)`, filter: 'blur(3px)' }} />
      <div style={{ position: 'absolute', left: x - 70, top: y - 70 }}>
        <Icon name="rocket" size={140} color={col} rotate={side > 0 ? 8 : -8} />
      </div>
    </>
  );
};

const Satellite: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const { p, live } = passes(frame, 4, 120, 40);
  if (!live) return null;
  const x = -120 + p * (WIDTH + 240);
  const y = SAFE_TOP + 300 - Math.sin(p * Math.PI) * 120;
  return (
    <>
      <div style={{ position: 'absolute', left: x - 70, top: y - 70, opacity: 0.95 }}>
        <Icon name="satellite" size={140} color={col} rotate={-20 + p * 40} />
      </div>
      {[0, 1].map((i) => {
        const r = ((frame * 2 + i * 40) % 80) + 10;
        return <div key={i} style={{ position: 'absolute', left: x - r, top: y - r, width: r * 2, height: r * 2, borderRadius: r, border: `2px solid ${col}`, opacity: Math.max(0, 0.5 - r / 180) }} />;
      })}
    </>
  );
};

const Waves: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const cx = 540;
  const cy = SAFE_TOP + 360;
  return (
    <>
      {[0, 1, 2, 3].map((i) => {
        const t = ((frame + i * 22) % 88) / 88;
        const r = 40 + t * 520;
        return <div key={i} style={{ position: 'absolute', left: cx - r, top: cy - r, width: r * 2, height: r * 2, borderRadius: r, border: `3px solid ${col}`, opacity: (1 - t) * 0.42 }} />;
      })}
    </>
  );
};

const Bolts: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  return (
    <>
      {[0, 1, 2].map((i) => {
        const period = 34 + i * 11;
        const f = (frame + i * 13) % period;
        const on = f < 9 ? interpolate(f, [0, 2, 9], [0, 1, 0], clamp) : 0;
        if (on <= 0) return null;
        const side = i % 2 === 0 ? -1 : 1;
        const x = 540 + side * (300 + random(`bx${i}-${Math.floor((frame + i * 13) / period)}`) * 120);
        const y = SAFE_TOP + 240 + random(`by${i}-${Math.floor((frame + i * 13) / period)}`) * 700;
        const s = 110 + random(`bs${i}`) * 90;
        return <div key={i} style={{ position: 'absolute', left: x - s / 2, top: y - s / 2, opacity: on }}><Icon name="bolt" size={s} color={col} rotate={side * 12} glow={26} /></div>;
      })}
    </>
  );
};

/** Rising embers / falling snow / falling drops / falling coins: the same particle engine with a different direction and shape. */
const Particles: React.FC<{ kind: 'embers' | 'snow' | 'drops' | 'coins'; accent: string; light: boolean }> = ({ kind, accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : kind === 'embers' ? '#7FB6FF' : kind === 'coins' ? '#9BD3FF' : accent; // every effect stays in the blue family
  const n = kind === 'coins' ? 9 : 18;
  const up = kind === 'embers';
  return (
    <>
      {Array.from({ length: n }).map((_, i) => {
        const speed = (kind === 'coins' ? 5.5 : kind === 'drops' ? 8 : kind === 'snow' ? 3 : 4) * (0.7 + random(`sp${i}`) * 0.7);
        const span = HEIGHT - SAFE_TOP * 0.6;
        const travel = (frame * speed + random(`o${i}`) * span) % span;
        const y = up ? HEIGHT - SAFE_BOTTOM + 120 - travel : SAFE_TOP * 0.6 + travel;
        const x = random(`x${i}`) * (WIDTH - 80) + 40 + Math.sin(frame / 18 + i) * (kind === 'snow' ? 40 : 14);
        const size = (kind === 'coins' ? 58 : kind === 'drops' ? 24 : kind === 'snow' ? 20 : 14) * (0.7 + random(`z${i}`) * 0.7);
        const fade = interpolate(travel, [0, 120, span - 160, span], [0, 1, 1, 0], clamp);
        if (kind === 'coins') {
          return (
            <div key={i} style={{ position: 'absolute', left: x, top: y, width: size, height: size, opacity: fade * 0.85, transform: `rotateY(${(frame * 9 + i * 40) % 360}deg)` }}>
              <Icon name="dollar" size={size} color={col} glow={10} />
            </div>
          );
        }
        return <div key={i} style={{ position: 'absolute', left: x, top: y, width: size, height: kind === 'drops' ? size * 1.6 : size, borderRadius: kind === 'drops' ? '50% 50% 50% 50% / 62% 62% 38% 38%' : '50%', background: kind === 'snow' ? '#FFFFFFCC' : col, opacity: fade * (kind === 'snow' ? 0.8 : 0.7), filter: `blur(${kind === 'embers' ? 1.5 : 0}px) drop-shadow(0 0 ${size}px ${col})` }} />;
      })}
    </>
  );
};

const Packets: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const y = HEIGHT - SAFE_BOTTOM - 110;
  return (
    <>
      <div style={{ position: 'absolute', left: 60, right: 60, top: y + 22, height: 2, background: `linear-gradient(90deg, transparent, ${col}66, transparent)` }} />
      {Array.from({ length: 7 }).map((_, i) => {
        const t = ((frame * 5 + i * 150) % 1100) / 1100;
        const x = -40 + t * (WIDTH + 80);
        const s = 22 + (i % 3) * 8;
        return <div key={i} style={{ position: 'absolute', left: x, top: y + 23 - s / 2, width: s, height: s, borderRadius: 5, background: col, opacity: interpolate(t, [0, 0.08, 0.92, 1], [0, 0.9, 0.9, 0], clamp), boxShadow: `0 0 18px ${col}` }} />;
      })}
    </>
  );
};

const Equalizer: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const bars = 17;
  const baseY = HEIGHT - SAFE_BOTTOM - 70;
  return (
    <>
      {Array.from({ length: bars }).map((_, i) => {
        const h = 24 + (Math.sin(frame / 5 + i * 0.9) * 0.5 + 0.5) * 120 * (0.5 + (Math.sin(frame / 17 + i) * 0.5 + 0.5) * 0.5);
        return <div key={i} style={{ position: 'absolute', left: 100 + i * 52, top: baseY - h, width: 28, height: h, borderRadius: 14, background: `linear-gradient(0deg, ${col}22, ${col}CC)`, opacity: 0.8, boxShadow: `0 0 16px ${col}55` }} />;
      })}
    </>
  );
};

const Signalbars: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const lit = Math.floor((frame / 12) % 6); // bars light one after another, then drop
  return (
    <div style={{ position: 'absolute', left: WIDTH - 330, top: SAFE_TOP + 250, display: 'flex', alignItems: 'flex-end', gap: 16, opacity: 0.9 }}>
      {[1, 2, 3, 4].map((b) => <div key={b} style={{ width: 34, height: 30 + b * 32, borderRadius: 9, background: b <= lit ? col : `${col}33`, boxShadow: b <= lit ? `0 0 20px ${col}` : 'none' }} />)}
    </div>
  );
};

const Notifications: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const cards = [{ icon: 'phone', title: 'Messages', body: 'New message' }, { icon: 'cloud', title: 'Mail', body: '3 new emails' }];
  return (
    <>
      {cards.map((c, i) => {
        const t0 = 8 + i * 34;
        const inP = interpolate(frame, [t0, t0 + 12], [0, 1], { ...clamp, easing: EASE_OUT });
        const outP = interpolate(frame, [t0 + 62, t0 + 76], [0, 1], clamp);
        if (frame < t0 || outP >= 1) return null;
        return (
          <div key={i} style={{ position: 'absolute', left: 90 + i * 30, width: 900, top: SAFE_TOP + 190 + i * 118 - (1 - inP) * 220, opacity: (1 - outP), transform: `translateX(${outP * 260}px)`, height: 100, borderRadius: 30, background: 'rgba(30,36,50,0.82)', border: '1px solid rgba(255,255,255,0.16)', display: 'flex', alignItems: 'center', gap: 22, padding: '0 26px', boxShadow: '0 20px 50px rgba(0,0,0,0.45)', backdropFilter: 'blur(10px)' }}>
            <div style={{ width: 62, height: 62, borderRadius: 16, background: `${col}22`, border: `1.5px solid ${col}`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg width={36} height={36} viewBox="0 0 48 48" fill="none" stroke={col} strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">{ICONS[c.icon]}</svg>
            </div>
            <div style={{ textAlign: 'left' }}>
              <div style={{ fontFamily: 'SF Pro Display, Helvetica, Arial, sans-serif', fontWeight: 800, fontSize: 28, color: '#fff' }}>{c.title}</div>
              <div style={{ fontFamily: 'SF Pro Display, Helvetica, Arial, sans-serif', fontWeight: 500, fontSize: 26, color: 'rgba(255,255,255,0.65)' }}>{c.body}</div>
            </div>
            <div style={{ marginLeft: 'auto', fontFamily: 'SF Pro Display, Helvetica, Arial, sans-serif', fontSize: 22, color: 'rgba(255,255,255,0.45)' }}>now</div>
          </div>
        );
      })}
    </>
  );
};

const BatteryFill: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const p = interpolate(frame, [10, 80], [0.08, 1], { ...clamp, easing: EASE_IO });
  const x = WIDTH / 2 - 150;
  const y = SAFE_TOP + 260;
  return (
    <div style={{ position: 'absolute', left: x, top: y, width: 300, height: 130, opacity: 0.92 }}>
      <div style={{ position: 'absolute', inset: 0, borderRadius: 30, border: `5px solid ${col}`, boxShadow: `0 0 28px ${col}66`, overflow: 'hidden' }}>
        <div style={{ width: `${p * 100}%`, height: '100%', background: `linear-gradient(90deg, ${col}77, ${col})` }} />
      </div>
      <div style={{ position: 'absolute', right: -22, top: 40, width: 18, height: 50, borderRadius: 8, background: col }} />
      <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'JetBrains Mono, Menlo, monospace', fontWeight: 700, fontSize: 52, color: '#05070C', mixBlendMode: 'normal' }}>{Math.round(p * 100)}%</div>
    </div>
  );
};

const ClockFx: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const cx = WIDTH - 250;
  const cy = SAFE_TOP + 330;
  return (
    <svg width={300} height={300} viewBox="-150 -150 300 300" style={{ position: 'absolute', left: cx - 150, top: cy - 150, opacity: 0.85, filter: `drop-shadow(0 0 16px ${col})` }}>
      <circle r={118} fill="rgba(8,18,40,0.55)" stroke={col} strokeWidth={6} />
      {Array.from({ length: 12 }).map((_, i) => <line key={i} x1={0} y1={-100} x2={0} y2={-112} stroke={col} strokeWidth={5} transform={`rotate(${i * 30})`} />)}
      <line x1={0} y1={0} x2={0} y2={-92} stroke={col} strokeWidth={5} strokeLinecap="round" transform={`rotate(${frame * 9})`} />
      <line x1={0} y1={0} x2={0} y2={-60} stroke="#fff" strokeWidth={7} strokeLinecap="round" transform={`rotate(${frame * 0.75})`} />
      <circle r={9} fill={col} />
    </svg>
  );
};

const Padlock: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const snap = interpolate(frame, [18, 26], [0, 1], { ...clamp, easing: EASE_OUT });
  const pop = interpolate(frame, [26, 30, 46], [1, 1.18, 1], clamp);
  const cx = 200;
  const cy = SAFE_TOP + 340;
  const ring = interpolate(frame, [26, 52], [0, 1], clamp);
  return (
    <>
      <div style={{ position: 'absolute', left: cx - 40 - ring * 120, top: cy - 40 - ring * 120, width: 80 + ring * 240, height: 80 + ring * 240, borderRadius: '50%', border: `4px solid ${col}`, opacity: (1 - ring) * (frame >= 26 ? 1 : 0) }} />
      <svg width={190} height={190} viewBox="0 0 48 48" fill="none" stroke={col} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" style={{ position: 'absolute', left: cx - 95, top: cy - 95 - (1 - snap) * 8, transform: `scale(${pop})`, filter: `drop-shadow(0 0 18px ${col})` }}>
        <rect x="9" y="21" width="30" height="21" rx="4" />
        <circle cx="24" cy="31" r="3" />
        <path d={`M15 21v${-6 - (1 - snap) * 9}a9 9 0 0 1 18 0v${6 + (1 - snap) * 9}`} />
      </svg>
    </>
  );
};

const Magnify: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const { p, live } = passes(frame, 10, 90, 20);
  if (!live) return null;
  const x = 140 + p * (WIDTH - 280);
  const y = SAFE_TOP + 360 + Math.sin(p * Math.PI * 2) * 40;
  return (
    <svg width={220} height={220} viewBox="0 0 48 48" fill="none" stroke={col} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" style={{ position: 'absolute', left: x - 110, top: y - 110, filter: `drop-shadow(0 0 18px ${col})` }}>
      <circle cx="20" cy="20" r="13" fill={`${col}18`} />
      {g2('M30 30l14 14')}
    </svg>
  );
};
const g2 = (d: string) => <path d={d} />;

const Bits: React.FC<{ accent: string; light: boolean }> = ({ accent, light }) => {
  const frame = useCurrentFrame();
  const col = light ? '#0A1220' : accent;
  const cols = 9;
  return (
    <>
      {Array.from({ length: cols }).map((_, c) => {
        const x = c < 5 ? 30 + c * 50 : WIDTH - 30 - (c - 4) * 50;
        const speed = 3 + random(`bs${c}`) * 3;
        const travel = (frame * speed + random(`bo${c}`) * 900) % 1100;
        return (
          <div key={c} style={{ position: 'absolute', left: x, top: SAFE_TOP + travel - 200, fontFamily: 'JetBrains Mono, Menlo, monospace', fontSize: 34, lineHeight: 1.3, color: col, opacity: 0.35, textAlign: 'center', whiteSpace: 'pre' }}>
            {Array.from({ length: 6 }).map((_, r) => `${random(`b${c}-${r}-${Math.floor(frame / 9) + r}`) > 0.5 ? 1 : 0}\n`).join('')}
          </div>
        );
      })}
    </>
  );
};

export const Ambient: React.FC<{ fx: SceneFx | null }> = ({ fx }) => {
  const { theme, light } = useTheme();
  if (!fx) return null;
  const props = { accent: theme.accent, light };
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      {fx === 'plane' && <Plane {...props} />}
      {fx === 'rocket' && <Rocket {...props} />}
      {fx === 'satellite' && <Satellite {...props} />}
      {fx === 'waves' && <Waves {...props} />}
      {fx === 'bolts' && <Bolts {...props} />}
      {(fx === 'embers' || fx === 'snow' || fx === 'drops' || fx === 'coins') && <Particles kind={fx} {...props} />}
      {fx === 'packets' && <Packets {...props} />}
      {fx === 'equalizer' && <Equalizer {...props} />}
      {fx === 'signalbars' && <Signalbars {...props} />}
      {fx === 'notifications' && <Notifications {...props} />}
      {fx === 'batteryfill' && <BatteryFill {...props} />}
      {fx === 'clock' && <ClockFx {...props} />}
      {fx === 'padlock' && <Padlock {...props} />}
      {fx === 'magnify' && <Magnify {...props} />}
      {fx === 'bits' && <Bits {...props} />}
    </AbsoluteFill>
  );
};
