/**
 * Minecraft video kit — hitboxes and collisions.
 *   - solids: every block-like thing in an episode (terrain hills, tree trunks, chest, signs, ladder column, door frame, ore veins,
 *     the closed door leaf) as axis-aligned boxes on the ground plane, with a height range and an optional time range
 *   - planPath: grid A* around the solids inflated by the actor's hitbox radius, string-pulled to a few straight legs (cached)
 *   - applyHits: knockback, hurt time and hop for whoever is hit by an attack (vanilla: 10 ticks of invulnerability)
 *   - separate: actors never overlap; the lower-priority one gives way smoothly (vanilla entity pushing), and pushed actors are kept
 *     out of the solids
 * Coordinates: x/z in blocks, y up. Boxes are [x0, z0, x1, z1].
 */
export type Vec2 = [number, number];
export type Box = [number, number, number, number];
export interface Solid { box: Box; y0: number; y1: number; from?: number; to?: number; what: string }

/* ------------------------------ geometry ------------------------------ */
const EPS = 1e-6;
export const inBox = (x: number, z: number, b: Box, r = 0) => x > b[0] - r && x < b[2] + r && z > b[1] - r && z < b[3] + r;

/** Does the segment p→q pass through the box inflated by r? (slab test, touching the border does not count) */
export const segHitsBox = (p: Vec2, q: Vec2, b: Box, r = 0) => {
  const x0 = b[0] - r, z0 = b[1] - r, x1 = b[2] + r, z1 = b[3] + r;
  let t0 = 0, t1 = 1;
  const dx = q[0] - p[0], dz = q[1] - p[1];
  for (const [d, s, lo, hi] of [[dx, p[0], x0, x1], [dz, p[1], z0, z1]] as const) {
    if (Math.abs(d) < EPS) {
      if (s <= lo + EPS || s >= hi - EPS) return false;
    } else {
      let a = (lo - s) / d, c = (hi - s) / d;
      if (a > c) [a, c] = [c, a];
      t0 = Math.max(t0, a);
      t1 = Math.min(t1, c);
      if (t1 - t0 <= EPS) return false;
    }
  }
  return true;
};
export const segClear = (p: Vec2, q: Vec2, boxes: Box[], r: number) => !boxes.some((b) => segHitsBox(p, q, b, r));

/** Smallest move that takes a body of radius r at (x, z) out of the box (null when it does not touch it). */
export const pushOut = (x: number, z: number, r: number, b: Box): Vec2 | null => {
  if (!inBox(x, z, b, r)) return null;
  const opts: [number, Vec2][] = [
    [x - (b[0] - r), [b[0] - r - x, 0]],
    [b[2] + r - x, [b[2] + r - x, 0]],
    [z - (b[1] - r), [0, b[1] - r - z]],
    [b[3] + r - z, [0, b[3] + r - z]],
  ];
  return opts.sort((a, c) => a[0] - c[0])[0][1];
};

/** Axis-aligned bounds of a rectangle (half sizes hx, hz, centred at local ox, oz) rotated by rotY (three.js) around (cx, cz). */
export const rotBox = (cx: number, cz: number, hx: number, hz: number, rotY = 0, ox = 0, oz = 0): Box => {
  const c = Math.cos(rotY), s = Math.sin(rotY);
  const wx = cx + ox * c + oz * s, wz = cz - ox * s + oz * c;
  const ex = Math.abs(hx * c) + Math.abs(hz * s), ez = Math.abs(hx * s) + Math.abs(hz * c);
  return [wx - ex, wz - ez, wx + ex, wz + ez];
};

/** Merge identical boxes (episode solids are often added twice: by the author and automatically). */
export const uniqBoxes = (boxes: Box[]): Box[] => {
  const seen = new Set<string>();
  return boxes.filter((b) => {
    const k = b.map((v) => v.toFixed(3)).join(',');
    if (seen.has(k)) return false;
    seen.add(k);
    return true;
  });
};

/* ------------------------------ path planning ------------------------------ */
const CELL = 0.25;
const pathCache = new Map<string, { path: Vec2[]; warn?: string }>();

