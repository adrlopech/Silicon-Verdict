/**
 * Minimal EMF/OptiFine CEM runtime: loads .jem models (+ .jpm includes) and evaluates their
 * animation expressions frame by frame (state persists between frames, like in the game).
 * Used with Fresh Animations packs (player + chest) from the user's own downloads.
 */

export type V3 = [number, number, number];

export interface JBox {
  c: [number, number, number, number, number, number]; // x,y,z,w,h,d
  size: [number, number, number];
  uv: [number, number];
  add: number;
}
export interface JNode {
  id: string;
  translate: V3;
  rotate: V3; // degrees
  boxes: JBox[];
  children: JNode[];
  depth: number;
}
export interface JModel {
  nodes: JNode[];
  anims: Record<string, string>[];
  tex: [number, number];
}

type Json = any; // eslint-disable-line @typescript-eslint/no-explicit-any

const parseNode = (m: Json, depth: number): JNode => ({
  id: m.id ?? m.part ?? 'node',
  translate: (m.translate ?? [0, 0, 0]) as V3,
  rotate: (m.rotate ?? [0, 0, 0]) as V3,
  boxes: (m.boxes ?? []).map((b: Json) => ({ c: b.coordinates, size: [b.coordinates[3], b.coordinates[4], b.coordinates[5]], uv: b.textureOffset ?? [0, 0], add: b.sizeAdd ?? 0 })),
  children: (m.submodels ?? []).map((s: Json) => parseNode(s, depth + 1)),
  depth,
});

const collectAnims = (m: Json, out: Record<string, string>[]) => {
  (m.animations ?? []).forEach((a: Record<string, string>) => out.push(a));
  (m.submodels ?? []).forEach((s: Json) => collectAnims(s, out));
};

export const loadModel = async (base: string, jem: string): Promise<JModel> => {
  const get = async (f: string) => (await fetch(`${base}/${f}`)).json();
  const j = await get(jem);
  const nodes: JNode[] = [];
  const anims: Record<string, string>[] = [];
  for (const m of j.models as Json[]) {
    let src = m;
    if (m.model) {
      const inc = await get(m.model).catch(() => ({}));
      collectAnims(inc, anims);
      // an included part file may also carry geometry
      if (inc.boxes || inc.submodels) src = { ...inc, ...m, boxes: inc.boxes, submodels: inc.submodels };
    }
    collectAnims(m, anims);
    if ((src.boxes && src.boxes.length) || (src.submodels && src.submodels.length) || (!m.model && m.part !== 'root')) nodes.push(parseNode(src, 0));
  }
  return { nodes, anims, tex: j.textureSize ?? [64, 64] };
};

/* ---------------- expression evaluator ---------------- */

type Env = { V: Record<string, number>; B: Record<string, number>; I: Record<string, number> };

const wrapRad = (x: number) => {
  const t = (x + Math.PI) % (2 * Math.PI);
  return (t < 0 ? t + 2 * Math.PI : t) - Math.PI;
};
let seed = 1;
const rand = () => {
  seed = (seed * 16807) % 2147483647;
  return (seed - 1) / 2147483646;
};
const FUNCS: Record<string, (...a: number[]) => number> = {
  sin: Math.sin, cos: Math.cos, tan: Math.tan, asin: Math.asin, acos: Math.acos, atan: Math.atan, atan2: Math.atan2,
  abs: Math.abs, min: Math.min, max: Math.max, floor: Math.floor, ceil: Math.ceil, round: Math.round, sqrt: Math.sqrt,
  exp: Math.exp, log: Math.log, pow: Math.pow,
  clamp: (x, a, b) => Math.min(b, Math.max(a, x)),
  lerp: (t, a, b) => a + (b - a) * t,
  fmod: (a, b) => a - b * Math.floor(a / b),
  torad: (d) => (d * Math.PI) / 180,
  todeg: (r) => (r * 180) / Math.PI,
  wraprad: wrapRad,
  wrapdeg: (d) => ((((d + 180) % 360) + 360) % 360) - 180,
  between: (x, a, b) => (x >= a && x <= b ? 1 : 0),
  // random(id) is a per-entity constant in EMF; only the bare random() changes over time
  random: (...a: number[]) => (a.length ? ((Math.sin((a[0] + 1) * 12.9898 + 78.233) * 43758.5453) % 1 + 1) % 1 : rand()),
  exists: () => 0,
  nbt: () => 0,
  iregex: () => 0,
  regex: () => 0,
  equals: (a, b) => (a === b ? 1 : 0),
  if: (...a: number[]) => {
    let i = 0;
    for (; i + 1 < a.length; i += 2) if (a[i]) return a[i + 1];
    return a.length % 2 ? a[a.length - 1] : 0;
  },
};

