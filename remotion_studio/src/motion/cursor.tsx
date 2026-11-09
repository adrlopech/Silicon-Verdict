import React, { useLayoutEffect, useRef, useState } from 'react';
import { delayRender, continueRender, interpolate, useCurrentFrame } from 'remotion';
import { EASE_IO, EASE_OUT, clamp } from './primitives';
import { ICONS } from './props';
import { MONO, SANS } from './fonts';
import { CursorAction, HEIGHT, MotionScene, SAFE_BOTTOM, SAFE_TOP, ToggleKey, WIDTH } from './types';

/**
 * The channel's character is a mouse cursor. It lives on top of the scenes and USES them like a person would use a web page:
 *   click  - glides to the key text, presses (ripple) and the text answers with a pulse
 *   hover  - rests on the key text, which gets a focus outline
 *   select - drags across the headline like selecting text with the mouse
 *   drag   - grabs a list item / code panel / bar and drags it a little
 *   tab    - clicks "+" on a browser tab strip and a new tab opens (used to start a video)
 *   toggle - a macOS-style Control Center panel opens and the cursor flips a switch (Airplane Mode turns Wi-Fi and Bluetooth off)
 *   busy   - turns into a loading ring beside the text (a thinking beat)
 *   idle   - waits in a bottom corner
 * Targets are measured from the DOM (elements tagged data-cursor), so the cursor always lands on what is really on screen.
 */

type Box = { x: number; y: number; w: number; h: number };
type Targets = Partial<Record<'text' | 'accent' | 'item' | 'number' | 'code' | 'bar', Box[]>>;
const KINDS = ['text', 'accent', 'item', 'number', 'code', 'bar'] as const;

/** Rects (in 1080x1920 composition pixels) of the tagged elements of one scene. */
const measure = (sceneIndex: number): Targets | null => {
  const root = document.querySelector('[data-cursor-root]');
  if (!root) return null;
  const rr = root.getBoundingClientRect();
  const k = rr.width / WIDTH || 1;
  const sceneEl = root.querySelector(`[data-scene="${sceneIndex}"]`);
  if (!sceneEl) return null;
  const out: Targets = {};
  for (const kind of KINDS) {
    out[kind] = Array.from(sceneEl.querySelectorAll(`[data-cursor="${kind}"]`)).map((e) => {
      const r = e.getBoundingClientRect();
      return { x: (r.left - rr.left) / k, y: (r.top - rr.top) / k, w: r.width / k, h: r.height / k };
    });
  }
  return out;
};

const same = (a: Targets | null, b: Targets | null) => JSON.stringify(a) === JSON.stringify(b);
const mix = (a: number, b: number, t: number) => a + (b - a) * t;
const ease = (f: number, from: number, to: number) => interpolate(f, [from, to], [0, 1], { ...clamp, easing: EASE_IO });

const REST_Y = HEIGHT - SAFE_BOTTOM - 60;
const restFor = (side: number) => ({ x: side > 0 ? 96 : WIDTH - 96, y: REST_Y });

/** Which corner the cursor rests in for each scene (alternating among the scenes that have it); 0 = no cursor. */
export const cursorSides = (scenes: MotionScene[]): number[] => {
  let n = 0;
  return scenes.map((s) => (s.cursor && s.type !== 'flash' ? (n++ % 2 === 0 ? 1 : -1) : 0));
};

/** The channel pointer, the same one as the YouTube banner (scripts/make_brand_assets.py `cursor_arrow`): a long, slim arrow with rounded corners and a thin dark outline.
 *  The outline is a thicker round-joined stroke under the white body; the same stroke on the body rounds its corners (radius = half the stroke width). The tip rests at (2, 2). */
const ARROW = 'M2.1 2.1 L2.1 34.1 L10.3 27.3 L17.3 45.1 L22.9 42.9 L16.3 25.7 L27.1 25.5 Z';
const ARROW_ROUND = 4.2; // stroke width of the white body = 2 x the corner radius
const ARROW_OUTLINE = 1.5; // dark outline on each side of the body

