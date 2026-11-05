/**
 * Minecraft video kit — choreography.
 * Turns a high-level plan ("walk to the chest, turn around, mine 6 blocks") into per-frame tracks with the rules that make
 * Minecraft animation look right on camera:
 *   - natural pace (default 4.1 blocks/s), one smooth speed profile over the whole path (soft start and stop)
 *   - paths go around every solid (hitbox-aware A*, see collision.ts) and are rounded at the corners
 *   - turns are eased over 16-40 frames, passing through the camera side when 180 degrees
 *   - before a walk the actor first turns towards where it goes; while walking the body follows the path heading (low-pass filtered)
 *   - actions (mine, attack, reach, wave, use) ease in and out and expose swing progress, hit and break frames for sounds and props
 * Two stages: `planTrack` produces raw positions (which collisions may still adjust), `finishTrack` derives everything the
 * animations need from the final positions (distance walked, speed, footsteps, swimming...). `buildTrack` does both.
 */
import { lerpAngle, pos01, ramp, shortestDelta, sstep } from './core';
import { Box, Vec2, planPath, segClear, uniqBoxes } from './collision';

export type { Box, Vec2 };
export type ActKind = 'mine' | 'attack' | 'reach' | 'wave' | 'use' | 'jump' | 'climb';

export type Step =
  | { t: 'wait'; frames: number }
  | { t: 'walk'; to: Vec2; via?: Vec2[]; speed?: number; swim?: boolean } // swim: crawl stroke at the water surface (default speed 1.9); PEAK speed in blocks per second (4.1 walk, 5.6 sprint); the soft start/stop makes the average ~20% lower
  | { t: 'face'; to: number | Vec2; frames?: number; dir?: 'shortest' | 'front' }
  | { t: 'act'; kind: ActKind; frames: number; cycle?: number; look?: Vec2; rise?: number }; // rise: blocks climbed (negative = down) for kind 'climb', ~2.3 blocks/s

export interface ActorPlan {
  start: Vec2;
  face: number | Vec2; // radians (0 = +z, PI/2 = +x) or a point to look at
  steps: Step[];
  obstacles?: Box[]; // solids the actor must walk around (the episode adds every prop/tree/hill automatically)
  water?: Box[]; // pond rectangles (x0, z0, x1, z1): the actor swims while inside them (filled in from world.ponds)
  avoidWater?: boolean; // walk around ponds (default: true for actors that never swim)
  stride?: number; // radians of limb phase per block walked (default from kinds.ts: no foot skating)
  radius?: number; // hitbox half width (default 0.3)
  stepEvery?: number; // a footstep sound every N foot landings
}

export interface Act {
  kind: ActKind;
  start: number;
  frames: number;
  cycle: number;
}

export interface RawTrack {
  frames: number;
  X: number[];
  Z: number[];
  Yb: number[]; // climbing height
  hop: number[]; // knockback hops
  F: number[];
  acts: Act[];
  marks: number[];
  warnings: string[];
  hurts: number[];
}

export interface Track {
  frames: number;
  x: number[];
  z: number[];
  y: number[]; // height above the ground (jumps, climbing, knockback hops)
  face: number[];
  dist: number[];
  speed: number[]; // blocks per second
  acts: Act[];
  stride: number;
  steps: number[]; // frames where a foot lands (with a footstep sound)
  hits: number[]; // frames where a tool hits (mine / attack)
  hurts: number[]; // frames where this actor is hurt (red flash, hurt sound)
  look: number[]; // extra head yaw (radians, three.js frame) towards someone nearby
  warnings: string[];
  marks: number[]; // frame where each plan step starts
  at: (f: number) => number;
  pos: (f: number) => Vec2;
  amt: (kind: ActKind, f: number) => number; // 0..1, eased
  prog: (kind: ActKind, f: number) => number; // swing progress 0..1 inside the current cycle
  swim: (f: number) => number; // 0..1: how much the actor is swimming (0 on land, 1 well inside the water, eased at the shore)
  lead: (f: number) => number; // how far the body will turn in the next ~9 frames (head leads the turn)
  hurt: (f: number) => number; // 0..1 red flash after being hit
  breaks: (act: Act) => number[]; // frame where each swing of a mining act completes (block k breaks)
}

const angleTo = (to: number | Vec2, from: Vec2) => (typeof to === 'number' ? to : Math.atan2(to[0] - from[0], to[1] - from[1]));
const DEFAULT_CYCLE: Record<ActKind, number> = { mine: 16, attack: 12, reach: 0, wave: 28, use: 0, jump: 0, climb: 0 };

