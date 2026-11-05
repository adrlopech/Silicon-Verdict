/**
 * Minecraft video kit — one table with everything that depends on the kind of actor:
 * vanilla hitbox (EntityType sizes), model scale (players and villagers render at 0.9375, the rest at 1 px = 1/16 block),
 * leg length and swing amplitude (used by anim.ts) and the stride that keeps the feet from skating, push priority and step sound.
 */
export type HumanoidKind = 'player' | 'zombie' | 'skeleton';
export type MobKind = 'pig' | 'cow' | 'chicken' | 'creeper' | 'sheep' | 'villager' | 'spider' | 'cave_spider';
export type ActorKind = HumanoidKind | MobKind;

export interface KindInfo {
  w: number; // hitbox width (blocks) — vanilla
  h: number; // hitbox height (blocks) — vanilla
  unit: number; // model scale: blocks per model pixel
  leg: number; // leg length in model pixels (0 = no swinging legs)
  amp: number; // walking leg swing amplitude (radians)
  ref: number; // speed (blocks/s) at which the walk cycle reaches full amplitude
  stride: number; // radians of limb phase per block walked
  priority: number; // who gives way when two actors would overlap (lower is pushed)
  stepEvery: number; // a footstep sound every N foot landings
}

export const PLAYER_UNIT = 0.9375 / 16;
const PX = 1 / 16;

/** Stride with no foot skating: the planted foot sweeps 2·L·sin(A) per half cycle, so the body must advance exactly that much. */
export const noSlipStride = (legBlocks: number, amp: number) => Math.PI / (2 * legBlocks * Math.sin(amp));

const mk = (w: number, h: number, unit: number, leg: number, amp: number, ref: number, priority: number, stepEvery = 1, stride?: number): KindInfo => ({
  w, h, unit, leg, amp, ref, priority, stepEvery, stride: stride ?? (leg ? noSlipStride(leg * unit, amp) : 4),
});

export const KINDS: Record<ActorKind, KindInfo> = {
  player: mk(0.6, 1.8, PLAYER_UNIT, 12, 0.9, 4.0, 3),
  zombie: mk(0.6, 1.95, PX, 12, 0.9, 4.0, 2),
  skeleton: mk(0.6, 1.99, PX, 12, 0.9, 4.0, 2),
  villager: mk(0.6, 1.95, PLAYER_UNIT, 12, 0.7, 1.8, 2),
  creeper: mk(0.6, 1.7, PX, 6, 0.6, 2.2, 1, 2),
  pig: mk(0.9, 0.9, PX, 6, 0.7, 1.8, 1, 2),
  cow: mk(0.9, 1.4, PX, 12, 0.7, 1.8, 1, 2),
  sheep: mk(0.9, 1.3, PX, 12, 0.7, 1.8, 1, 2),
  chicken: mk(0.4, 0.7, PX, 5, 1.0, 1.6, 1, 2),
  spider: mk(1.4, 0.9, PX, 0, 0.4, 1.6, 1, 2, 4.0),
  cave_spider: mk(0.7, 0.5, PX * 0.7, 0, 0.4, 1.6, 1, 2, 5.0),
};

export const HUMANOIDS: ActorKind[] = ['player', 'zombie', 'skeleton'];
export const isHumanoid = (k: ActorKind): k is HumanoidKind => HUMANOIDS.includes(k);
export const radiusOf = (k: ActorKind) => KINDS[k].w / 2;