const Arrow: React.FC<{ x: number; y: number; scale: number; accent: string; press: number }> = ({ x, y, scale, accent, press }) => (
  <svg width={120} height={150} viewBox="-6 -6 48 60" style={{ position: 'absolute', left: x - 6 * 2.5, top: y - 6 * 2.5, overflow: 'visible', transform: `scale(${scale * (1 - 0.14 * press)})`, transformOrigin: '6px 6px', filter: `drop-shadow(0 0 14px ${accent}AA) drop-shadow(0 6px 10px rgba(0,0,0,0.55))` }}>
    <path d={ARROW} fill="#05070C" stroke="#05070C" strokeWidth={ARROW_ROUND + 2 * ARROW_OUTLINE} strokeLinejoin="round" />
    <path d={ARROW} fill="#FFFFFF" stroke="#FFFFFF" strokeWidth={ARROW_ROUND} strokeLinejoin="round" />
  </svg>
);

const Ripple: React.FC<{ x: number; y: number; t: number; accent: string }> = ({ x, y, t, accent }) => {
  if (t < 0 || t > 1) return null;
  return (
    <>
      {[0, 0.28].map((d, i) => {
        const p = Math.max(0, Math.min(1, (t - d) / (1 - d)));
        if (p <= 0) return null;
        const r = 18 + p * 110;
        return <div key={i} style={{ position: 'absolute', left: x - r, top: y - r, width: r * 2, height: r * 2, borderRadius: r, border: `${5 - p * 3}px solid ${accent}`, opacity: (1 - p) * 0.9, boxShadow: `0 0 24px ${accent}88` }} />;
      })}
    </>
  );
};

const Spinner: React.FC<{ x: number; y: number; frame: number; accent: string }> = ({ x, y, frame, accent }) => (
  <svg width={110} height={110} viewBox="-55 -55 110 110" style={{ position: 'absolute', left: x - 22, top: y - 22, overflow: 'visible', filter: `drop-shadow(0 0 14px ${accent}CC)` }}>
    <circle r={34} fill="rgba(5,7,12,0.65)" stroke="rgba(255,255,255,0.25)" strokeWidth={6} />
    <circle r={34} fill="none" stroke={accent} strokeWidth={8} strokeLinecap="round" strokeDasharray="70 150" transform={`rotate(${frame * 14})`} />
  </svg>
);

const Focus: React.FC<{ box: Box; t: number; accent: string; pulse?: number }> = ({ box, t, accent, pulse = 0 }) => {
  const pad = 22;
  return (
    <div style={{ position: 'absolute', left: box.x - pad, top: box.y - pad * 0.6, width: box.w + pad * 2, height: box.h + pad * 1.2, borderRadius: 22, border: `3px solid ${accent}`, background: `${accent}${pulse > 0 ? '22' : '12'}`, opacity: t, boxShadow: `0 0 ${30 + pulse * 40}px ${accent}66`, transform: `scale(${1 + pulse * 0.02})` }} />
  );
};

/** Browser-style tab strip; the cursor clicks "+" and a new tab opens with the video's title. */
const TAB_W = 300;
const tabGeometry = () => {
  const left = (WIDTH - 900) / 2;
  const top = SAFE_TOP + 96;
  return { left, top, plusX: left + 24 + TAB_W + 62, plusY: top + 38 };
};
const TabStrip: React.FC<{ t: number; open: number; title: string; accent: string }> = ({ t, open, title, accent }) => {
  const g = tabGeometry();
  const tab = (label: string, active: boolean, w: number, k: number) => (
    <div style={{ width: w * k, height: 62, borderRadius: '18px 18px 0 0', background: active ? 'rgba(18,34,64,0.95)' : 'rgba(255,255,255,0.07)', border: `1px solid ${active ? accent + '88' : 'rgba(255,255,255,0.12)'}`, borderBottom: 'none', display: 'flex', alignItems: 'center', gap: 12, padding: '0 18px', overflow: 'hidden', opacity: k, boxShadow: active ? `0 -6px 30px ${accent}33` : 'none', flexShrink: 0 }}>
      <div style={{ width: 20, height: 20, borderRadius: 10, background: active ? accent : 'rgba(255,255,255,0.4)', flexShrink: 0 }} />
      <span style={{ fontFamily: SANS, fontWeight: 700, fontSize: 24, color: active ? '#fff' : 'rgba(255,255,255,0.5)', whiteSpace: 'nowrap', textOverflow: 'ellipsis', overflow: 'hidden' }}>{label}</span>
      <span style={{ marginLeft: 'auto', fontFamily: MONO, fontSize: 22, color: 'rgba(255,255,255,0.35)' }}>×</span>
    </div>
  );
  return (
    <div style={{ position: 'absolute', left: g.left, top: g.top, width: 900, height: 76, opacity: t, transform: `translateY(${(1 - t) * -20}px)` }}>
      <div style={{ position: 'absolute', inset: 0, borderRadius: 24, background: 'rgba(8,14,28,0.78)', border: `1px solid ${accent}33`, backdropFilter: 'blur(6px)' }} />
      <div style={{ position: 'absolute', left: 24, top: 14, display: 'flex', gap: 10, alignItems: 'flex-end' }}>
        {tab('silicon verdict', open < 0.5, TAB_W, 1)}
        {tab(title.toLowerCase(), true, TAB_W, interpolate(open, [0, 1], [0.001, 1], clamp))}
        <div style={{ width: 56, height: 56, borderRadius: 28, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: SANS, fontSize: 40, fontWeight: 600, color: accent, marginLeft: 6, background: open > 0 && open < 0.2 ? `${accent}33` : 'transparent' }}>+</div>
      </div>
    </div>
  );
};


