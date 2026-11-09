import React from 'react';
import { AbsoluteFill, interpolate, random, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { EASE_OUT, clamp, useTheme } from './primitives';
import { BRAND_BLUE, MotionScene } from './types';

/** Thematic objects: neon line icons (48x48 grid) that pop in around the text and float, picked from what the scene talks about. */
const g = (...d: string[]) => d.map((p, i) => <path key={i} d={p} />);

export const ICONS: Record<string, React.ReactNode> = {
  chip: <>{g('M18 6v6M24 6v6M30 6v6M18 36v6M24 36v6M30 36v6M6 18h6M6 24h6M6 30h6M36 18h6M36 24h6M36 30h6')}<rect x="12" y="12" width="24" height="24" rx="3" /><rect x="19" y="19" width="10" height="10" rx="1.5" /></>,
  gpu: <><rect x="4" y="12" width="40" height="22" rx="3" /><circle cx="17" cy="23" r="6" /><circle cx="32" cy="23" r="6" />{g('M4 38h30', 'M17 17v12M11 23h12')}</>,
  ram: <><rect x="4" y="13" width="40" height="19" rx="2" /><rect x="9" y="18" width="8" height="9" /><rect x="20" y="18" width="8" height="9" /><rect x="31" y="18" width="8" height="9" />{g('M9 32v6M15 32v6M21 32v6M27 32v6M33 32v6M39 32v6')}</>,
  battery: <><rect x="5" y="14" width="33" height="20" rx="3.5" />{g('M38 21h5v6h-5', 'M11 20v8M18 20v8M25 20v8')}</>,
  bolt: g('M27 3L10 27h12l-3 18 19-25H26z'),
  wifi: <>{g('M5 19a27 27 0 0 1 38 0', 'M11 26a18 18 0 0 1 26 0', 'M17 33a9 9 0 0 1 14 0')}<circle cx="24" cy="39" r="2.4" /></>,
  globe: <><circle cx="24" cy="24" r="19" /><ellipse cx="24" cy="24" rx="8" ry="19" />{g('M5 24h38', 'M8 14h32', 'M8 34h32')}</>,
  cloud: g('M14 37a9 9 0 0 1-1-18 12 12 0 0 1 23 3 7.5 7.5 0 0 1 0 15z'),
  server: <><rect x="6" y="6" width="36" height="11" rx="3" /><rect x="6" y="20" width="36" height="11" rx="3" /><rect x="6" y="34" width="36" height="9" rx="3" /><circle cx="13" cy="11.5" r="1.6" /><circle cx="13" cy="25.5" r="1.6" /><circle cx="13" cy="38.5" r="1.6" /></>,
  disk: <><rect x="3" y="14" width="42" height="20" rx="2.5" /><rect x="13" y="19" width="9" height="10" rx="1" /><rect x="25" y="19" width="9" height="10" rx="1" /><rect x="37" y="21" width="4" height="6" rx="1" />{g('M3 20h4M3 24h4M3 28h4')}</>,
  lock: <><rect x="9" y="21" width="30" height="21" rx="4" /><circle cx="24" cy="31" r="3" />{g('M15 21v-6a9 9 0 0 1 18 0v6')}</>,
  key: <><circle cx="14" cy="24" r="8" />{g('M22 24h22', 'M36 24v8', 'M42 24v6')}</>,
  shield: g('M24 4L8 10v12c0 11 7 18 16 22 9-4 16-11 16-22V10z', 'M16 24l6 6 11-13'),
  thermometer: g('M19 8a5 5 0 0 1 10 0v21a9 9 0 1 1-10 0z', 'M24 16v19'),
  flame: g('M24 3c2 9 13 13 13 26a13 13 0 0 1-26 0c0-7 4-9 6-15 3 2 5 5 5 8 2-4 3-10 2-19z'),
  fan: <><circle cx="24" cy="24" r="3.5" /><circle cx="24" cy="24" r="20" />{[0, 120, 240].map((r) => <path key={r} transform={`rotate(${r} 24 24)`} d="M24 20C22 11 29 6 35 9c2 6-3 11-9 13z" />)}</>,
  gauge: <>{g('M6 35a18 18 0 1 1 36 0', 'M24 35l8-13', 'M10 35h3M35 35h3M24 17v3')}<circle cx="24" cy="35" r="2.4" /></>,
  clock: g('M24 5a19 19 0 1 0 .01 0z', 'M24 12v13l9 5'),
  code: g('M16 13L5 24l11 11', 'M32 13l11 11-11 11', 'M28 8l-8 32'),
  brain: g('M24 9C20 3 10 5 10 14c-6 2-6 11 0 13-2 7 6 12 14 8z', 'M24 9c4-6 14-4 14 5 6 2 6 11 0 13 2 7-6 12-14 8z', 'M24 9v26'),
  bulb: g('M24 4a14 14 0 0 0-8 26v5h16v-5A14 14 0 0 0 24 4z', 'M18 40h12', 'M20 44h8'),
  dollar: g('M24 5a19 19 0 1 0 .01 0z', 'M30 17c-1-4-10-5-11 0-1 6 12 3 11 10-1 5-10 5-12 0', 'M24 10v28'),
  skull: <>{g('M24 4C12 4 8 13 10 22c1 4 4 5 4 9v6h20v-6c0-4 3-5 4-9 2-9-2-18-14-18z', 'M21 37v-4M27 37v-4')}<circle cx="18" cy="23" r="3.6" /><circle cx="30" cy="23" r="3.6" /></>,
  warning: <>{g('M24 5L44 40H4z', 'M24 18v12')}<circle cx="24" cy="35" r="1.6" /></>,
  controller: <>{g('M14 13h20c8 0 12 10 11 21-1 5-6 5-9 1l-3-5H15l-3 5c-3 4-8 4-9-1C2 23 6 13 14 13z', 'M15 20v8M11 24h8')}<circle cx="31" cy="21" r="1.9" /><circle cx="36" cy="26" r="1.9" /></>,
  monitor: <><rect x="4" y="7" width="40" height="27" rx="3" />{g('M16 42h16', 'M24 34v8')}</>,
  phone: <><rect x="13" y="3" width="22" height="42" rx="5" />{g('M20 39h8')}</>,
  camera: <><rect x="4" y="12" width="40" height="28" rx="5" /><circle cx="24" cy="26" r="8" />{g('M16 12l3-5h10l3 5')}</>,
  wave: g('M7 20v8M14 11v26M21 5v38M28 13v22M35 18v12M42 22v4'),
  planet: <><circle cx="24" cy="24" r="11" /><ellipse cx="24" cy="24" rx="22" ry="7" transform="rotate(-22 24 24)" /></>,
  rocket: <>{g('M24 3c8 6 10 17 8 27H16C14 20 16 9 24 3z', 'M16 30l-7 9 9-2', 'M32 30l7 9-9-2', 'M20 37l4 8 4-8')}<circle cx="24" cy="17" r="3.4" /></>,
  atom: <><ellipse cx="24" cy="24" rx="20" ry="8" /><ellipse cx="24" cy="24" rx="20" ry="8" transform="rotate(60 24 24)" /><ellipse cx="24" cy="24" rx="20" ry="8" transform="rotate(-60 24 24)" /><circle cx="24" cy="24" r="3" fill="currentColor" /></>,
  magnet: g('M10 5v19a14 14 0 0 0 28 0V5H28v19a4 4 0 0 1-8 0V5z', 'M10 13h10M28 13h10'),
  droplet: g('M24 4C14 18 9 24 9 31a15 15 0 0 0 30 0c0-7-5-13-15-27z'),
  snow: g('M24 4v40M7 14l34 20M7 34l34-20', 'M19 7l5 4 5-4M19 41l5-4 5 4'),
  heart: g('M24 42C5 28 5 12 16 9c5-1 8 2 8 6 0-4 3-7 8-6 11 3 11 19-8 33z'),
  search: <><circle cx="20" cy="20" r="13" />{g('M30 30l14 14')}</>,
  check: g('M24 5a19 19 0 1 0 .01 0z', 'M14 25l7 7 14-15'),
  cross: g('M24 5a19 19 0 1 0 .01 0z', 'M16 16l16 16M32 16L16 32'),
  gear: <><circle cx="24" cy="24" r="6.5" /><circle cx="24" cy="24" r="14" />{g('M24 4v6M24 38v6M4 24h6M38 24h6M10 10l4 4M34 34l4 4M38 10l-4 4M14 34l-4 4')}</>,
  star: g('M24 4l6 13 14 2-10 10 3 14-13-7-13 7 3-14L4 19l14-2z'),
  net: <><circle cx="24" cy="10" r="5" /><circle cx="9" cy="36" r="5" /><circle cx="39" cy="36" r="5" />{g('M21 14L12 32M27 14l9 18M14 36h20')}</>,
  arrow: g('M24 42V8M10 22L24 8l14 14'),
  bluetooth: g('M12 16l24 16-12 10V6l12 10L12 32'),
  airdrop: <><circle cx="24" cy="30" r="3" />{g('M15 31a12 12 0 1 1 18 0', 'M9 37a20 20 0 1 1 30 0')}</>,
  plane: g('M24 3c2 0 3 2 3 5v10l16 10v5l-16-4v8l5 4v4l-8-2-8 2v-4l5-4v-8L5 33v-5l16-10V8c0-3 1-5 3-5z'),
  satellite: <><rect x="19" y="19" width="10" height="10" rx="1.5" transform="rotate(45 24 24)" />{g('M5 21l9-9 6 6-9 9z', 'M28 30l9-9 6 6-9 9z', 'M30 12l4-4M34 16l4-4')}</>,
};

/** Keyword -> icons. First matches win; everything is matched against the scene's own words, so the objects always relate to what is being said. */
const RULES: [RegExp, string[]][] = [
  [/\b(air ?planes?|aeroplanes?|planes?|flights?|flying|fly|airlines?|airports?|aircraft|aviation|pilots?|jets?)\b/i, ['plane']],
  [/\b(satellites?|gps|orbit\w*)\b/i, ['satellite']],
  [/\b(cpu|processor|cores?|threads?|silicon|chips?|transistors?|nanomet\w*|nm|die|architecture)\b/i, ['chip']],
  [/\b(gpu|graphics|shaders?|ray ?trac\w*|fps|frames?|render\w*|nvidia|radeon|vram)\b/i, ['gpu']],
  [/\b(ram|dram|memory|cache|bandwidth|ddr\d?)\b/i, ['ram']],
  [/\b(battery|batteries|charg\w*|watts?|energy|voltage|electric\w*|power)\b/i, ['battery', 'bolt']],
  [/\b(ssd|nand|flash|storage|drives?|disks?|hdd|files?|cells?|writes?|nvme)\b/i, ['disk']],
  [/\b(wi-?fi|wireless|signal|bluetooth|5g|latency|ping|packets?|router)\b/i, ['wifi']],
  [/\b(internet|web|online|cloud|data ?cent\w*|servers?|bandwidth)\b/i, ['globe', 'cloud', 'server']],
  [/\b(lock\w*|encrypt\w*|password\w*|secur\w*|hack\w*|privacy|cipher|malware)\b/i, ['lock', 'shield', 'key']],
  [/\b(heat\w*|hot|thermal|temperature|cool\w*|throttl\w*|overheat\w*|melt\w*)\b/i, ['thermometer', 'flame', 'fan']],
  [/\b(speed\w*|fast\w*|quick\w*|boost\w*|overclock\w*|accelerat\w*|instant\w*|turbo)\b/i, ['gauge', 'bolt']],
  [/\b(time|seconds?|milliseconds?|nanoseconds?|years?|decades?|hours?|clock|ticks?)\b/i, ['clock']],
  [/\b(code|bugs?|software|programs?|scripts?|compil\w*|apis?|binary|algorithm\w*|loops?|function\w*)\b/i, ['code']],
  [/\b(ai|neural|brain|learn\w*|model\w*|think\w*|smart|intelligen\w*|train\w*)\b/i, ['brain', 'bulb']],
  [/\b(idea|trick|clever|secret|hidden|clue|discover\w*|find|found|search\w*)\b/i, ['search', 'bulb']],
  [/\b(money|costs?|prices?|cheap\w*|expensive|dollars?|billions?|millions?|pay\w*)\b/i, ['dollar']],
  [/\b(dead|death|die|dies|crash\w*|fail\w*|kill\w*|wear\w*|broke\w*|corrupt\w*)\b/i, ['skull', 'warning']],
  [/\b(games?|gaming|players?|consoles?|playing|levels?|bosses|speedrun\w*|skyrim|doom|zelda)\b/i, ['controller']],
  [/\b(screens?|display\w*|monitors?|pixels?|refresh|hz|oled|resolution|4k)\b/i, ['monitor']],
  [/\b(phones?|mobile|iphone|android|smartphone)\b/i, ['phone']],
  [/\b(camera\w*|photo\w*|lens\w*|sensors?|image\w*)\b/i, ['camera']],
  [/\b(sound|audio|music|voices?|noise|echo)\b/i, ['wave']],
  [/\b(space|nasa|satellite\w*|orbit\w*|planets?|moon|mars)\b/i, ['planet', 'rocket']],
  [/\b(quantum|atoms?|physics|particles?|electrons?|photons?|qubits?)\b/i, ['atom']],
  [/\b(magnet\w*)\b/i, ['magnet']],
  [/\b(water|liquid|flood\w*|coolant)\b/i, ['droplet']],
  [/\b(cold|freez\w*|ice|nitrogen|frozen)\b/i, ['snow']],
  [/\b(love|heart|care)\b/i, ['heart']],
  [/\b(network\w*|connect\w*|nodes?|mesh)\b/i, ['net']],
  [/\b(rocket|launch\w*|ship\w*|lift ?off)\b/i, ['rocket']],
  [/\b(engines?|gears?|mechanic\w*|machines?|build\w*|works?)\b/i, ['gear']],
  [/\b(true|facts?|correct|real|proof|verified)\b/i, ['check']],
  [/\b(false|myths?|wrong|lie|fake|never)\b/i, ['cross']],
];

const TYPE_FALLBACK: Partial<Record<MotionScene['type'], string[]>> = { counter: ['gauge'], progressBar: ['battery'], curve: ['arrow'], codeBlock: ['code'], outro: ['star', 'bolt'] };
const NO_PROPS = new Set(['footage', 'flash', 'tier', 'timeline', 'versus', 'verdict', 'codeBlock', 'ui']); // a drawn interface fills the scene: no floating icon tiles

export const pickIcons = (scene: MotionScene, prev: string[] = []): string[] => {
  const explicit = (scene.icons ?? []).filter((n) => ICONS[n]);
  if (explicit.length) return explicit.slice(0, 4);
  if (NO_PROPS.has(scene.type)) return [];
  const hay = [scene.text, scene.accentText, scene.kicker, scene.unit, scene.narration, ...(scene.items ?? [])].filter(Boolean).join(' ');
  const found: string[] = [];
  for (const [re, names] of RULES) {
    if (re.test(hay)) for (const n of names) if (!found.includes(n)) found.push(n);
    if (found.length >= 6) break;
  }
  if (!found.length) found.push(...(TYPE_FALLBACK[scene.type] ?? []));
  // never repeat what the previous scene just showed: a scene with nothing new shows no tiles instead of the same ones
  const fresh = found.filter((n) => !prev.includes(n));
  return (scene.type === 'outro' ? found : fresh).slice(0, 3);
};

// Tiles sit in a free row under the text (centred by count); the first icon also appears huge and ghosted behind the text.
const rowSlot = (i: number, n: number): [number, number, number] => {
  const gap = n === 1 ? 0 : n === 2 ? 300 : 300;
  return [540 + (i - (n - 1) / 2) * gap, 1450, n === 1 ? 220 : 190];
};

const Prop: React.FC<{ name: string; slot: number; count: number; seed: number; delay: number }> = ({ name, slot, count, seed, delay }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const [x, sy, size] = rowSlot(slot, count);
  const pop = spring({ frame: frame - delay, fps, config: { damping: 9, stiffness: 120, mass: 0.8 } });
  const t = frame / fps;
  const ph = random(`ph${seed}`) * 6.28;
  const bobY = Math.sin(t * 1.9 + ph) * 18;
  const bobX = Math.cos(t * 1.3 + ph) * 10;
  const tilt = Math.sin(t * 1.4 + ph) * 7 + (1 - pop) * -50;
  const spin = (frame * 1.6 + ph * 40) % 360;
  const col = light ? '#0A1220' : theme.accent;
  const ring = interpolate(frame - delay, [0, 24], [0, 1], { ...clamp, easing: EASE_OUT });
  const out = size * 0.62;
  return (
    <div style={{ position: 'absolute', left: x - size / 2 + bobX, top: sy - size / 2 + bobY, width: size, height: size, opacity: Math.min(1, pop * 1.4), transform: `scale(${0.2 + 0.8 * pop}) rotate(${tilt}deg)` }}>
      <div style={{ position: 'absolute', inset: 0, borderRadius: '50%', background: light ? 'rgba(255,255,255,0.7)' : `radial-gradient(circle at 35% 30%, ${theme.accent}33, rgba(8,18,40,0.82) 70%)`, border: `2px solid ${col}66`, boxShadow: light ? '0 18px 50px rgba(20,50,90,0.25)' : `0 0 ${size * 0.28}px ${theme.accent}55, inset 0 0 ${size * 0.2}px ${BRAND_BLUE}44` }} />
      <svg width={size} height={size} viewBox="0 0 100 100" style={{ position: 'absolute', inset: 0, transform: `rotate(${spin}deg)` }}>
        <circle cx="50" cy="50" r="47" fill="none" stroke={col} strokeOpacity={0.55} strokeWidth="1.4" strokeDasharray="3 6" pathLength={100} strokeDashoffset={100 - 100 * ring} />
        <circle cx="50" cy="3" r="2.6" fill={col} style={{ filter: `drop-shadow(0 0 4px ${col})` }} />
      </svg>
      <svg width={out} height={out} viewBox="0 0 48 48" fill="none" stroke={col} strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round" style={{ position: 'absolute', left: (size - out) / 2, top: (size - out) / 2, color: col, filter: light ? 'none' : `drop-shadow(0 0 ${size * 0.05}px ${theme.accent})` }}>
        {ICONS[name]}
      </svg>
    </div>
  );
};

/** Big translucent icon behind the text, slowly turning and breathing. */
const Ghost: React.FC<{ name: string; index: number }> = ({ name, index }) => {
  const frame = useCurrentFrame();
  const { theme, light } = useTheme();
  const p = interpolate(frame, [4, 28], [0, 1], { ...clamp, easing: EASE_OUT });
  const side = index % 2 === 0 ? 1 : -1;
  const col = light ? '#0A1220' : theme.accent;
  return (
    <div style={{ position: 'absolute', left: 540 + side * 150 - 330, top: 900 - 330, width: 660, height: 660, opacity: p * (light ? 0.12 : 0.2), transform: `scale(${0.7 + 0.3 * p + Math.sin(frame / 22) * 0.025}) rotate(${side * (frame * 0.35 - 12)}deg)` }}>
      <svg width="660" height="660" viewBox="0 0 48 48" fill="none" stroke={col} strokeWidth={0.9} strokeLinecap="round" strokeLinejoin="round" style={{ filter: light ? 'none' : `drop-shadow(0 0 14px ${theme.accent})` }}>{ICONS[name]}</svg>
    </div>
  );
};

export const PropField: React.FC<{ icons: string[]; index: number }> = ({ icons, index }) => {
  if (!icons.length) return null;
  return (
    <AbsoluteFill style={{ pointerEvents: 'none' }}>
      <Ghost name={icons[0]} index={index} />
      {icons.map((name, i) => (
        <Prop key={name + i} name={name} slot={i} count={icons.length} seed={index * 7 + i} delay={6 + i * 7} />
      ))}
    </AbsoluteFill>
  );
};
