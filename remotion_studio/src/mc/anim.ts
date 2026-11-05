/**
 * Minecraft video kit — vanilla animations (HumanoidModel / QuadrupedModel / ChickenModel / CreeperModel setupAnim),
 * softened like the animated trailers:
 *   - limb amplitude follows the real speed (stride and pace always match) and is lower than vanilla (frantic on camera)
 *   - walking, mining, reaching, waving... all ease in and out (no snapping between states)
 *   - forward lean, counter-twist of the torso, soft bounce, head counter-rotation and head leading each turn
 * Angles are in the vanilla (y-down) frame; use `e3()` from core to convert.
 */
import { Rot, V3, sstep } from './core';
import type { Track } from './choreo';
import { ActorKind, KINDS } from './kinds';

/** Hip drop that keeps the feet near the ground: a leg of `leg` px swung by `a` lifts its foot leg·(1−cos a); lower the body by part of it. */
const plant = (leg: number, a: number, k = 0.55) => -k * leg * (1 - Math.cos(a));

export interface Pose {
  head: Rot; body: Rot; rArm: Rot; lArm: Rot; rLeg: Rot; lLeg: Rot;
  rArmPos: V3; lArmPos: V3; // vanilla pivots in px (x, y down from the neck, z)
  bob: number; // body lift in px
  pitch: number; // whole-body forward tilt around the hips (swimming)
  drop: number; // whole-body lowering in px (swimming)
}

export interface HumanoidOpts {
  hold?: boolean; // item in the right hand (vanilla "item" arm pose). default true
  armsForward?: boolean; // zombie pose
  sneak?: boolean;
  kind?: ActorKind; // amplitude / speed reference from kinds.ts (default player)
}

