/**
 * Minecraft video kit — actors: humanoids (player skin, zombie, skeleton) and vanilla mobs (pig, cow, chicken, creeper).
 * Every actor is driven by a choreography Track + the vanilla animations in anim.ts.
 */
import React from 'react';
import { MobPose, chickenPose, humanoidPose, quadrupedPose, spiderPose, villagerPose } from './anim';
import type { Track } from './choreo';
import { HURT_TINT, Rot, Sprite3D, TexBox, V3, e3 } from './core';
import { HumanoidKind, KINDS, MobKind } from './kinds';

export type { HumanoidKind, MobKind };

/** Vanilla blob shadow under the feet (stays on the ground while jumping, shrinks with height). */
const Shadow: React.FC<{ r: number; track: Track; f: number }> = ({ r, track, f }) => {
  const y = track.y[track.at(f)];
  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0.012 - y, 0]} scale={1 - Math.min(0.4, y * 0.3)}>
      <circleGeometry args={[r, 16]} />
      <meshBasicMaterial color="#000" transparent opacity={0.25 * (1 - Math.min(0.6, y * 0.4))} depthWrite={false} />
    </mesh>
  );
};

/** Size of the item in the hand: tools are drawn big, small items (books, ingots, gems, food) much smaller. */
const HELD_SCALE: Record<string, number> = { item_book: 0.42, item_writable_book: 0.42, item_paper: 0.42, item_emerald: 0.5, item_diamond: 0.5, item_gold_ingot: 0.5, item_redstone: 0.5, item_coal: 0.5, item_bread: 0.55, item_apple: 0.55, item_wheat: 0.55 };

/** Warm colour multiplier for an actor near torches (null = none). `warm` is quantised by the caller so the shared material cache stays small. */
const warmTint = (w: number): [number, number, number] | undefined => (w > 0.01 ? [1 + w * 1.0, 1 + w * 0.6, 1 + w * 0.15] : undefined);

/* ------------------------------ humanoids ------------------------------ */

export const Humanoid: React.FC<{
  track: Track;
  f: number;
  kind?: HumanoidKind;
  skin?: string; // texture name (player: 'skin')
  hand?: string; // item sprite held in the right hand, e.g. 'item_diamond_pickaxe'
  sneak?: boolean;
  warm?: number; // 0..~0.6: torch light reaching this actor (warm colour boost)
}> = ({ track, f, kind = 'player', skin, hand, sneak, warm = 0 }) => {
  const P = humanoidPose(track, f, { hold: kind === 'player' && !!hand, armsForward: kind === 'zombie', sneak, kind });
  const i = track.at(f);
  const U1 = KINDS[kind].unit; // players render at 0.9375, zombies and skeletons at full size
  const tint = track.hurt(f) > 0.05 ? HURT_TINT : warmTint(warm);
  const tex = skin ?? (kind === 'player' ? 'skin' : `mob_${kind}`);
  const thin = kind === 'skeleton';
  const ts: [number, number] = kind === 'skeleton' ? [64, 32] : [64, 64];
  const overlays = kind === 'player';
  const T = (o: [number, number], s: [number, number, number], pos: V3, inflate = 0, mirror = false) => ({
    name: tex, origin: o, size: s, position: [pos[0] * U1, pos[1] * U1, pos[2] * U1] as V3, unit: U1, inflate, texSize: ts, mirror, tint,
  });
  const limb: [number, number, number] = thin ? [2, 12, 2] : [4, 12, 4];
  const arm = (right: boolean) => {
    const a = right ? P.rArm : P.lArm, pv = right ? P.rArmPos : P.lArmPos;
    const dx = thin ? 0 : right ? -1 : 1;
    const origin: [number, number] = right || thin ? [40, 16] : [32, 48];
    return (
      <group key={right ? 'r' : 'l'} position={[pv[0] * U1, (24 - pv[1]) * U1, -pv[2] * U1]} rotation={e3(a)}>
        <TexBox {...T(origin, limb, [dx, -4, 0], 0, thin && !right)} />
        {overlays && <TexBox {...T(right ? [40, 32] : [48, 48], limb, [dx, -4, 0], 0.5)} />}
        {right && hand && (
          <group position={[-U1, -9 * U1, U1]} rotation={[-0.55, 0, 0]}>
            <Sprite3D name={hand} scale={HELD_SCALE[hand] ?? 0.95} position={[0, HELD_SCALE[hand] ? -0.2 : -0.295, 0.04]} rotation={[0, Math.PI / 2, (-3 * Math.PI) / 4]} />
          </group>
        )}
      </group>
    );
  };
  const leg = (right: boolean) => (
    <group key={right ? 'rl' : 'll'} position={[(thin ? (right ? -2 : 2) : right ? -1.9 : 1.9) * U1, 12 * U1, -0.1 * U1]} rotation={e3(right ? P.rLeg : P.lLeg)}>
      <TexBox {...T(right || thin ? [0, 16] : [16, 48], limb, [0, -6, 0], 0, thin && !right)} />
      {overlays && <TexBox {...T(right ? [0, 32] : [0, 48], limb, [0, -6, 0], 0.5)} />}
    </group>
  );
  return (
    <group position={[track.x[i], track.y[i], track.z[i]]} rotation={[0, track.face[i], 0]}>
      <Shadow r={0.42 * U1 * 16} track={track} f={f} />
      <group position={[0, (P.bob + P.drop + 12) * U1, 0]} rotation={[P.pitch, 0, 0]}>
       <group position={[0, -12 * U1, 0]}>
        <group position={[0, 24 * U1, 0]} rotation={e3(P.head)}>
          <TexBox {...T([0, 0], [8, 8, 8], [0, 4, 0])} />
          {overlays && <TexBox {...T([32, 0], [8, 8, 8], [0, 4, 0], 1)} />}
        </group>
        <group position={[0, 24 * U1, 0]} rotation={e3(P.body)}>
          <TexBox {...T([16, 16], [8, 12, 4], [0, -6, 0])} />
          {overlays && <TexBox {...T([16, 32], [8, 12, 4], [0, -6, 0], 0.5)} />}
        </group>
        {arm(true)}
        {arm(false)}
        {leg(true)}
        {leg(false)}
       </group>
      </group>
    </group>
  );
};