const compile = (expr: string): ((env: Env) => number) | null => {
  if (/['"]/.test(expr)) return null;
  const js = expr.replace(/[A-Za-z_][A-Za-z_0-9]*(?:\.[A-Za-z_0-9]+)*/g, (id, off: number) => {
    const rest = expr.slice(off + id.length);
    if (/^\s*\(/.test(rest)) return `F[${JSON.stringify(id)}]`;
    if (id === 'true') return '1';
    if (id === 'false') return '0';
    if (id === 'pi') return 'Math.PI';
    if (id.startsWith('var.') || id.startsWith('varb.')) return `(V[${JSON.stringify(id)}]||0)`;
    return `G(${JSON.stringify(id)})`;
  });
  try {
    const fn = new Function('V', 'G', 'F', `return (${js});`) as (V: Env['V'], G: (n: string) => number, F: typeof FUNCS) => number;
    return (env) => {
      const G = (n: string) => (n in env.B ? env.B[n] : n in env.I ? env.I[n] : 0);
      const r = fn(env.V, G, FUNCS);
      const n = typeof r === 'boolean' ? (r ? 1 : 0) : Number(r);
      return Number.isFinite(n) ? n : 0;
    };
  } catch {
    return null;
  }
};

export type Snapshot = Record<string, number>;

export const simulate = (model: JModel, frames: number, inputs: (f: number) => Record<string, number>, baseline: (i: Record<string, number>) => Record<string, number>): Snapshot[] => {
  const prog: [string, (e: Env) => number][] = [];
  model.anims.forEach((a) => Object.entries(a).forEach(([k, v]) => {
    const fn = compile(String(v));
    if (fn) prog.push([k, fn]);
  }));
  const V: Env['V'] = {};
  seed = 1;
  const out: Snapshot[] = [];
  for (let f = 0; f < frames; f++) {
    const I = inputs(f);
    const B = baseline(I);
    const env: Env = { V, B, I };
    for (const [k, fn] of prog) {
      let r = 0;
      try { r = fn(env); } catch { r = 0; }
      if (k.startsWith('var.') || k.startsWith('varb.')) V[k] = k.startsWith('varb.') ? (r ? 1 : 0) : r;
      else B[k] = r;
    }
    out.push({ ...B });
  }
  return out;
};

/** Vanilla Minecraft 1.20 PlayerModel pose (what OptiFine/EMF exposes as the default bone values before expressions run). */
export const vanillaPlayerBaseline = (i: Record<string, number>): Record<string, number> => {
  const ls = i.limb_swing || 0, sp = i.limb_speed || 0, age = i.age || 0, at = i.swing_progress || 0;
  const hx = ((i.head_pitch || 0) * Math.PI) / 180, hy = ((i.head_yaw || 0) * Math.PI) / 180;
  let rax = Math.cos(ls * 0.6662 + Math.PI) * 2 * sp * 0.5, lax = Math.cos(ls * 0.6662) * 2 * sp * 0.5;
  let ray = 0, lay = 0, raz = 0, laz = 0;
  const rlx = Math.cos(ls * 0.6662) * 1.4 * sp, llx = Math.cos(ls * 0.6662 + Math.PI) * 1.4 * sp;
  if (i.is_holding_item_right) rax = rax * 0.5 - 0.31415927;
  let bodyRy = 0;
  let rp: [number, number, number] = [-5, 2, 0], lp: [number, number, number] = [5, 2, 0];
  if (at > 0) {
    bodyRy = Math.sin(Math.sqrt(at) * Math.PI * 2) * 0.2;
    rp = [-Math.cos(bodyRy) * 5, 2, Math.sin(bodyRy) * 5];
    lp = [Math.cos(bodyRy) * 5, 2, -Math.sin(bodyRy) * 5];
    ray += bodyRy; lay += bodyRy; lax += bodyRy;
    let f = 1 - at; f *= f; f *= f; f = 1 - f;
    const f1 = Math.sin(f * Math.PI), f2 = Math.sin(at * Math.PI) * -(hx - 0.7) * 0.75;
    rax -= f1 * 1.2 + f2;
    ray += bodyRy * 2;
    raz += Math.sin(at * Math.PI) * -0.4;
  }
  raz += Math.cos(age * 0.09) * 0.05 + 0.05; rax += Math.sin(age * 0.067) * 0.05;
  laz -= Math.cos(age * 0.09) * 0.05 + 0.05; lax -= Math.sin(age * 0.067) * 0.05;
  const b: Record<string, number> = {};
  const put = (bone: string, p: [number, number, number], r: [number, number, number]) => {
    b[`${bone}.tx`] = p[0]; b[`${bone}.ty`] = p[1]; b[`${bone}.tz`] = p[2];
    b[`${bone}.rx`] = r[0]; b[`${bone}.ry`] = r[1]; b[`${bone}.rz`] = r[2];
  };
  put('head', [0, 0, 0], [hx, hy, 0]); put('headwear', [0, 0, 0], [hx, hy, 0]);
  put('body', [0, 0, 0], [0, bodyRy, 0]); put('jacket', [0, 0, 0], [0, bodyRy, 0]);
  put('right_arm', rp, [rax, ray, raz]); put('right_sleeve', rp, [rax, ray, raz]);
  put('left_arm', lp, [lax, lay, laz]); put('left_sleeve', lp, [lax, lay, laz]);
  put('right_leg', [-1.9, 12, 0.1], [rlx, 0.005, 0.005]); put('right_pants', [-1.9, 12, 0.1], [rlx, 0.005, 0.005]);
  put('left_leg', [1.9, 12, 0.1], [llx, -0.005, -0.005]); put('left_pants', [1.9, 12, 0.1], [llx, -0.005, -0.005]);
  return b;
};