export const humanoidPose = (T: Track, f: number, o: HumanoidOpts = {}): Pose => {
  const i = T.at(f);
  const hold = o.hold ?? true;
  const K = KINDS[o.kind ?? 'player'];
  const speed = T.speed[i];
  const w = sstep(speed / K.ref);
  const run = sstep((speed - 4.6) / 1.6); // sprint: bigger strides, more lean
  const age = (f * 20) / 30;
  const ph = T.dist[i] * T.stride;
  const mineAmt = T.amt('mine', f), attackAmt = T.amt('attack', f);
  const m = Math.max(mineAmt, attackAmt);
  const swingKind = attackAmt > mineAmt ? 'attack' : 'mine';
  const r = T.amt('reach', f), wv = T.amt('wave', f), use = T.amt('use', f);
  const sw = T.swim(f), cl = T.amt('climb', f);
  const jp = T.amt('jump', f) * Math.sin(Math.PI * T.prog('jump', f)); // 0..1 over the air time

  const lr = Math.cos(ph) * (K.amp + 0.18 * run) * w; // stride (kinds.ts) is matched to this amplitude: no foot skating
  const armAmp = 0.62 + 0.3 * run;
  let rax = Math.cos(ph + Math.PI) * armAmp * w, lax = Math.cos(ph) * armAmp * w;
  let ray = 0, raz = 0, lay = 0, laz = 0;
  if (hold) rax = rax * 0.5 - 0.31415927; // vanilla item-in-hand pose
  const idle = 1 - w;
  raz += (Math.cos(age * 0.09) * 0.05 + 0.05) * idle;
  rax += Math.sin(age * 0.067) * 0.05 * idle;
  laz -= (Math.cos(age * 0.09) * 0.05 + 0.05) * idle;
  lax -= Math.sin(age * 0.067) * 0.05 * idle;
  if (o.armsForward) {
    // vanilla AnimationUtils.animateZombieArms (non-aggressive)
    const f4 = -Math.PI / 2.25;
    rax = f4 + Math.sin(age * 0.067) * 0.05 + Math.cos(ph + Math.PI) * 0.12 * w;
    lax = f4 - Math.sin(age * 0.067) * 0.05 + Math.cos(ph) * 0.12 * w;
    ray = -0.1; lay = 0.1;
    raz = Math.cos(age * 0.09) * 0.05 + 0.05;
    laz = -(Math.cos(age * 0.09) * 0.05 + 0.05);
  }
  let bodyRx = 0.1 * w + 0.12 * run * w + Math.sin(age * 0.07) * 0.012 * idle;
  let bodyRy = Math.cos(ph) * 0.09 * w;
  let bob = plant(12, lr); // body lowest when the legs are spread, feet stay on the ground
  if (o.sneak) { bodyRx += 0.45; bob -= 2.2; }
  let rp: V3 = [-5, 2, 0], lp: V3 = [5, 2, 0];
  let headRx = -bodyRx * 0.75, headRy = -bodyRy * 0.6 - T.lead(f) - T.look[i]; // head starts turning a beat before the body

  // vanilla attack animation (swing progress), eased in/out
  if (m > 0.001) {
    const p = T.prog(swingKind, f);
    rax = rax * (1 - m) + -0.55 * m; // arm lifted towards the work
    const by = Math.sin(Math.sqrt(p) * Math.PI * 2) * 0.2 * m;
    bodyRy += by;
    rp = [-Math.cos(by) * 5, 2, Math.sin(by) * 5];
    lp = [Math.cos(by) * 5, 2, -Math.sin(by) * 5];
    ray += by; lay += by; lax += by;
    let q = 1 - p; q = q * q * q; q = 1 - q; // vanilla uses ^4; ^3 keeps the strike softer
    rax -= (Math.sin(q * Math.PI) * 1.2 + Math.sin(p * Math.PI) * 0.5) * m;
    ray += by * 2;
    raz += Math.sin(p * Math.PI) * -0.4 * m;
    bodyRx += 0.07 * m; headRx += 0.12 * m;
  }
  if (r > 0.001) { // reaching forward (chest, lever, button...)
    rax = rax * (1 - r) + (-1.2 + Math.sin(f * 0.18) * 0.06) * r;
    bodyRx += 0.12 * r; headRx += 0.18 * r; bodyRy += -0.15 * r;
  }
  if (wv > 0.001) { // wave hello
    rax = rax * (1 - wv) + -2.7 * wv;
    raz = raz * (1 - wv) + (-0.25 + Math.sin(f * 0.34) * 0.45) * wv;
    headRy += -0.12 * wv; bodyRx -= 0.03 * wv;
  }
  if (use > 0.001) { // eat / drink: hand to the mouth, chewing bob
    rax = rax * (1 - use) + (-1.45 + Math.sin(f * 0.6) * 0.07) * use;
    ray += -0.35 * use;
    headRx += (0.08 + Math.sin(f * 0.8) * 0.05) * use;
  }
  let rLeg = lr, lLeg = -lr;
  if (jp > 0.001) { // jump: arms swing up, legs trail behind
    rax -= 0.9 * jp; lax -= 0.9 * jp; raz -= 0.15 * jp; laz += 0.15 * jp;
    rLeg = lr * (1 - jp) + 0.5 * jp; lLeg = -lr * (1 - jp) + 0.2 * jp;
    bodyRx -= 0.06 * jp; headRx += 0.1 * jp;
  }
  let pitch = 0, drop = 0;
  if (sw > 0.001) { // crawl stroke at the water surface: body flat, arms circle overhead, legs flutter
    const sp = T.dist[i] * 2.6;
    rax = rax * (1 - sw) + (-2.9 + Math.cos(sp) * 0.85) * sw;
    lax = lax * (1 - sw) + (-2.9 + Math.cos(sp + Math.PI) * 0.85) * sw;
    raz *= 1 - sw; laz *= 1 - sw;
    rLeg = rLeg * (1 - sw) + Math.sin(sp * 2) * 0.4 * sw;
    lLeg = lLeg * (1 - sw) - Math.sin(sp * 2) * 0.4 * sw;
    headRx = headRx * (1 - sw) + -1.05 * sw; // lift the head forward
    bodyRy = bodyRy * (1 - sw) + Math.cos(sp) * 0.12 * sw;
    pitch = 1.3 * sw; drop = -15 * sw; bob *= 1 - sw; // back just breaking the surface, like vanilla swimming
  }
  if (cl > 0.001) { // ladder: hands alternate overhead, knees come up one after the other
    const cp = T.y[i] * 6.5;
    rax = rax * (1 - cl) + (-2.7 + Math.sin(cp) * 0.55) * cl;
    lax = lax * (1 - cl) + (-2.7 - Math.sin(cp) * 0.55) * cl;
    raz = raz * (1 - cl) - 0.2 * cl; laz = laz * (1 - cl) + 0.2 * cl;
    rLeg = rLeg * (1 - cl) + (-0.45 + Math.sin(cp + Math.PI / 2) * 0.55) * cl;
    lLeg = lLeg * (1 - cl) + (-0.45 - Math.sin(cp + Math.PI / 2) * 0.55) * cl;
    headRx += -0.3 * cl; bodyRx -= 0.04 * cl; bob *= 1 - cl;
  }
  return {
    head: [headRx, headRy, 0], body: [bodyRx, bodyRy, 0], rArm: [rax, ray, raz], lArm: [lax, lay, laz],
    rLeg: [rLeg, 0.005, 0.005], lLeg: [lLeg, -0.005, -0.005], rArmPos: rp, lArmPos: lp, bob, pitch, drop,
  };
};