class Heap {
  private a: [number, number][] = [];
  get size() { return this.a.length; }
  push(v: number, k: number) {
    const a = this.a;
    a.push([k, v]);
    let i = a.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;
      if (a[p][0] <= a[i][0]) break;
      [a[p], a[i]] = [a[i], a[p]];
      i = p;
    }
  }
  pop(): number {
    const a = this.a;
    const top = a[0];
    const last = a.pop()!;
    if (a.length) {
      a[0] = last;
      let i = 0;
      for (;;) {
        const l = 2 * i + 1, r = l + 1;
        let m = i;
        if (l < a.length && a[l][0] < a[m][0]) m = l;
        if (r < a.length && a[r][0] < a[m][0]) m = r;
        if (m === i) break;
        [a[m], a[i]] = [a[i], a[m]];
        i = m;
      }
    }
    return top[1];
  }
}

const astar = (p: Vec2, q: Vec2, boxes: Box[], r: number): { path: Vec2[]; warn?: string } => {
  const pad = r + 0.06;
  const xs = [p[0], q[0]], zs = [p[1], q[1]];
  const snap = (v: number) => Math.floor(v / CELL) * CELL; // grid aligned to multiples of CELL: results do not depend on p and q
  const x0 = snap(Math.min(...xs) - 8), x1 = Math.max(...xs) + 8, z0 = snap(Math.min(...zs) - 8), z1 = Math.max(...zs) + 8;
  const W = Math.ceil((x1 - x0) / CELL), H = Math.ceil((z1 - z0) / CELL);
  const near = boxes.filter((b) => b[2] + pad > x0 && b[0] - pad < x1 && b[3] + pad > z0 && b[1] - pad < z1);
  const blocked = new Uint8Array(W * H);
  near.forEach((b) => {
    const i0 = Math.max(0, Math.floor((b[0] - pad - x0) / CELL)), i1 = Math.min(W - 1, Math.ceil((b[2] + pad - x0) / CELL));
    const j0 = Math.max(0, Math.floor((b[1] - pad - z0) / CELL)), j1 = Math.min(H - 1, Math.ceil((b[3] + pad - z0) / CELL));
    for (let j = j0; j <= j1; j++)
      for (let i = i0; i <= i1; i++) if (inBox(x0 + (i + 0.5) * CELL, z0 + (j + 0.5) * CELL, b, pad)) blocked[j * W + i] = 1;
  });
  const cellOf = (v: Vec2) => Math.min(H - 1, Math.max(0, Math.floor((v[1] - z0) / CELL))) * W + Math.min(W - 1, Math.max(0, Math.floor((v[0] - x0) / CELL)));
  const centre = (c: number): Vec2 => [x0 + ((c % W) + 0.5) * CELL, z0 + (Math.floor(c / W) + 0.5) * CELL];
  const nearestFree = (c: number) => {
    if (!blocked[c]) return c;
    const seen = new Uint8Array(W * H);
    const qu = [c];
    seen[c] = 1;
    for (let k = 0; k < qu.length; k++) {
      const u = qu[k];
      if (!blocked[u]) return u;
      const ux = u % W, uz = Math.floor(u / W);
      for (const [dx, dz] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
        const vx = ux + dx, vz = uz + dz;
        if (vx < 0 || vz < 0 || vx >= W || vz >= H) continue;
        const v = vz * W + vx;
        if (!seen[v]) { seen[v] = 1; qu.push(v); }
      }
    }
    return c;
  };
  let warn: string | undefined;
  const sRaw = cellOf(p), gRaw = cellOf(q);
  const s = nearestFree(sRaw), g = nearestFree(gRaw);
  const goal: Vec2 = g === gRaw ? q : centre(g);
  if (g !== gRaw) warn = `walk target (${q[0].toFixed(1)}, ${q[1].toFixed(1)}) is inside a hitbox; moved to (${goal[0].toFixed(1)}, ${goal[1].toFixed(1)})`;

  const gScore = new Float32Array(W * H).fill(Infinity);
  const from = new Int32Array(W * H).fill(-1);
  const closed = new Uint8Array(W * H);
  const gx = g % W, gz = Math.floor(g / W);
  const hEst = (c: number) => {
    const dx = Math.abs((c % W) - gx), dz = Math.abs(Math.floor(c / W) - gz);
    return Math.max(dx, dz) + 0.4142 * Math.min(dx, dz);
  };
  const open = new Heap();
  gScore[s] = 0;
  open.push(s, hEst(s));
  let found = false;
  while (open.size) {
    const u = open.pop();
    if (closed[u]) continue;
    if (u === g) { found = true; break; }
    closed[u] = 1;
    const ux = u % W, uz = Math.floor(u / W);
    for (let dz = -1; dz <= 1; dz++)
      for (let dx = -1; dx <= 1; dx++) {
        if (!dx && !dz) continue;
        const vx = ux + dx, vz = uz + dz;
        if (vx < 0 || vz < 0 || vx >= W || vz >= H) continue;
        const v = vz * W + vx;
        if (blocked[v] || closed[v]) continue;
        if (dx && dz && (blocked[uz * W + vx] || blocked[vz * W + ux])) continue; // no corner cutting
        const ng = gScore[u] + (dx && dz ? 1.4142 : 1);
        if (ng < gScore[v]) {
          gScore[v] = ng;
          from[v] = u;
          open.push(v, ng + hEst(v));
        }
      }
  }
  if (!found) return { path: [p, q], warn: `no free path from (${p[0].toFixed(1)}, ${p[1].toFixed(1)}) to (${q[0].toFixed(1)}, ${q[1].toFixed(1)})` };
  const cells: Vec2[] = [];
  for (let c = g; c !== -1; c = from[c]) cells.push(centre(c));
  cells.reverse();
  const pts: Vec2[] = [p, ...cells.slice(1, -1), goal];
  // string pulling: keep only the corners needed to stay clear of the solids
  const out: Vec2[] = [p];
  let i = 0;
  while (i < pts.length - 1) {
    let j = pts.length - 1;
    while (j > i + 1 && !segClear(pts[i], pts[j], near, r + 0.03)) j--;
    out.push(pts[j]);
    i = j;
  }
  return { path: out, warn };
};