/** macOS-style Control Center: glass tiles for Wi-Fi, Bluetooth, AirDrop and Airplane Mode, and a brightness slider. The cursor flips one of the switches. */
const CC = { left: 80, width: 920, top: HEIGHT - SAFE_BOTTOM - 410 - 10, height: 410, tileW: 204, tileH: 206, gap: 20, pad: 26 };
const TILES: { key: ToggleKey; icon: string; label: string; on: string; off: string }[] = [
  { key: 'wifi', icon: 'wifi', label: 'Wi-Fi', on: 'Home Network', off: 'Off' },
  { key: 'bluetooth', icon: 'bluetooth', label: 'Bluetooth', on: 'On', off: 'Off' },
  { key: 'airdrop', icon: 'airdrop', label: 'AirDrop', on: 'Contacts Only', off: 'Off' },
  { key: 'airplane', icon: 'plane', label: 'Airplane Mode', on: 'On', off: 'Off' },
];
const tileCenter = (key: ToggleKey) => {
  const i = TILES.findIndex((t) => t.key === key);
  return { x: CC.left + CC.pad + i * (CC.tileW + CC.gap) + CC.tileW / 2, y: CC.top + CC.pad + CC.tileH * 0.42 };
};

const ControlCenter: React.FC<{ t: number; f: number; clickAt: number; which: ToggleKey }> = ({ t, f, clickAt, which }) => {
  const flip = (delay: number) => interpolate(f, [clickAt + delay, clickAt + delay + 6], [0, 1], clamp);
  // how "on" each tile is: Wi-Fi, Bluetooth and AirDrop start on; Airplane starts off. Airplane Mode flips itself on and the three radios off, one after another.
  const state: Record<ToggleKey, number> = {
    wifi: which === 'airplane' ? 1 - flip(12) : which === 'wifi' ? 1 - flip(0) : 1,
    bluetooth: which === 'airplane' ? 1 - flip(19) : which === 'bluetooth' ? 1 - flip(0) : 1,
    airdrop: which === 'airplane' ? 1 - flip(26) : which === 'airdrop' ? 1 - flip(0) : 1,
    airplane: which === 'airplane' ? flip(0) : 0,
  };
  return (
    <div style={{ position: 'absolute', left: CC.left, top: CC.top, width: CC.width, height: CC.height, opacity: t, transform: `translateY(${(1 - t) * 70}px) scale(${0.96 + 0.04 * t})`, borderRadius: 58, background: 'linear-gradient(160deg, rgba(40,46,60,0.82), rgba(14,18,28,0.88))', border: '1.5px solid rgba(255,255,255,0.16)', boxShadow: '0 40px 100px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.12)', backdropFilter: 'blur(14px)' }}>
      {TILES.map((tile, i) => {
        const k = state[tile.key];
        const airplane = tile.key === 'airplane';
        const circle = airplane ? `rgba(255,159,10,${0.0 + k})` : `rgba(255,255,255,${0.14 + 0.86 * k})`;
        const iconColor = airplane ? (k > 0.5 ? '#FFFFFF' : 'rgba(255,255,255,0.75)') : k > 0.5 ? '#0A84FF' : 'rgba(255,255,255,0.7)';
        const press = tile.key === which ? interpolate(f, [clickAt - 2, clickAt + 1, clickAt + 8], [0, 1, 0], clamp) : 0;
        return (
          <div key={tile.key} style={{ position: 'absolute', left: CC.pad + i * (CC.tileW + CC.gap), top: CC.pad, width: CC.tileW, height: CC.tileH, borderRadius: 44, background: 'rgba(255,255,255,0.09)', border: '1px solid rgba(255,255,255,0.1)', transform: `scale(${1 - 0.04 * press})` }}>
            <div style={{ position: 'absolute', left: (CC.tileW - 100) / 2, top: 24, width: 100, height: 100, borderRadius: 50, background: airplane && k < 0.02 ? 'rgba(255,255,255,0.14)' : circle, display: 'flex', alignItems: 'center', justifyContent: 'center', boxShadow: airplane && k > 0.5 ? '0 0 36px rgba(255,159,10,0.6)' : 'none' }}>
              <svg width={56} height={56} viewBox="0 0 48 48" fill="none" stroke={iconColor} strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round">{ICONS[tile.icon]}</svg>
            </div>
            <div style={{ position: 'absolute', left: 0, right: 0, top: 136, textAlign: 'center', fontFamily: SANS, fontWeight: 700, fontSize: 24, color: '#fff', whiteSpace: 'nowrap' }}>{tile.label}</div>
            <div style={{ position: 'absolute', left: 8, right: 8, top: 168, textAlign: 'center', fontFamily: SANS, fontWeight: 500, fontSize: 21, color: 'rgba(255,255,255,0.55)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{k > 0.5 ? tile.on : tile.off}</div>
          </div>
        );
      })}
      <div style={{ position: 'absolute', left: CC.pad, right: CC.pad, top: CC.pad + CC.tileH + 22, height: 118, borderRadius: 44, background: 'rgba(255,255,255,0.09)', border: '1px solid rgba(255,255,255,0.1)', overflow: 'hidden' }}>
        <div style={{ position: 'absolute', left: 26, top: 14, fontFamily: SANS, fontWeight: 700, fontSize: 24, color: '#fff' }}>Display</div>
        <div style={{ position: 'absolute', left: 26, right: 26, top: 62, height: 34, borderRadius: 17, background: 'rgba(255,255,255,0.18)', overflow: 'hidden' }}>
          <div style={{ width: '46%', height: '100%', background: '#FFFFFF', borderRadius: 17 }} />
        </div>
      </div>
    </div>
  );
};

type Props = { scenes: MotionScene[]; starts: number[]; current: number; accent: string; title: string };

export const CursorLayer: React.FC<Props> = ({ scenes, starts, current, accent, title }) => {
  const frame = useCurrentFrame();
  const scene = scenes[current];
  const action: CursorAction | undefined = scene?.type === 'flash' ? undefined : scene?.cursor;
  const [targets, setTargets] = useState<Targets | null>(null);
  const pending = useRef<number | null>(null); // the open delayRender handle, if any
  const handledFrame = useRef(-1); // the last frame whose targets were measured
  const needsTargets = !!action && action !== 'tab' && action !== 'idle' && action !== 'toggle';
  // the targets are measured from the live DOM once per frame; the frame waits (delayRender) until the measurement has been applied
  if (needsTargets && handledFrame.current !== frame && pending.current === null) pending.current = delayRender('cursor targets');
  useLayoutEffect(() => {
    if (needsTargets) {
      const m = measure(current);
      setTargets((prev) => (same(prev, m) ? prev : m));
    }
    handledFrame.current = frame;
    if (pending.current !== null) {
      continueRender(pending.current);
      pending.current = null;
    }
  }, [frame, current, needsTargets]);

  if (!scene || !action) return null;
  const side = cursorSides(scenes)[current];
  const rest = restFor(side);
  const start = starts[current];
  const f = frame - start;
  const dur = scene.durationInFrames;
  const bob = { x: Math.sin(frame / 14) * 6, y: Math.cos(frame / 11) * 7 };

  const arrive = Math.min(34, Math.round(dur * 0.34)); // frame at which the cursor reaches its target
  const leaveAt = Math.max(arrive + 14, dur - 22);
  const fadeIn = interpolate(f, [0, 8], [0, 1], clamp);
  const fadeOut = interpolate(f, [dur - 4, dur + 6], [1, 0], clamp);
  const opacity = Math.min(fadeIn, fadeOut);

  const pick = (kinds: (keyof Targets)[]): Box | null => {
    for (const k of kinds) {
      const b = targets?.[k]?.[0];
      if (b && b.w > 4) return b;
    }
    return null;
  };
  const centerShot = { x: WIDTH / 2, y: HEIGHT * 0.5 };

  let tip = { x: rest.x, y: rest.y }; // where the cursor tip is
  let press = 0;
  let ripple = -1;
  let focus: { box: Box; t: number; pulse: number } | null = null;
  let selection: Box | null = null;
  let ghost: { box: Box; label: string } | null = null;
  let busy = false;
  let tab: { t: number; open: number } | null = null;
  let panel: { t: number; clickAt: number; which: ToggleKey } | null = null;

  const travel = (to: { x: number; y: number }) => {
    const out = ease(f, 6, arrive);
    const back = ease(f, leaveAt, dur - 4);
    const p = { x: mix(mix(rest.x, to.x, out), rest.x, back), y: mix(mix(rest.y, to.y, out), rest.y, back) };
    // a slight arc, as a hand moves, instead of a straight line
    const arc = Math.sin(Math.PI * out) * 46 * (1 - back) + Math.sin(Math.PI * back) * 30;
    return { x: p.x + arc * (side > 0 ? -0.6 : 0.6), y: p.y - arc * 0.8 };
  };

  if (action === 'idle') {
    tip = { x: rest.x + bob.x, y: rest.y + bob.y };
  } else if (action === 'tab') {
    const g = tabGeometry();
    const over = travel({ x: g.plusX, y: g.plusY });
    tip = over;
    const clickAt = arrive + 4;
    const open = interpolate(f, [clickAt, clickAt + 12], [0, 1], { ...clamp, easing: EASE_OUT });
    const strip = interpolate(f, [2, 12], [0, 1], clamp) * interpolate(f, [dur - 14, dur - 2], [1, 0], clamp);
    tab = { t: strip, open };
    press = interpolate(f, [clickAt - 3, clickAt, clickAt + 6], [0, 1, 0], clamp);
    ripple = f >= clickAt ? (f - clickAt) / 22 : -1;
  } else if (action === 'toggle') {
    const which: ToggleKey = scene.toggle ?? 'airplane';
    const to = tileCenter(which);
    tip = travel({ x: to.x, y: to.y });
    const clickAt = arrive + 5;
    panel = { t: interpolate(f, [0, 14], [0, 1], { ...clamp, easing: EASE_OUT }) * interpolate(f, [dur - 12, dur - 2], [1, 0], clamp), clickAt, which };
    press = interpolate(f, [clickAt - 3, clickAt, clickAt + 7], [0, 1, 0], clamp);
    ripple = f >= clickAt ? (f - clickAt) / 24 : -1;
  } else if (action === 'select') {
    const box = pick(['text', 'number']);
    if (box) {
      const y = box.y + box.h * 0.5;
      const sel = ease(f, arrive, arrive + 24);
      if (f < arrive) {
        tip = travel({ x: box.x - 6, y });
      } else if (f < leaveAt) {
        tip = { x: box.x + box.w * sel, y: y + Math.sin(frame / 9) * 3 };
      } else {
        const back = ease(f, leaveAt, dur - 4);
        tip = { x: mix(box.x + box.w, rest.x, back), y: mix(y, rest.y, back) };
      }
      selection = { x: box.x - 6, y: box.y - 4, w: Math.max(0, (box.w + 12) * sel), h: box.h + 8 };
      press = f >= arrive && f < arrive + 26 ? 1 : 0;
    } else {
      tip = travel(centerShot);
    }
  } else if (action === 'drag') {
    const src = pick(['item', 'code', 'bar', 'text']);
    if (src) {
      const items = targets?.item ?? [];
      const step = items.length > 1 ? items[1].y - items[0].y : Math.min(90, src.h * 0.6 + 20);
      const grabPt = { x: src.x + Math.min(src.w * 0.3, 140), y: src.y + src.h * 0.5 };
      const dropPt = { x: grabPt.x + 40, y: grabPt.y + step * (items.length > 1 ? 1 : 0.8) };
      const grab = arrive + 6;
      const move = ease(f, grab, grab + 24);
      const toGrab = travel(grabPt);
      const base = f < grab ? toGrab : { x: mix(grabPt.x, dropPt.x, move), y: mix(grabPt.y, dropPt.y, move) };
      const back = ease(f, leaveAt, dur - 4);
      tip = f >= leaveAt ? { x: mix(dropPt.x, rest.x, back), y: mix(dropPt.y, rest.y, back) } : base;
      press = f >= grab && f < grab + 30 ? 1 : 0;
      if (f >= grab && f < leaveAt + 8) ghost = { box: { x: src.x + (tip.x - grabPt.x), y: src.y + (tip.y - grabPt.y), w: src.w, h: src.h }, label: '' };
      focus = f < grab ? { box: src, t: ease(f, arrive - 6, arrive), pulse: 0 } : null;
    } else {
      tip = travel(centerShot);
    }
  } else {
    // hover / click / busy: go to the key text (the accent, a number, or the headline)
    const box = pick(['accent', 'number', 'text', 'bar', 'code']);
    const aim = box ? { x: box.x + box.w * 0.66, y: box.y + box.h * 0.62 } : centerShot;
    tip = travel(aim);
    const settle = interpolate(f, [arrive, arrive + 8], [0, 1], clamp) * interpolate(f, [leaveAt - 6, leaveAt], [1, 0], clamp);
    if (action === 'busy') {
      busy = f >= arrive - 4 && f < leaveAt;
      if (box) focus = { box, t: settle * 0.7, pulse: 0 };
    } else if (action === 'hover') {
      if (box) focus = { box, t: settle, pulse: 0 };
    } else {
      const clickAt = arrive + 5;
      press = interpolate(f, [clickAt - 3, clickAt, clickAt + 7], [0, 1, 0], clamp);
      ripple = f >= clickAt ? (f - clickAt) / 24 : -1;
      const pulse = interpolate(f, [clickAt, clickAt + 5, clickAt + 16], [0, 1, 0], clamp);
      if (box) focus = { box, t: settle * 0.6 + pulse * 0.4, pulse };
    }
  }

  const moving = action !== 'idle' ? 1 : 0.8;
  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 20, pointerEvents: 'none' }}>
      {panel && <ControlCenter t={panel.t} f={f} clickAt={panel.clickAt} which={panel.which} />}
      {tab && <TabStrip t={tab.t} open={tab.open} title={title || 'silicon verdict'} accent={accent} />}
      <div style={{ position: 'absolute', inset: 0, opacity }}>
        {focus && <Focus box={focus.box} t={focus.t} accent={accent} pulse={focus.pulse} />}
        {selection && (
          <>
            <div style={{ position: 'absolute', left: selection.x, top: selection.y, width: selection.w, height: selection.h, background: `${accent}38`, borderRadius: 8, borderRight: `3px solid ${accent}` }} />
          </>
        )}
        {ghost && <div style={{ position: 'absolute', left: ghost.box.x - 10, top: ghost.box.y - 6, width: ghost.box.w + 20, height: ghost.box.h + 12, borderRadius: 18, border: `3px dashed ${accent}`, background: `${accent}18`, boxShadow: `0 18px 40px rgba(0,0,0,0.45), 0 0 26px ${accent}55`, transform: 'rotate(-1.2deg)' }} />}
        <Ripple x={tip.x} y={tip.y} t={ripple} accent={accent} />
        {busy ? <Spinner x={tip.x} y={tip.y} frame={frame} accent={accent} /> : <Arrow x={tip.x} y={tip.y} scale={moving} accent={accent} press={press} />}
      </div>
    </div>
  );
};
