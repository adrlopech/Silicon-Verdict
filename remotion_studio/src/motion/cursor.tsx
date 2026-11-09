import React, { useLayoutEffect, useRef, useState } from 'react';
import { delayRender, continueRender, interpolate, useCurrentFrame } from 'remotion';
import { EASE_IO, EASE_OUT, clamp } from './primitives';
import { ICONS } from './props';
import { SANS } from './fonts';
import { CursorAction, FPS, HEIGHT, MotionScene, SAFE_BOTTOM, TIER_DROP, TIER_GRAB, ToggleKey, WIDTH, uiAct } from './types';

/**
 * The channel's character is a mouse pointer. It only appears when it DOES something that means something, never as decoration and never to introduce the topic:
 *   select - drags across the key phrase like selecting text, arriving when the narrator says it (scene.cursorCue)
 *   drag   - progress bar: grabs the knob at the end of the bar and pulls it to its value; tier list: carries the new chip into its row
 *   click  - presses the setting or the step: the code panel of a fix, the first step of a list (ripple + a pulse on what it pressed)
 *   toggle - a macOS-style Control Center panel opens and the pointer flips a switch (Airplane Mode turns Wi-Fi and Bluetooth off)
 * Targets are measured from the DOM (elements tagged data-cursor), every frame, so the pointer always lands on what is really on screen.
 */
const KNOWN: CursorAction[] = ['click', 'select', 'drag', 'toggle'];

type Box = { x: number; y: number; w: number; h: number };
type Targets = Partial<Record<'text' | 'accent' | 'item' | 'number' | 'code' | 'bar' | 'fill' | 'newitem' | 'target', Box[]>>;
const KINDS = ['text', 'accent', 'item', 'number', 'code', 'bar', 'fill', 'newitem', 'target'] as const;

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
const ARROW_SIZE = 0.5; // overall size of the pointer (1 = the size of the banner drawing at 2.5 px per unit); the tip stays put when it shrinks

const Arrow: React.FC<{ x: number; y: number; scale: number; accent: string; press: number }> = ({ x, y, scale, accent, press }) => (
  <svg width={120} height={150} viewBox="-6 -6 48 60" style={{ position: 'absolute', left: x - 6 * 2.5, top: y - 6 * 2.5, overflow: 'visible', transform: `scale(${scale * ARROW_SIZE * (1 - 0.14 * press)})`, transformOrigin: '6px 6px', filter: `drop-shadow(0 0 10px ${accent}AA) drop-shadow(0 4px 7px rgba(0,0,0,0.55))` }}>
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
        const r = 12 + p * 72;
        return <div key={i} style={{ position: 'absolute', left: x - r, top: y - r, width: r * 2, height: r * 2, borderRadius: r, border: `${4 - p * 2.4}px solid ${accent}`, opacity: (1 - p) * 0.9, boxShadow: `0 0 24px ${accent}88` }} />;
      })}
    </>
  );
};