/** Polyline from p to q (both included) that keeps a body of radius r clear of the boxes. Straight when nothing is in the way. */
export const planPath = (p: Vec2, q: Vec2, boxes: Box[], r: number, key?: string): { path: Vec2[]; warn?: string } => {
  if (segClear(p, q, boxes, r + 0.03)) return { path: [p, q] };
  const k = `${p[0].toFixed(3)},${p[1].toFixed(3)}>${q[0].toFixed(3)},${q[1].toFixed(3)}@${r}|${key ?? boxes.map((b) => b.join(',')).join(';')}`;
  let hit = pathCache.get(k);
  if (!hit) {
    hit = astar(p, q, boxes, r);
    if (pathCache.size > 4000) pathCache.clear();
    pathCache.set(k, hit);
  }
  return hit;
};

/* ------------------------------ bodies: knockback and separation ------------------------------ */
export interface Body {
  id: string;
  kind: string;
  r: number;
  h: number;
  priority: number;
  X: number[];
  Z: number[];
  Y: number[]; // feet height
  F: number[]; // facing
  hop: number[]; // extra height from knockback hops
  hurts: number[]; // frames where it gets hurt
  attacks: { start: number; frames: number; cycle: number }[];
  avoid: Box[]; // static solids this body has to stay out of when pushed
}

const HURT_FRAMES = 15; // vanilla: 10 ticks of red flash / invulnerability

/** Attacks land on the nearest actor in front within reach: red flash, knockback (0.45 blocks, eased) and a small hop. */
export const applyHits = (bodies: Body[], frames: number) => {
  bodies.forEach((a) =>
    a.attacks.forEach((act) => {
      for (let k = 0; k * act.cycle < act.frames; k++) {
        const f = act.start + k * act.cycle + Math.round(act.cycle * 0.34);
        if (f >= frames) break;
        let best: Body | null = null, bd = 9;
        for (const b of bodies) {
          if (b === a) continue;
          const dx = b.X[f] - a.X[f], dz = b.Z[f] - a.Z[f];
          const d = Math.hypot(dx, dz);
          let da = Math.atan2(dx, dz) - a.F[f];
          da = Math.atan2(Math.sin(da), Math.cos(da));
          if (d < 3 + b.r && Math.abs(da) < 1.1 && d < bd) { best = b; bd = d; }
        }
        if (!best || best.hurts.some((h) => f - h < HURT_FRAMES)) continue;
        best.hurts.push(f);
        const dx = best.X[f] - a.X[f], dz = best.Z[f] - a.Z[f];
        const l = Math.hypot(dx, dz) || 1;
        const ux = dx / l, uz = dz / l;
        for (let t = f; t < frames; t++) {
          const u = Math.min(1, (t - f) / 8);
          const e = 0.45 * (1 - (1 - u) * (1 - u));
          best.X[t] += ux * e;
          best.Z[t] += uz * e;
          if (t - f < 9) best.hop[t] += 0.3 * 4 * ((t - f) / 9) * (1 - (t - f) / 9);
        }
      }
    }),
  );
};