export interface MobPose {
  head: Rot;
  legs: Rot[]; // pig/cow/creeper: rear-right, rear-left, front-right, front-left; chicken: right, left
  wings: Rot[]; // chicken only: right, left
  bob: number; // px
  headZ: number; // px (chicken head pecking)
  scale: number; // creeper swell
}

/** Pig, cow, sheep and creeper: diagonal leg pairs, gentle head sway. */
export const quadrupedPose = (T: Track, f: number, kind: ActorKind = 'pig'): MobPose => {
  const K = KINDS[kind];
  const i = T.at(f);
  const w = sstep(T.speed[i] / K.ref);
  const age = (f * 20) / 30;
  const ph = T.dist[i] * T.stride;
  const a = Math.cos(ph) * K.amp * w;
  return {
    head: [Math.sin(age * 0.05) * 0.05 + Math.sin(ph * 2) * 0.05 * w, -T.lead(f) * 0.8 - T.look[i] + Math.sin(age * 0.031) * 0.06 * (1 - w), 0],
    legs: [[a, 0, 0], [-a, 0, 0], [-a, 0, 0], [a, 0, 0]],
    wings: [], bob: plant(K.leg, a, 0.5), headZ: 0, scale: 1,
  };
};

export const chickenPose = (T: Track, f: number): MobPose => {
  const K = KINDS.chicken;
  const i = T.at(f);
  const w = sstep(T.speed[i] / K.ref);
  const age = (f * 20) / 30;
  const ph = T.dist[i] * T.stride;
  const a = Math.cos(ph) * K.amp * w;
  const flutter = Math.sin(age * 0.5) * 0.05;
  return {
    head: [Math.sin(age * 0.09) * 0.05, -T.lead(f) * 0.8 - T.look[i], 0],
    legs: [[a, 0, 0], [-a, 0, 0]],
    wings: [[0, 0, 0.08 + flutter], [0, 0, -0.08 - flutter]],
    bob: plant(K.leg, a, 0.5), headZ: Math.sin(ph * 2) * 1.2 * w, scale: 1,
  };
};

/** Villager: legs like a biped, slow head sway (the crossed arms are part of the model). */
export const villagerPose = (T: Track, f: number): MobPose => {
  const K = KINDS.villager;
  const i = T.at(f);
  const w = sstep(T.speed[i] / K.ref);
  const age = (f * 20) / 30;
  const a = Math.cos(T.dist[i] * T.stride) * K.amp * w;
  return {
    head: [Math.sin(age * 0.04) * 0.04, -T.lead(f) * 0.8 - T.look[i] + Math.sin(age * 0.025) * 0.09 * (1 - w), 0],
    legs: [[a, 0, 0], [-a, 0, 0]], wings: [], bob: plant(K.leg, a), headZ: 0, scale: 1,
  };
};

/** Spider: eight legs in four phase-shifted pairs (vanilla SpiderModel.setupAnim); values are deltas over the rest pose. */
export const spiderPose = (T: Track, f: number): MobPose => {
  const i = T.at(f);
  const w = sstep(T.speed[i] / KINDS.spider.ref);
  const age = (f * 20) / 30;
  const ls = T.dist[i] * T.stride;
  const legs: Rot[] = [];
  [0, Math.PI, Math.PI / 2, (3 * Math.PI) / 2].forEach((ph) => {
    const y = -Math.cos(ls * 2 + ph) * 0.4 * w, z = Math.abs(Math.sin(ls + ph)) * 0.4 * w;
    legs.push([0, y, z], [0, -y, -z]); // right leg, then left leg (mirrored)
  });
  return {
    head: [Math.sin(age * 0.05) * 0.04, -T.lead(f) * 0.8 - T.look[i] + Math.sin(age * 0.03) * 0.08 * (1 - w), 0],
    legs, wings: [], bob: 0, headZ: 0, scale: 1,
  };
};