/** Rounds the corners of a polyline with quadratic curves, shrinking a corner (down to sharp) if the curve would cut into a solid. */
const roundPath = (pts: Vec2[], r: number, boxes: Box[], rad: number): Vec2[] => {
  if (pts.length < 3) return pts;
  const out: Vec2[] = [pts[0]];
  for (let i = 1; i < pts.length - 1; i++) {
    const a = pts[i - 1], b = pts[i], c = pts[i + 1];
    const la = Math.hypot(b[0] - a[0], b[1] - a[1]), lc = Math.hypot(c[0] - b[0], c[1] - b[1]);
    let corner: Vec2[] = [b];
    for (const rr of [r, r / 2]) {
      const ra = Math.min(rr, la / 2), rc = Math.min(rr, lc / 2);
      const p0: Vec2 = [b[0] + ((a[0] - b[0]) / la) * ra, b[1] + ((a[1] - b[1]) / la) * ra];
      const p2: Vec2 = [b[0] + ((c[0] - b[0]) / lc) * rc, b[1] + ((c[1] - b[1]) / lc) * rc];
      const curve: Vec2[] = [];
      for (let k = 0; k <= 8; k++) {
        const t = k / 8;
        curve.push([(1 - t) * (1 - t) * p0[0] + 2 * (1 - t) * t * b[0] + t * t * p2[0], (1 - t) * (1 - t) * p0[1] + 2 * (1 - t) * t * b[1] + t * t * p2[1]]);
      }
      if (curve.every((q, k) => k === 0 || segClear(curve[k - 1], q, boxes, rad))) { corner = curve; break; }
    }
    out.push(...corner);
  }
  out.push(pts[pts.length - 1]);
  return out;
};

export const planTrack = (plan: ActorPlan, frames: number): RawTrack => {
  const X: number[] = [], Z: number[] = [], F: number[] = [], Yb: number[] = [];
  let yb = 0;
  const acts: Act[] = [];
  const marks: number[] = [];
  const warnings: string[] = [];
  let x = plan.start[0], z = plan.start[1], face = angleTo(plan.face, plan.start);
  const rad = plan.radius ?? 0.3;
  const swims = plan.steps.some((s) => s.t === 'walk' && s.swim);
  const obstacles = uniqBoxes([...(plan.obstacles ?? []), ...((plan.avoidWater ?? !swims) ? plan.water ?? [] : [])]);
  const obsKey = obstacles.map((b) => b.join(',')).join(';');
  const push = () => { X.push(x); Z.push(z); F.push(face); Yb.push(yb); };
  const hold = (n: number) => { for (let i = 0; i < n; i++) push(); };
  const turn = (target: number, n: number, dir: 'shortest' | 'front' = 'shortest') => {
    const start = face;
    const delta = dir === 'front' && Math.abs(Math.abs(shortestDelta(start, target)) - Math.PI) < 0.4 ? target - start : shortestDelta(start, target);
    if (Math.abs(delta) < 0.02) return;
    for (let k = 1; k <= n; k++) {
      face = start + delta * sstep(k / n);
      push();
    }
  };
  const autoTurnFrames = (delta: number) => Math.round(Math.min(40, Math.max(16, Math.abs(delta) * 11)));

  for (const s of plan.steps) {
    marks.push(X.length);
    if (s.t === 'wait') hold(s.frames);
    else if (s.t === 'face') {
      const target = angleTo(s.to, [x, z]);
      turn(target, s.frames ?? autoTurnFrames(shortestDelta(face, target)), s.dir);
    } else if (s.t === 'act') {
      if (s.look) {
        const target = angleTo(s.look, [x, z]);
        turn(target, autoTurnFrames(shortestDelta(face, target)));
      }
      const cycle = s.kind === 'jump' ? s.frames : s.cycle ?? DEFAULT_CYCLE[s.kind]; // a jump is one cycle: progress 0..1 over its frames
      acts.push({ kind: s.kind, start: X.length, frames: s.frames, cycle });
      if (s.kind === 'climb') {
        const rise = s.rise ?? 3;
        if ((Math.abs(rise) / s.frames) * 30 > 2.6) warnings.push(`climb speed ${((Math.abs(rise) / s.frames) * 30).toFixed(1)} blocks/s is too fast (vanilla ~2.3)`);
        const y0 = yb;
        for (let k = 1; k <= s.frames; k++) {
          yb = y0 + rise * pos01(k / s.frames);
          push();
        }
      } else hold(s.frames);
    } else {
      const speed = s.speed ?? (s.swim ? 1.9 : 4.1);
      if (s.swim && speed > 2.3) warnings.push(`swim speed ${speed} blocks/s is too fast (vanilla ~2)`);
      const raw: Vec2[] = [[x, z]];
      for (const q of [...(s.via ?? []), s.to]) {
        const leg = planPath(raw[raw.length - 1], q, obstacles, rad, obsKey);
        if (leg.warn) warnings.push(leg.warn);
        raw.push(...leg.path.slice(1));
      }
      const path = roundPath(raw, 0.9, obstacles, rad);
      const cum = [0];
      for (let i = 1; i < path.length; i++) cum.push(cum[i - 1] + Math.hypot(path[i][0] - path[i - 1][0], path[i][1] - path[i - 1][1]));
      const L = cum[cum.length - 1];
      if (L < 0.05) continue;
      const pointAt = (sLen: number): Vec2 => {
        const t = Math.min(L, Math.max(0, sLen));
        let i = 1;
        while (i < cum.length - 1 && cum[i] < t) i++;
        const u = (t - cum[i - 1]) / Math.max(1e-6, cum[i] - cum[i - 1]);
        return [path[i - 1][0] + (path[i][0] - path[i - 1][0]) * u, path[i - 1][1] + (path[i][1] - path[i - 1][1]) * u];
      };
      const headingAt = (sLen: number) => {
        const b = pointAt(sLen + 0.35), c = pointAt(sLen - 0.35);
        return Math.atan2(b[0] - c[0] + 1e-6, b[1] - c[1] + 1e-6);
      };
      const first = headingAt(0.1);
      const d0 = shortestDelta(face, first);
      if (Math.abs(d0) > 0.5) turn(first, autoTurnFrames(d0), 'front');
      const n = Math.max(2, Math.round((L / speed) * 30 * 1.25)); // the speed profile peaks at 1.25x its mean, so scale the duration to make `speed` the peak
      for (let k = 1; k <= n; k++) {
        const p = pointAt(pos01(k / n) * L);
        face = lerpAngle(face, headingAt(pos01(k / n) * L), 0.2);
        x = p[0]; z = p[1];
        push();
      }
    }
  }
  if (X.length < frames) hold(frames - X.length);
  X.length = Z.length = F.length = Yb.length = frames;
  return { frames, X, Z, Yb, F, hop: new Array(frames).fill(0), acts, marks, warnings, hurts: [] };
};