/* ------------------------------ table-driven mobs ------------------------------ */
interface BoxDef { origin: [number, number]; box: [number, number, number, number, number, number]; mirror?: boolean; tex?: string; inflate?: number }
interface PartDef { id: string; pivot: V3; rot?: Rot; boxes: BoxDef[] }

// Vanilla 1.20 model layouts (pivot in the vanilla frame: x, y down from the 24px line, z; boxes relative to the pivot).
const MOBS: Record<MobKind, { parts: PartDef[]; tex: [number, number]; shadow: number; scale?: number; texName?: string }> = {
  pig: {
    tex: [64, 32], shadow: 0.55,
    parts: [
      { id: 'head', pivot: [0, 12, -6], boxes: [{ origin: [0, 0], box: [-4, -4, -8, 8, 8, 8] }, { origin: [16, 16], box: [-2, 0, -9, 4, 3, 1] }] },
      { id: 'body', pivot: [0, 11, 2], rot: [Math.PI / 2, 0, 0], boxes: [{ origin: [28, 8], box: [-5, -10, -7, 10, 16, 8] }] },
      ...(
        [['l0', -3, 7], ['l1', 3, 7], ['l2', -3, -5], ['l3', 3, -5]] as [string, number, number][]
      ).map(([id, x, z]): PartDef => ({ id, pivot: [x, 18, z], boxes: [{ origin: [0, 16], box: [-2, 0, -2, 4, 6, 4] }] })),
    ],
  },
  cow: {
    tex: [64, 32], shadow: 0.7,
    parts: [
      {
        id: 'head', pivot: [0, 4, -8],
        boxes: [{ origin: [0, 0], box: [-4, -4, -6, 8, 8, 6] }, { origin: [22, 0], box: [-5, -5, -4, 1, 3, 1] }, { origin: [22, 0], box: [4, -5, -4, 1, 3, 1], mirror: true }],
      },
      { id: 'body', pivot: [0, 5, 2], rot: [Math.PI / 2, 0, 0], boxes: [{ origin: [18, 4], box: [-6, -10, -7, 12, 18, 10] }, { origin: [52, 0], box: [-2, 2, -8, 4, 6, 1] }] },
      ...(
        [['l0', -4, 7], ['l1', 4, 7], ['l2', -4, -6], ['l3', 4, -6]] as [string, number, number][]
      ).map(([id, x, z]): PartDef => ({ id, pivot: [x, 12, z], boxes: [{ origin: [0, 16], box: [-2, 0, -2, 4, 12, 4] }] })),
    ],
  },
  chicken: {
    tex: [64, 32], shadow: 0.3,
    parts: [
      { id: 'head', pivot: [0, 15, -4], boxes: [{ origin: [0, 0], box: [-2, -6, -2, 4, 6, 3] }, { origin: [14, 0], box: [-2, -4, -4, 4, 2, 2] }, { origin: [14, 4], box: [-1, -2, -3, 2, 2, 2] }] },
      { id: 'body', pivot: [0, 16, 0], rot: [Math.PI / 2, 0, 0], boxes: [{ origin: [0, 9], box: [-3, -4, -3, 6, 8, 6] }] },
      { id: 'l0', pivot: [-2, 19, 1], boxes: [{ origin: [26, 0], box: [-1, 0, -3, 3, 5, 3] }] },
      { id: 'l1', pivot: [1, 19, 1], boxes: [{ origin: [26, 0], box: [-1, 0, -3, 3, 5, 3] }] },
      { id: 'w0', pivot: [-4, 13, 0], boxes: [{ origin: [24, 13], box: [0, 0, -3, 1, 4, 6] }] },
      { id: 'w1', pivot: [4, 13, 0], boxes: [{ origin: [24, 13], box: [-1, 0, -3, 1, 4, 6] }] },
    ],
  },
  sheep: {
    tex: [64, 32], shadow: 0.6,
    parts: [
      { id: 'head', pivot: [0, 6, -8], boxes: [{ origin: [0, 0], box: [-3, -4, -6, 6, 6, 8] }, { tex: 'mob_sheep_fur', origin: [0, 0], box: [-3, -4, -4, 6, 6, 6], inflate: 1.2 }] },
      { id: 'body', pivot: [0, 5, 2], rot: [Math.PI / 2, 0, 0], boxes: [{ origin: [28, 8], box: [-4, -10, -7, 8, 16, 6] }, { tex: 'mob_sheep_fur', origin: [28, 8], box: [-4, -10, -7, 8, 16, 6], inflate: 3.5 }] },
      ...(
        [['l0', -3, 7], ['l1', 3, 7], ['l2', -3, -5], ['l3', 3, -5]] as [string, number, number][]
      ).map(([id, x, z]): PartDef => ({ id, pivot: [x, 12, z], boxes: [{ origin: [0, 16], box: [-2, 0, -2, 4, 12, 4] }, { tex: 'mob_sheep_fur', origin: [0, 16], box: [-2, 0, -2, 4, 6, 4], inflate: 1.0 }] })),
    ],
  },
  villager: {
    tex: [64, 64], shadow: 0.45,
    parts: [
      { id: 'head', pivot: [0, 0, 0], boxes: [{ origin: [0, 0], box: [-4, -10, -4, 8, 10, 8] }, { origin: [32, 0], box: [-4, -10, -4, 8, 10, 8], inflate: 0.5 }, { origin: [24, 0], box: [-1, -3, -6, 2, 4, 2] }] },
      { id: 'body', pivot: [0, 0, 0], boxes: [{ origin: [16, 20], box: [-4, 0, -3, 8, 12, 6] }, { origin: [0, 38], box: [-4, 0, -3, 8, 18, 6], inflate: 1.0 }] },
      { id: 'arms', pivot: [0, 3, -1], rot: [-0.75, 0, 0], boxes: [{ origin: [44, 22], box: [-8, -2, -2, 4, 8, 4] }, { origin: [44, 22], box: [4, -2, -2, 4, 8, 4], mirror: true }, { origin: [40, 38], box: [-4, 2, -2, 8, 4, 4] }] },
      { id: 'l0', pivot: [-2, 12, 0], boxes: [{ origin: [0, 22], box: [-2, 0, -2, 4, 12, 4] }] },
      { id: 'l1', pivot: [2, 12, 0], boxes: [{ origin: [0, 22], box: [-2, 0, -2, 4, 12, 4], mirror: true }] },
    ],
  },
  spider: {
    tex: [64, 32], shadow: 0.7,
    parts: [
      { id: 'head', pivot: [0, 15, -3], boxes: [{ origin: [32, 4], box: [-4, -4, -8, 8, 8, 8] }] },
      { id: 'neck', pivot: [0, 15, 0], boxes: [{ origin: [0, 0], box: [-3, -3, -3, 6, 6, 6] }] },
      { id: 'body', pivot: [0, 15, 9], boxes: [{ origin: [0, 12], box: [-5, -4, -6, 10, 8, 12] }] },
      ...(
        [
          [-4, 2, Math.PI / 4, -Math.PI / 4], [4, 2, -Math.PI / 4, Math.PI / 4],
          [-4, 1, Math.PI / 8, -0.58119464], [4, 1, -Math.PI / 8, 0.58119464],
          [-4, 0, -Math.PI / 8, -0.58119464], [4, 0, Math.PI / 8, 0.58119464],
          [-4, -1, -Math.PI / 4, -Math.PI / 4], [4, -1, Math.PI / 4, Math.PI / 4],
        ] as [number, number, number, number][]
      ).map(([x, z, ry, rz], k): PartDef => ({
        id: `l${k}`, pivot: [x, 15, z], rot: [0, ry, rz],
        boxes: [{ origin: [18, 0], box: x < 0 ? [-15, -1, -1, 16, 2, 2] : [-1, -1, -1, 16, 2, 2], mirror: x > 0 }],
      })),
    ],
  },
  cave_spider: { tex: [64, 32], shadow: 0.5, scale: 0.7, texName: 'mob_cave_spider', parts: [] },
  creeper: {
    tex: [64, 32], shadow: 0.5,
    parts: [
      { id: 'head', pivot: [0, 6, 0], boxes: [{ origin: [0, 0], box: [-4, -8, -4, 8, 8, 8] }] },
      { id: 'body', pivot: [0, 6, 0], boxes: [{ origin: [16, 16], box: [-4, 0, -2, 8, 12, 4] }] },
      ...(
        [['l0', -2, 4], ['l1', 2, 4], ['l2', -2, -4], ['l3', 2, -4]] as [string, number, number][]
      ).map(([id, x, z]): PartDef => ({ id, pivot: [x, 18, z], boxes: [{ origin: [0, 16], box: [-2, 0, -2, 4, 6, 4] }] })),
    ],
  },
};

