/**
 * Minecraft video kit — props: chest (vanilla lid animation), signs (fixed in the world), ore veins that crack and break,
 * break particles and dropped items flying to the player.
 */
import React, { useContext, useMemo } from 'react';
import * as THREE from 'three';
import type { Act, Track } from './choreo';
import { AssetsCtx, PIXEL, Sprite3D, TexBox, faceLight, getTex, rnd, useShadedMats } from './core';

/* ------------------------------ specs ------------------------------ */
export interface SignSpec { type: 'sign'; at: [number, number]; lines: string[]; rotY?: number }
export interface ChestSpec { type: 'chest'; at: [number, number]; rotY?: number; openAt: number; closeAt: number } // at = block centre (x, z)
export type Ore = 'coal' | 'iron' | 'gold' | 'redstone' | 'lapis' | 'diamond';
export interface VeinSpec {
  type: 'vein';
  actor: string; // actor id that mines it
  act: number; // index of the actor's mine act
  x: number; // block x of the wall face
  cells: [number, number][]; // [y, z] of each block, broken in this order (one per swing)
  ores: Ore[];
}
export interface LadderSpec { type: 'ladder'; at: [number, number]; height: number; rotY?: number } // wall column centred at `at`, ladder on its +z face (rotY turns it)
export interface DoorSpec { type: 'door'; at: [number, number]; rotY?: number; openAt: number; closeAt: number; swing?: 1 | -1; frame?: boolean } // door in a 3-wide planks wall; at = centre of the doorway
export type PropSpec = SignSpec | ChestSpec | VeinSpec | LadderSpec | DoorSpec;

export const ORE_TILE: Record<Ore, string> = { coal: 'coal_ore', iron: 'iron_ore', gold: 'gold_ore', redstone: 'redstone_ore', lapis: 'lapis_ore', diamond: 'diamond_ore' };
export const ORE_ITEM: Record<Ore, string> = { coal: 'item_coal', iron: 'item_raw_iron', gold: 'item_gold_ingot', redstone: 'item_redstone', lapis: 'item_lapis_lazuli', diamond: 'item_diamond' };
const ORE_CHIP: Record<Ore, string> = { coal: '#222', iron: '#d9b79f', gold: '#fbe94b', redstone: '#e01616', lapis: '#2f55c9', diamond: '#5fe8f0' };

/** Frame when block k of a vein breaks = end of swing k of the mining act. */
export const veinBreaks = (v: VeinSpec, tracks: Record<string, Track>): { act: Act; breaks: number[] } | null => {
  const T = tracks[v.actor];
  const act = T?.acts.filter((a) => a.kind === 'mine')[v.act];
  if (!act) return null;
  return { act, breaks: T.breaks(act).slice(0, v.cells.length) };
};

export const chestOpenAmount = (f: number, c: ChestSpec) => {
  const o = f < c.openAt ? 0 : f < c.openAt + 15 ? (f - c.openAt) / 15 : f < c.closeAt ? 1 : f < c.closeAt + 15 ? 1 - (f - c.closeAt) / 15 : 0; // 10 ticks each way
  return 1 - Math.pow(1 - o, 3);
};

/* ------------------------------ chest ------------------------------ */
export const Chest: React.FC<{ f: number; spec: ChestSpec }> = ({ f, spec }) => {
  const q = 1 / 16;
  const e = chestOpenAmount(f, spec);
  const lid = -(e * (Math.PI / 2) * (1 + 0.035 * Math.sin(e * Math.PI))); // vanilla angle with a tiny settle
  const bx = { unit: q, texSize: [64, 64] as [number, number], swapVert: true };
  return (
    <group position={[spec.at[0], 0, spec.at[1]]} rotation={[0, spec.rotY ?? 0, 0]}>
      <TexBox name="chest" size={[14, 10, 14]} origin={[0, 19]} position={[0, 5 * q, 0]} {...bx} />
      <group position={[0, 10 * q, -7 * q]} rotation={[lid, 0, 0]}>
        <TexBox name="chest" size={[14, 5, 14]} origin={[0, 0]} position={[0, 2.5 * q, 7 * q]} {...bx} />
        <TexBox name="chest" size={[2, 4, 1]} origin={[0, 0]} position={[0, -1 * q, 14.5 * q]} {...bx} />
      </group>
    </group>
  );
};

