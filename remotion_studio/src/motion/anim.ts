import type { MotionScene } from './types';

/**
 * The ARSENAL: how the text of a scene is revealed, how the camera moves and which big element is added to the picture. Each is picked per scene, deterministically from the
 * scene's own words, never the same as the previous scenes, so a video never repeats itself and the same script always renders the same video.
 */
export type Reveal = 'pop' | 'slam' | 'type' | 'draw' | 'scramble' | 'mask' | 'drop' | 'wave' | 'blur' | 'slice' | 'rise' | 'focus' | 'flip';
/** The reveals picked by default are the calm ones; scramble, drop and slice are implemented (reveal.tsx) but kept out of the pool because they read as too intense. */
export const REVEALS: Reveal[] = ['pop', 'type', 'draw', 'mask', 'wave', 'blur', 'rise', 'focus', 'flip'];

export type CameraMove = 'pushIn' | 'pullOut' | 'panLeft' | 'panRight' | 'tiltUp' | 'tiltDown' | 'dolly' | 'orbit' | 'crane' | 'punch' | 'rollIn' | 'slideDiag' | 'breathe';
export const CAMERA_MOVES: CameraMove[] = ['pushIn', 'pullOut', 'panLeft', 'panRight', 'tiltUp', 'tiltDown', 'dolly', 'orbit', 'crane', 'punch', 'rollIn', 'slideDiag', 'breathe'];

export type BigFxName = 'rings' | 'rays' | 'scribble' | 'arrow' | 'giantIcon' | 'brackets' | 'laser' | 'speed' | 'stars' | 'diamonds' | 'pie' | 'crosshair' | 'dotwave' | 'frameDraw' | 'hexes' | 'orbitDots' | 'equalizer' | 'radar' | 'comets' | 'ripples';
export const BIG_FX: BigFxName[] = ['rings', 'rays', 'scribble', 'arrow', 'giantIcon', 'brackets', 'laser', 'speed', 'stars', 'diamonds', 'pie', 'crosshair', 'dotwave', 'frameDraw', 'hexes', 'orbitDots', 'equalizer', 'radar', 'comets', 'ripples'];
/** The ones that are quiet enough to sit next to a stage visual. */
export const BIG_FX_LIGHT: BigFxName[] = ['rays', 'speed', 'stars', 'frameDraw', 'dotwave', 'comets', 'ripples'];

export const hash = (s: string): number => {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return (h >>> 0) / 4294967296;
};

/** Picks one item per scene from `pool`, never one of the last `memory` picks; `eligible(i)` can veto a scene (null result). */
export function pickSeries<T>(scenes: MotionScene[], pool: T[], salt: string, memory = 3, eligible: (i: number) => T[] | null = () => pool): (T | null)[] {
  const out: (T | null)[] = [];
  const recent: T[] = [];
  scenes.forEach((sc, i) => {
    const allowed = eligible(i);
    if (!allowed) {
      out.push(null);
      return;
    }
    const fresh = allowed.filter((x) => !recent.includes(x));
    const from = fresh.length ? fresh : allowed;
    const pick = from[Math.floor(hash(`${salt}|${i}|${sc.text}|${sc.type}`) * from.length)];
    recent.push(pick);
    if (recent.length > memory) recent.shift();
    out.push(pick);
  });
  return out;
}