export const Mob: React.FC<{ track: Track; f: number; kind: MobKind; skin?: string; swell?: number; warm?: number }> = ({ track, f, kind, skin, swell = 0, warm = 0 }) => {
  const def = kind === 'cave_spider' ? { ...MOBS.spider, scale: 0.7, texName: 'mob_cave_spider' } : MOBS[kind];
  const pose: MobPose =
    kind === 'chicken' ? chickenPose(track, f) : kind === 'villager' ? villagerPose(track, f) : kind === 'spider' || kind === 'cave_spider' ? spiderPose(track, f) : quadrupedPose(track, f, kind);
  const i = track.at(f);
  const U1 = KINDS[kind === 'cave_spider' ? 'spider' : kind].unit; // villagers render at 0.9375, other mobs at 1 px = 1/16 block
  const tint = track.hurt(f) > 0.05 ? HURT_TINT : warmTint(warm);
  const tex = skin ?? def.texName ?? `mob_${kind}`;
  const angle = (id: string): Rot => {
    if (id === 'head') return pose.head;
    const n = Number(id.slice(1));
    if (id[0] === 'l') return pose.legs[n] ?? [0, 0, 0];
    if (id[0] === 'w') return pose.wings[n] ?? [0, 0, 0];
    return [0, 0, 0];
  };
  const s = (def.scale ?? 1) * (1 + swell * 0.18 * Math.sin(swell * Math.PI)); // creeper inflating before it blows
  return (
    <group position={[track.x[i], track.y[i], track.z[i]]} rotation={[0, track.face[i], 0]} scale={[s, (def.scale ?? 1) + (s - (def.scale ?? 1)) * 0.6, s]}>
      <Shadow r={def.shadow} track={track} f={f} />
      <group position={[0, pose.bob * U1, 0]}>
        {def.parts.map((p) => {
          const a = angle(p.id);
          const r: Rot = [(p.rot?.[0] ?? 0) + a[0], (p.rot?.[1] ?? 0) + a[1], (p.rot?.[2] ?? 0) + a[2]];
          return (
            <group key={p.id} position={[p.pivot[0] * U1, (24 - p.pivot[1]) * U1, (-p.pivot[2] + (p.id === 'head' ? -pose.headZ : 0)) * U1]} rotation={e3(r)}>
              {p.boxes.map((b, k) => {
                const [x, y, z, w, h, d] = b.box;
                return <TexBox key={k} name={b.tex ?? tex} origin={b.origin} size={[w, h, d]} texSize={def.tex} unit={U1} mirror={b.mirror} inflate={b.inflate} tint={tint} position={[(x + w / 2) * U1, -(y + h / 2) * U1, -(z + d / 2) * U1]} />;
              })}
            </group>
          );
        })}
      </group>
    </group>
  );
};
