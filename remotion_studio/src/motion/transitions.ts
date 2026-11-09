import { CSSProperties } from 'react';
import { Easing, random } from 'remotion';

/** Scene-to-scene transitions. `enter(p)` styles the incoming scene (p 0 -> 1), `exit(p)` the outgoing one (p 0 -> 1) while both overlap. */
export type TransitionName =
  | 'fade' | 'pushLeft' | 'pushUp' | 'zoomThrough' | 'zoomOut' | 'wipe' | 'iris' | 'blinds' | 'flip' | 'whip' | 'glitch' | 'spin' | 'diagonal';

export const TRANSITIONS: TransitionName[] = ['pushLeft', 'zoomThrough', 'iris', 'glitch', 'pushUp', 'blinds', 'whip', 'flip', 'wipe', 'zoomOut', 'diagonal', 'spin', 'fade'];

const W = 1080;
const H = 1920;
const out = Easing.bezier(0.16, 1, 0.3, 1);
const io = Easing.bezier(0.65, 0, 0.35, 1);
const mask = (v: string): CSSProperties => ({ clipPath: v });

type Styler = (p: number, seed: number) => CSSProperties;

const jitter = (seed: number, p: number) => (random(`g${seed}-${Math.floor(p * 12)}`) - 0.5);

export const ENTER: Record<TransitionName, Styler> = {
  fade: (p) => ({ opacity: out(p), filter: `blur(${(1 - out(p)) * 10}px)` }),
  pushLeft: (p) => ({ transform: `translateX(${(1 - io(p)) * W}px)` }),
  pushUp: (p) => ({ transform: `translateY(${(1 - io(p)) * H}px)` }),
  zoomThrough: (p) => ({ opacity: out(p), transform: `scale(${0.55 + 0.45 * out(p)})`, filter: `blur(${(1 - out(p)) * 14}px)` }),
  zoomOut: (p) => ({ opacity: out(p), transform: `scale(${1.7 - 0.7 * out(p)})`, filter: `blur(${(1 - out(p)) * 16}px)` }),
  wipe: (p) => mask(`inset(0 ${(1 - io(p)) * 100}% 0 0)`),
  iris: (p) => mask(`circle(${io(p) * 1250}px at 50% 52%)`),
  blinds: (p) => ({ WebkitMaskImage: `linear-gradient(90deg, #000 ${io(p) * 100}%, transparent ${io(p) * 100}%)`, WebkitMaskSize: '135px 100%', WebkitMaskRepeat: 'repeat' }),
  flip: (p) => ({ opacity: p >= 0.5 ? 1 : 0, transform: `perspective(1400px) rotateY(${(1 - io(p)) * -90}deg)`, transformOrigin: '100% 50%' }),
  whip: (p) => ({ transform: `translateX(${(1 - out(p)) * 1400}px) skewX(${(1 - out(p)) * -18}deg)`, filter: `blur(${(1 - out(p)) * 26}px)` }),
  glitch: (p, s) => ({ opacity: p < 0.15 ? 0 : 1, transform: `translate(${jitter(s, p) * 90 * (1 - p)}px, ${jitter(s + 9, p) * 24 * (1 - p)}px) skewX(${jitter(s + 3, p) * 14 * (1 - p)}deg)`, filter: `hue-rotate(${(1 - p) * 160 * jitter(s, p)}deg) saturate(${1 + (1 - p) * 2}) contrast(${1 + (1 - p) * 0.6})` }),
  spin: (p) => ({ opacity: out(p), transform: `rotate(${(1 - out(p)) * -14}deg) scale(${0.6 + 0.4 * out(p)})` }),
  diagonal: (p) => mask(`polygon(0 0, ${io(p) * 230 - 30}% 0, ${io(p) * 230 - 130}% 100%, 0 100%)`),
};

export const EXIT: Record<TransitionName, Styler> = {
  fade: (p) => ({ opacity: 1 - out(p), filter: `blur(${out(p) * 10}px)` }),
  pushLeft: (p) => ({ transform: `translateX(${-io(p) * W * 0.6}px)`, opacity: 1 - io(p) * 0.6 }),
  pushUp: (p) => ({ transform: `translateY(${-io(p) * H * 0.5}px)`, opacity: 1 - io(p) * 0.6 }),
  zoomThrough: (p) => ({ opacity: 1 - out(p), transform: `scale(${1 + 0.9 * out(p)})`, filter: `blur(${out(p) * 18}px)` }),
  zoomOut: (p) => ({ opacity: 1 - out(p), transform: `scale(${1 - 0.4 * out(p)})`, filter: `blur(${out(p) * 12}px)` }),
  wipe: (p) => ({ opacity: 1 - io(p) * 0.5 }),
  iris: (p) => ({ opacity: 1 - io(p) * 0.4, transform: `scale(${1 - io(p) * 0.08})` }),
  blinds: (p) => ({ opacity: 1 - io(p) * 0.5 }),
  flip: (p) => ({ opacity: p < 0.5 ? 1 : 0, transform: `perspective(1400px) rotateY(${io(p) * 90}deg)`, transformOrigin: '0% 50%' }),
  whip: (p) => ({ transform: `translateX(${-out(p) * 1400}px) skewX(${out(p) * 18}deg)`, filter: `blur(${out(p) * 26}px)` }),
  glitch: (p, s) => ({ opacity: p > 0.85 ? 0 : 1, transform: `translate(${jitter(s + 5, p) * 110 * p}px, ${jitter(s + 7, p) * 30 * p}px) skewX(${jitter(s + 1, p) * 18 * p}deg)`, filter: `hue-rotate(${p * 200 * jitter(s + 2, p)}deg) saturate(${1 + p * 2.4})` }),
  spin: (p) => ({ opacity: 1 - out(p), transform: `rotate(${out(p) * 12}deg) scale(${1 + 0.3 * out(p)})` }),
  diagonal: (p) => ({ opacity: 1 - io(p) * 0.4 }),
};

/** Deterministic pick that never repeats the previous transition and cycles through the whole set. */
export const pickTransition = (index: number, explicit?: string, pool: TransitionName[] = TRANSITIONS): TransitionName => {
  if (explicit && (explicit as TransitionName) in ENTER) return explicit as TransitionName;
  const base = Math.floor(random(`tr${index}`) * pool.length);
  return pool[(base + index * 5) % pool.length]; // the look decides which transitions it uses
};