const Focus: React.FC<{ box: Box; t: number; accent: string; pulse?: number }> = ({ box, t, accent, pulse = 0 }) => {
  const pad = 22;
  return (
    <div style={{ position: 'absolute', left: box.x - pad, top: box.y - pad * 0.6, width: box.w + pad * 2, height: box.h + pad * 1.2, borderRadius: 22, border: `3px solid ${accent}`, background: `${accent}${pulse > 0 ? '22' : '12'}`, opacity: t, boxShadow: `0 0 ${30 + pulse * 40}px ${accent}66`, transform: `scale(${1 + pulse * 0.02})` }} />
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

type Props = { scenes: MotionScene[]; starts: number[]; current: number; accent: string };

export const CursorLayer: React.FC<Props> = ({ scenes, starts, current, accent }) => {
  const frame = useCurrentFrame();
  const scene = scenes[current];
  const raw = scene?.type === 'flash' ? undefined : scene?.cursor;
  const action: CursorAction | undefined = raw && KNOWN.includes(raw) ? raw : undefined; // an action from an older script (tab, hover, busy, idle) is simply not shown
  const [targets, setTargets] = useState<Targets | null>(null);
  const pending = useRef<number | null>(null); // the open delayRender handle, if any
  const handledFrame = useRef(-1); // the last frame whose targets were measured
  const needsTargets = !!action && action !== 'toggle';
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

  // the pointer reaches its target when the narrator says the phrase it acts on (cursorCue); without voice timing it arrives about a third into the scene
  const cueF = scene.cursorCue != null ? Math.round(scene.cursorCue * FPS) : null;
  const arrive = cueF != null && (action === 'select' || action === 'click') ? Math.max(16, Math.min(dur - 44, cueF - 2)) : Math.min(34, Math.round(dur * 0.34));
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

  let tip = { x: rest.x, y: rest.y }; // where the pointer tip is
  let press = 0;
  let ripple = -1;
  let focus: { box: Box; t: number; pulse: number } | null = null;
  let selection: Box | null = null;
  let panel: { t: number; clickAt: number; which: ToggleKey } | null = null;
  let shown = true; // false when the scene has nothing the action could mean (the pointer stays away)

  const travel = (to: { x: number; y: number }) => {
    const out = ease(f, 6, arrive);
    const back = ease(f, leaveAt, dur - 4);
    const p = { x: mix(mix(rest.x, to.x, out), rest.x, back), y: mix(mix(rest.y, to.y, out), rest.y, back) };
    // a slight arc, as a hand moves, instead of a straight line
    const arc = Math.sin(Math.PI * out) * 46 * (1 - back) + Math.sin(Math.PI * back) * 30;
    return { x: p.x + arc * (side > 0 ? -0.6 : 0.6), y: p.y - arc * 0.8 };
  };
  /** Glide from the resting corner to a point that may itself be moving (a knob, a chip), arriving at frame `at`. */
  const reach = (to: { x: number; y: number }, at: number) => {
    const out = ease(f, 2, at);
    const arc = Math.sin(Math.PI * out) * 40;
    return { x: mix(rest.x, to.x, out) + arc * (side > 0 ? -0.6 : 0.6), y: mix(rest.y, to.y, out) - arc * 0.8 };
  };
  const leave = (from: { x: number; y: number }, at: number) => {
    const back = ease(f, at, dur - 4);
    return { x: mix(from.x, rest.x, back), y: mix(from.y, rest.y, back) };
  };

  if (scene.type === 'ui') {
    // a drawn interface (preset): the element the pointer acts on is tagged data-cursor="target" and measured live; the preset animates the change between grab and done
    const { grab, done } = uiAct(scene);
    const box = pick(['target']);
    if (box) {
      const mid = { x: box.x + box.w * 0.5, y: box.y + box.h * 0.5 };
      if (action === 'select') {
        const sel = ease(f, grab, grab + 24);
        const edge = { x: box.x + box.w, y: mid.y };
        tip = f < grab ? reach({ x: box.x - 6, y: mid.y }, grab) : f < done + 14 ? { x: box.x + box.w * sel, y: mid.y } : leave(edge, done + 14);
        selection = { x: box.x - 6, y: box.y - 4, w: Math.max(0, (box.w + 12) * sel), h: box.h + 8 };
        press = f >= grab && f < grab + 26 ? 1 : 0;
      } else if (action === 'drag') {
        if (f < grab) tip = reach(mid, grab);
        else if (f < done + 4) {
          tip = mid;
          press = 1;
        } else tip = leave(mid, done + 10);
      } else {
        tip = f < grab ? reach(mid, grab) : f < done + 10 ? mid : leave(mid, done + 10);
        press = interpolate(f, [grab - 3, grab, grab + 7], [0, 1, 0], clamp);
        ripple = f >= grab ? (f - grab) / 24 : -1;
      }
    } else shown = false;
  } else if (action === 'toggle') {
    const which: ToggleKey = scene.toggle ?? 'airplane';
    const to = tileCenter(which);
    tip = travel({ x: to.x, y: to.y });
    const clickAt = arrive + 5;
    panel = { t: interpolate(f, [0, 14], [0, 1], { ...clamp, easing: EASE_OUT }) * interpolate(f, [dur - 12, dur - 2], [1, 0], clamp), clickAt, which };
    press = interpolate(f, [clickAt - 3, clickAt, clickAt + 7], [0, 1, 0], clamp);
    ripple = f >= clickAt ? (f - clickAt) / 24 : -1;
  } else if (action === 'select') {
    // the key phrase: the accent of a headline pair, the label itself when the scene is one big word
    const box = scene.type === 'bigText' ? pick(['text']) : pick(['accent', 'text']);
    if (box) {
      const y = box.y + box.h * 0.5;
      const sel = ease(f, arrive, arrive + 24);
      if (f < arrive) {
        tip = travel({ x: box.x - 6, y });
      } else if (f < leaveAt) {
        tip = { x: box.x + box.w * sel, y: y + Math.sin(frame / 9) * 3 };
      } else {
        tip = leave({ x: box.x + box.w, y }, leaveAt);
      }
      selection = { x: box.x - 6, y: box.y - 4, w: Math.max(0, (box.w + 12) * sel), h: box.h + 8 };
      press = f >= arrive && f < arrive + 26 ? 1 : 0;
    } else shown = false;
  } else if (action === 'drag' && scene.type === 'progressBar') {
    // grabs the knob at the end of the bar and pulls it: the fill grows as the pointer moves
    const fill = pick(['fill']);
    if (fill) {
      const knob = { x: fill.x + fill.w, y: fill.y + fill.h * 0.5 };
      const grab = 14;
      const release = Math.max(grab + 24, dur - 26);
      if (f < grab) tip = reach(knob, grab);
      else if (f < release) {
        tip = knob;
        press = 1;
      } else tip = leave(knob, release);
    } else shown = false;
  } else if (action === 'drag' && scene.type === 'tier') {
    // carries the newest chip from the tray into its row (the scene moves the chip; the pointer holds it)
    const chip = pick(['newitem']);
    if (chip) {
      const hold = { x: chip.x + Math.min(24, chip.w * 0.15), y: chip.y + chip.h * 0.62 };
      if (f < TIER_GRAB) tip = reach(hold, TIER_GRAB);
      else if (f < TIER_DROP + 4) {
        tip = hold;
        press = 1;
      } else tip = leave(hold, Math.max(TIER_DROP + 12, dur - 40));
    } else shown = false;
  } else if (action === 'click') {
    // presses the setting or the step: the code panel of a fix, the first step of a list
    const box = scene.type === 'codeBlock' ? pick(['code']) : scene.type === 'list' ? pick(['item']) : null;
    if (box) {
      tip = travel({ x: box.x + Math.min(box.w * 0.35, 260), y: box.y + box.h * 0.5 });
      const settle = interpolate(f, [arrive, arrive + 8], [0, 1], clamp) * interpolate(f, [leaveAt - 6, leaveAt], [1, 0], clamp);
      const clickAt = arrive + 5;
      press = interpolate(f, [clickAt - 3, clickAt, clickAt + 7], [0, 1, 0], clamp);
      ripple = f >= clickAt ? (f - clickAt) / 24 : -1;
      const pulse = interpolate(f, [clickAt, clickAt + 5, clickAt + 16], [0, 1, 0], clamp);
      focus = { box, t: settle * 0.6 + pulse * 0.4, pulse };
    } else shown = false;
  } else shown = false;

  if (!shown && !panel) return null;
  return (
    <div style={{ position: 'absolute', inset: 0, zIndex: 20, pointerEvents: 'none' }}>
      {panel && <ControlCenter t={panel.t} f={f} clickAt={panel.clickAt} which={panel.which} />}
      <div style={{ position: 'absolute', inset: 0, opacity }}>
        {focus && <Focus box={focus.box} t={focus.t} accent={accent} pulse={focus.pulse} />}
        {selection && <div style={{ position: 'absolute', left: selection.x, top: selection.y, width: selection.w, height: selection.h, background: `${accent}38`, borderRadius: 8, borderRight: `3px solid ${accent}` }} />}
        <Ripple x={tip.x} y={tip.y} t={ripple} accent={accent} />
        {shown && <Arrow x={tip.x} y={tip.y} scale={1} accent={accent} press={press} />}
      </div>
    </div>
  );
};