const blur = (a: Float32Array, rad: number) => {
  const out = new Float32Array(a.length);
  const w: number[] = [];
  for (let k = -rad; k <= rad; k++) w.push(Math.exp(-(k * k) / (2 * (rad / 2.5) ** 2)));
  for (let i = 0; i < a.length; i++) {
    let s = 0, ws = 0;
    for (let k = -rad; k <= rad; k++) {
      const j = i + k;
      if (j < 0 || j >= a.length) continue;
      s += a[j] * w[k + rad];
      ws += w[k + rad];
    }
    out[i] = s / ws;
  }
  return out;
};

/**
 * Keeps hitboxes apart. Each pass measures the overlaps, gives the correction to the lower-priority actor (or shares it), blurs
 * it over time so the actor steps aside before contact instead of popping, and repeats until nothing overlaps.
 */
export const separate = (bodies: Body[], frames: number, passes = 8) => {
  const n = bodies.length;
  const yr = (b: Body, f: number): [number, number] => [b.Y[f] + b.hop[f], b.Y[f] + b.hop[f] + b.h];
  for (let pass = 0; pass <= passes; pass++) {
    const final = pass === passes;
    const OX = bodies.map(() => new Float32Array(frames)), OZ = bodies.map(() => new Float32Array(frames));
    let worst = 0;
    for (let f = 0; f < frames; f++) {
      for (let i = 0; i < n; i++)
        for (let j = i + 1; j < n; j++) {
          const a = bodies[i], b = bodies[j];
          if (a.priority >= 3 && b.priority >= 3) continue; // two scripted players are the author's business
          const [ay0, ay1] = yr(a, f), [by0, by1] = yr(b, f);
          if (ay1 <= by0 || by1 <= ay0) continue;
          let dx = b.X[f] - a.X[f], dz = b.Z[f] - a.Z[f];
          let d = Math.hypot(dx, dz);
          const need = a.r + b.r + 0.04 - d;
          if (need <= 0) continue;
          if (d < 1e-4) { dx = Math.cos(i * 2.4 + j); dz = Math.sin(i * 2.4 + j); d = 1; }
          const ux = dx / d, uz = dz / d;
          const wa = a.priority > b.priority ? 0 : a.priority < b.priority ? 1 : 0.5;
          OX[i][f] -= ux * need * wa; OZ[i][f] -= uz * need * wa;
          OX[j][f] += ux * need * (1 - wa); OZ[j][f] += uz * need * (1 - wa);
          worst = Math.max(worst, need);
        }
      for (let i = 0; i < n; i++) {
        const b = bodies[i];
        if (b.priority >= 3) continue;
        for (const box of b.avoid) {
          const m = pushOut(b.X[f] + OX[i][f], b.Z[f] + OZ[i][f], b.r + 0.02, box);
          if (m) { OX[i][f] += m[0]; OZ[i][f] += m[1]; worst = Math.max(worst, Math.hypot(m[0], m[1])); }
        }
      }
    }
    if (worst < 0.005) return;
    bodies.forEach((b, i) => {
      const ox = final ? OX[i] : blur(OX[i], 8), oz = final ? OZ[i] : blur(OZ[i], 8);
      const gain = final ? 1 : 1.6; // blurring lowers the peaks: overshoot a little so the passes converge quickly
      for (let f = 0; f < frames; f++) { b.X[f] += ox[f] * gain; b.Z[f] += oz[f] * gain; }
    });
  }
};

/** Smallest gap between two bodies' hitboxes over the frames, for the validator (negative = overlap). */
export const minGap = (a: Body, b: Body, frames: number) => {
  let g = Infinity, at = -1;
  for (let f = 0; f < frames; f++) {
    if (a.Y[f] + a.h <= b.Y[f] || b.Y[f] + b.h <= a.Y[f]) continue;
    const d = Math.hypot(a.X[f] - b.X[f], a.Z[f] - b.Z[f]) - a.r - b.r;
    if (d < g) { g = d; at = f; }
  }
  return { gap: g, at };
};