/* ------------------------------ sign ------------------------------ */
export const SignPost: React.FC<{ spec: SignSpec }> = ({ spec }) => {
  const q = 1 / 16;
  const text = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = 96;
    c.height = 48;
    const g = c.getContext('2d')!;
    g.fillStyle = '#000';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.font = `6px ${PIXEL}`;
    g.imageSmoothingEnabled = false;
    spec.lines.forEach((l, i) => g.fillText(l, 48, 8 + i * 10));
    const t = new THREE.CanvasTexture(c);
    t.magFilter = THREE.NearestFilter;
    t.minFilter = THREE.NearestFilter;
    t.generateMipmaps = false;
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }, [spec.lines]);
  return (
    <group position={[spec.at[0], 0, spec.at[1]]} rotation={[0, spec.rotY ?? 0, 0]}>
      <TexBox name="sign" size={[2, 14, 2]} origin={[0, 14]} texSize={[64, 32]} position={[0, 7 * q, 0]} />
      <TexBox name="sign" size={[24, 12, 2]} origin={[0, 0]} texSize={[64, 32]} position={[0, 20 * q, 0]} />
      <mesh position={[0, 20 * q, 1.08 * q]}>
        <planeGeometry args={[22 * q, 11 * q]} />
        <meshBasicMaterial map={text} transparent depthWrite={false} />
      </mesh>
    </group>
  );
};

/* ------------------------------ ore block with crack animation ------------------------------ */
export const OreBlock: React.FC<{ tile: string; p: [number, number, number]; stage?: number }> = ({ tile, p, stage = -1 }) => {
  const A = useContext(AssetsCtx);
  const tex = getTex(tile, A[tile]);
  const mats = useShadedMats(tex);
  const crack = stage >= 0 ? getTex(`destroy_${stage}`, A[`destroy_${stage}`]) : null;
  return (
    <group position={[p[0] + 0.5, p[1] + 0.5, p[2] + 0.5]}>
      <mesh material={mats} castShadow>
        <boxGeometry args={[1, 1, 1]} />
      </mesh>
      {crack && (
        <mesh>
          <boxGeometry args={[1.004, 1.004, 1.004]} />
          <meshBasicMaterial map={crack} transparent depthWrite={false} polygonOffset polygonOffsetFactor={-2} />
        </mesh>
      )}
    </group>
  );
};

const chipGeo = new THREE.BoxGeometry(0.1, 0.1, 0.1); // shared by every particle
export const Burst: React.FC<{ p: [number, number, number]; age: number; color: string; seed: number }> = ({ p, age, color, seed }) => {
  if (age < 0 || age > 16) return null;
  const t = age / 30;
  return (
    <>
      {Array.from({ length: 10 }).map((_, i) => {
        const vx = (rnd(seed + i * 1.7) - 0.5) * 2.4;
        const vy = rnd(seed + i * 3.1) * 2.2 + 0.6;
        const vz = (rnd(seed + i * 5.3) - 0.5) * 2.4;
        return (
          <mesh key={i} geometry={chipGeo} position={[p[0] + vx * t, p[1] + vy * t - 4.5 * t * t, p[2] + vz * t]}>
            <meshBasicMaterial color={i % 3 === 0 ? '#777' : color} />
          </mesh>
        );
      })}
    </>
  );
};