export const finishTrack = (raw: RawTrack, plan: ActorPlan): Track => {
  const { frames, X, Z, Yb, F, acts, marks, warnings, hurts, hop } = raw;
  const at = (f: number) => Math.max(0, Math.min(frames - 1, Math.round(f)));
  const D: number[] = [0];
  for (let f = 1; f < frames; f++) D.push(D[f - 1] + Math.hypot(X[f] - X[f - 1], Z[f] - Z[f - 1]));
  const speed = X.map((_, f) => Math.hypot(X[at(f + 1)] - X[at(f - 1)], Z[at(f + 1)] - Z[at(f - 1)]) * 15);
  // swimming follows the real position: depth inside the nearest pond (blocks), eased over 0.7 blocks so entering/leaving is gradual
  const SW = X.map((_, i) => (plan.water ?? []).reduce((m, [x0, z0, x1, z1]) => Math.max(m, sstep((Math.min(X[i] - x0, x1 - X[i], Z[i] - z0, z1 - Z[i]) + 0.1) / 0.7)), 0));
  const stride = plan.stride ?? 2.85;
  const every = Math.PI * (plan.stepEvery ?? 1);
  const steps: number[] = [];
  let last = Math.floor((D[0] * stride) / every);
  for (let f = 1; f < frames; f++) {
    const st = Math.floor((D[f] * stride) / every); // a foot lands each time the legs are spread
    if (st !== last) {
      if (speed[f] > 1.0) steps.push(f);
      last = st;
    }
  }
  const Y = Yb.map((v, f) => v + hop[f]);
  acts.filter((a) => a.kind === 'jump').forEach((a) => {
    for (let k = 0; k < a.frames && a.start + k < frames; k++) Y[a.start + k] += 4 * 1.1 * (k / a.frames) * (1 - k / a.frames); // ~1.1 block high parabola
    if (a.start + a.frames < frames) steps.push(a.start + a.frames); // landing
  });
  steps.sort((a, b) => a - b);
  const hits: number[] = [];
  acts.forEach((a) => {
    if (a.kind !== 'mine' && a.kind !== 'attack') return;
    for (let k = 0; k * a.cycle < a.frames; k++) hits.push(a.start + k * a.cycle + Math.round(a.cycle * 0.34));
  });
  const actsOf = (kind: ActKind) => acts.filter((a) => a.kind === kind);

  return {
    frames, x: X, z: Z, y: Y, face: F, dist: D, speed, acts, stride, steps, hits, hurts, warnings, marks, at,
    look: new Array(frames).fill(0),
    pos: (f) => [X[at(f)], Z[at(f)]],
    amt: (kind, f) => actsOf(kind).reduce((m, a) => Math.max(m, ramp(f, a.start - 4, a.start + 6, a.start + a.frames - 6, a.start + a.frames + 8)), 0),
    prog: (kind, f) => {
      const a = acts.find((q) => q.kind === kind && f >= q.start && f < q.start + q.frames + 1);
      if (!a || !a.cycle) return 0;
      return ((f - a.start) % a.cycle) / a.cycle;
    },
    swim: (f) => SW[at(f)],
    lead: (f) => Math.max(-0.7, Math.min(0.7, F[at(f + 9)] - F[at(f)])),
    hurt: (f) => hurts.reduce((m, h) => (f >= h && f < h + 15 ? Math.max(m, 1 - (f - h) / 15) : m), 0),
    breaks: (a) => Array.from({ length: Math.floor(a.frames / a.cycle) }, (_, k) => a.start + (k + 1) * a.cycle),
  };
};

/** Plan + finish for a single actor (no other actors to collide with). */
export const buildTrack = (plan: ActorPlan, frames: number): Track => finishTrack(planTrack(plan, frames), plan);