/** Blocks crack while the actor swings, break at the end of each swing, spawn particles and a drop that flies to the actor. */
export const Vein: React.FC<{ f: number; spec: VeinSpec; tracks: Record<string, Track>; index: number }> = ({ f, spec, tracks, index }) => {
  const info = veinBreaks(spec, tracks);
  if (!info) return null;
  const T = tracks[spec.actor];
  const [px0, pz0] = T.pos(f);
  const nodes: React.ReactNode[] = [];
  spec.cells.forEach(([y, z], k) => {
    const bf = info.breaks[k];
    if (bf === undefined) {
      nodes.push(<OreBlock key={`b${k}`} tile={ORE_TILE[spec.ores[k]]} p={[spec.x, y, z]} />);
      return;
    }
    const ore = spec.ores[k];
    const c: [number, number, number] = [spec.x + 0.5, y + 0.5, z + 0.5];
    const dur = info.act.cycle;
    const stage = f >= bf - dur && f < bf ? Math.min(9, Math.floor(((f - (bf - dur)) / dur) * 10)) : -1;
    if (f < bf) nodes.push(<OreBlock key={`b${k}`} tile={ORE_TILE[ore]} p={[spec.x, y, z]} stage={stage} />);
    const age = f - bf;
    nodes.push(<Burst key={`p${k}`} p={c} age={age} color={ORE_CHIP[ore]} seed={k * 11 + spec.x * 3 + index * 17} />);
    if (age >= 0 && age <= 28) {
      const hang = age < 16;
      const kk = hang ? 0 : (age - 16) / 12;
      nodes.push(
        <Sprite3D
          key={`i${k}`}
          name={ORE_ITEM[ore]}
          scale={0.34}
          position={[hang ? c[0] : c[0] + (px0 - c[0]) * kk, (hang ? 0.35 + Math.sin(age * 0.5) * 0.06 : 0.35 + 0.5 * kk) + (y >= 1 ? 0.5 * (1 - kk) : 0), hang ? c[2] : c[2] + (pz0 - c[2]) * kk]}
          rotation={[0, f * 0.09, 0]}
        />,
      );
    }
  });
  return <>{nodes}</>;
};

/* ------------------------------ ladder ------------------------------ */
export const Ladder: React.FC<{ spec: LadderSpec }> = ({ spec }) => {
  const A = useContext(AssetsCtx);
  const tex = getTex('ladder', A.ladder);
  const color = useMemo(() => new THREE.Color(...faceLight('pz')), []);
  return (
    <group position={[spec.at[0], 0, spec.at[1]]} rotation={[0, spec.rotY ?? 0, 0]}>
      {Array.from({ length: spec.height }).map((_, y) => (
        <React.Fragment key={y}>
          <OreBlock tile="oak_planks" p={[-0.5, y, -0.5]} />
          <mesh position={[0, y + 0.5, 0.5 + 0.015]}>
            <planeGeometry args={[1, 1]} />
            <meshBasicMaterial map={tex} color={color} alphaTest={0.5} side={THREE.DoubleSide} />
          </mesh>
        </React.Fragment>
      ))}
    </group>
  );
};

/* ------------------------------ door ------------------------------ */
export const doorOpenAmount = (f: number, d: DoorSpec) => {
  const o = f < d.openAt ? 0 : f < d.openAt + 12 ? (f - d.openAt) / 12 : f < d.closeAt ? 1 : f < d.closeAt + 10 ? 1 - (f - d.closeAt) / 10 : 0;
  return o * o * (3 - 2 * o);
};
const DoorSlab: React.FC<{ tex: string; y: number }> = ({ tex, y }) => {
  const A = useContext(AssetsCtx);
  const mats = useShadedMats(getTex(tex, A[tex]), 0.5);
  return (
    <mesh material={mats} position={[0.5, y + 0.5, 0]} castShadow>
      <boxGeometry args={[1, 1, 3 / 16]} />
    </mesh>
  );
};
export const Door: React.FC<{ f: number; spec: DoorSpec }> = ({ f, spec }) => {
  const ang = doorOpenAmount(f, spec) * (Math.PI / 2) * (spec.swing ?? 1);
  return (
    <group position={[spec.at[0], 0, spec.at[1]]} rotation={[0, spec.rotY ?? 0, 0]}>
      {spec.frame !== false &&
        [-1, 1].flatMap((dx) => [0, 1, 2].map((y) => <OreBlock key={`${dx}${y}`} tile="oak_planks" p={[dx - 0.5, y, -0.5]} />))}
      {spec.frame !== false && <OreBlock tile="oak_planks" p={[-0.5, 2, -0.5]} />}
      <group position={[-0.5, 0, 0]} rotation={[0, ang, 0]}>
        <DoorSlab tex="door_oak_lower" y={0} />
        <DoorSlab tex="door_oak_upper" y={1} />
      </group>
    </group>
  );
};
