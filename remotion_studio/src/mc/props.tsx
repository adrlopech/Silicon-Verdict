/**
 * Minecraft video kit — props: chest (vanilla lid animation), signs (fixed in the world), ore veins that crack and break,
 * break particles and dropped items flying to the player.
 */
import React, { useContext, useMemo } from 'react';
import * as THREE from 'three';
import type { Act, Track } from './choreo';
import { AssetsCtx, PIXEL, Sprite3D, TexBox, faceLight, getTex, lightKey, rnd, useShadedMats } from './core';

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
export interface StallTag { f: number; now: string; was?: string; icon?: string } // value plaque next to the counter: the old value struck through, the new one below
export interface StallSpec { type: 'stall'; at: [number, number]; items: string[]; rotY?: number; stock?: { f: number; items: string[] }[]; tags?: StallTag[] } // market stall: barrel counter at `at` (2 x 1 blocks), striped awning, items on the counter
export interface HouseSpec { type: 'house'; at: [number, number]; w: number; d: number; h?: number; lit?: boolean } // village house facing +z (the camera); at = footprint centre
export interface LibrarySpec { type: 'library'; at: [number, number]; fill: number; events?: { f: number; delta: number }[] } // 3 x 2 bookshelf cells; `fill` of them hold books at the start (0 = empty library), events add or remove books
export type PropSpec = SignSpec | ChestSpec | VeinSpec | LadderSpec | DoorSpec | StallSpec | HouseSpec | LibrarySpec;

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

/* ------------------------------ market stall (village shop: red/white awning, barrel counter, items for sale) ------------------------------ */
const BRIGHT = [0.85, 0.85, 1.0, 0.55, 0.95, 0.8]; // px nx py ny pz nz: same face shading idea as the rest of the kit
const blockMats = new Map<string, THREE.MeshBasicMaterial[]>();
const blockMat = (A: Record<string, HTMLImageElement>, side: string, top = side) => {
  const key = lightKey() + '|' + side + '|' + top;
  let m = blockMats.get(key);
  if (!m) {
    m = BRIGHT.map((b, i) => {
      const L = faceLight(['px', 'nx', 'py', 'ny', 'pz', 'nz'][i]);
      return new THREE.MeshBasicMaterial({ map: getTex(i === 2 || i === 3 ? top : side, A[i === 2 || i === 3 ? top : side]), color: new THREE.Color(L[0] * 1.05, L[1] * 1.05, L[2] * 1.05) });
    });
    blockMats.set(key, m);
  }
  return m;
};
const Cuboid: React.FC<{ side: string; top?: string; size: [number, number, number]; position: [number, number, number] }> = ({ side, top, size, position }) => {
  const A = useContext(AssetsCtx);
  return <mesh material={blockMat(A, side, top)} position={position} castShadow><boxGeometry args={size} /></mesh>;
};

const ease = (x: number) => 1 - Math.pow(1 - Math.min(1, Math.max(0, x)), 3);

const TagPlaque: React.FC<{ tag: StallTag; age: number }> = ({ tag, age }) => {
  const A = useContext(AssetsCtx);
  const tex = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = 112;
    c.height = 48;
    const g = c.getContext('2d')!;
    g.imageSmoothingEnabled = false;
    g.fillStyle = '#3b2a14';
    g.fillRect(0, 0, 112, 48);
    g.fillStyle = '#a8814a';
    g.fillRect(3, 3, 106, 42);
    g.textBaseline = 'middle';
    g.textAlign = 'center';
    const cx = tag.icon && A[tag.icon] ? 44 : 56;
    if (tag.was) {
      g.font = `9px ${PIXEL}`;
      g.fillStyle = '#b01818';
      g.fillText(tag.was, cx, 15);
      const w = g.measureText(tag.was).width;
      g.fillRect(cx - w / 2 - 2, 14, w + 4, 2);
    }
    g.font = `${tag.was ? 14 : 16}px ${PIXEL}`;
    g.fillStyle = '#143d14';
    g.fillText(tag.now, cx + 1, (tag.was ? 33 : 24) + 1);
    g.fillStyle = '#ffffff';
    g.fillText(tag.now, cx, tag.was ? 33 : 24);
    if (tag.icon && A[tag.icon]) g.drawImage(A[tag.icon], 80, 12, 24, 24);
    const t = new THREE.CanvasTexture(c);
    t.magFilter = THREE.NearestFilter;
    t.minFilter = THREE.NearestFilter;
    t.generateMipmaps = false;
    t.colorSpace = THREE.SRGBColorSpace;
    return t;
  }, [tag, A]);
  const k = age < 10 ? 0.4 + 0.6 * ease(age / 10) + Math.sin(Math.min(1, age / 10) * Math.PI) * 0.12 : 1;
  return (
    <mesh position={[0.78, 1.95, 0.5]} scale={[k, k, 1]} castShadow>
      <planeGeometry args={[0.95, 0.4]} />
      <meshBasicMaterial map={tex} transparent />
    </mesh>
  );
};

export const stallHalfWidth = 1;
export const Stall: React.FC<{ f: number; spec: StallSpec }> = ({ f, spec }) => {
  const stripes = 7;
  const w = 2.9; // awning width
  const stock = [{ f: 0, items: spec.items }, ...(spec.stock ?? [])];
  const si = stock.reduce((k, s, i) => (s.f <= f ? i : k), 0);
  const cur = stock[si];
  const prev = si > 0 ? stock[si - 1].items : [];
  const items = cur.items.slice(0, 6);
  const age = f - cur.f;
  const tags = spec.tags ?? [];
  const tag = [...tags].reverse().find((t) => t.f <= f);
  return (
    <group position={[spec.at[0], 0, spec.at[1]]} rotation={[0, spec.rotY ?? 0, 0]}>
      {[-0.5, 0.5].map((dx) => <Cuboid key={dx} side="barrel_side" top="barrel_top" size={[1, 1, 1]} position={[dx, 0.5, 0]} />)}
      {[-1.3, 1.3].map((dx) => (
        <React.Fragment key={dx}>
          <Cuboid side="oak_log" top="oak_log_top" size={[0.25, 2.2, 0.25]} position={[dx, 1.1, 0.45]} />
          <Cuboid side="oak_log" top="oak_log_top" size={[0.25, 2.6, 0.25]} position={[dx, 1.3, -0.95]} />
        </React.Fragment>
      ))}
      <group position={[0, 2.38, -0.2]} rotation={[0.2, 0, 0]}>
        {Array.from({ length: stripes }).map((_, i) => (
          <Cuboid key={i} side={i % 2 ? 'white_wool' : 'red_wool'} size={[w / stripes, 0.12, 1.9]} position={[-w / 2 + (i + 0.5) * (w / stripes), 0, 0]} />
        ))}
      </group>
      {items.map((it, i, all) => {
        const x = (i - (all.length - 1) / 2) * Math.min(0.55, 1.7 / Math.max(1, all.length - 1));
        const fresh = si > 0 && prev[i] !== it; // new or changed item: pops in with green sparkles
        const k = fresh ? 0.15 + 0.85 * ease(age / 9) + Math.sin(Math.min(1, age / 9) * Math.PI) * 0.25 : 1;
        const pos: [number, number, number] = [x, 1.28 + Math.sin(f * 0.07 + i * 1.7) * 0.025 + (fresh ? (1 - ease(age / 9)) * 0.3 : 0), 0.05];
        return (
          <React.Fragment key={i}>
            <Sprite3D name={it} scale={0.5 * k} position={pos} rotation={[0, Math.sin(f * 0.04 + i) * 0.35, 0]} />
            {fresh && <Burst p={[x, 1.25, 0.05]} age={age - 2} color="#55ff55" seed={si * 13 + i * 7} />}
          </React.Fragment>
        );
      })}
      {tag && <TagPlaque tag={tag} age={f - tag.f} />}
    </group>
  );
};

/* ------------------------------ village house (cobblestone base, planks, log corners, gable roof, door, windows) ------------------------------ */
const repTex = new Map<string, THREE.Texture>();
const getRepTex = (name: string, img: HTMLImageElement) => {
  let t = repTex.get(name);
  if (!t) {
    t = getTex(name, img).clone();
    t.wrapS = t.wrapT = THREE.RepeatWrapping;
    t.magFilter = THREE.NearestFilter;
    t.minFilter = THREE.NearestFilter;
    t.generateMipmaps = false;
    t.colorSpace = THREE.SRGBColorSpace;
    t.needsUpdate = true;
    repTex.set(name, t);
  }
  return t;
};
const repMats = new Map<string, THREE.MeshBasicMaterial[]>();
const repGeos = new Map<string, THREE.BoxGeometry>();
/** Box whose texture repeats once per block (instead of stretching one 16 px tile over the whole wall). */
const RepBox: React.FC<{ tex: string; size: [number, number, number]; position: [number, number, number] }> = ({ tex, size, position }) => {
  const A = useContext(AssetsCtx);
  const mk = lightKey() + '|' + tex;
  let mats = repMats.get(mk);
  if (!mats) {
    mats = ['px', 'nx', 'py', 'ny', 'pz', 'nz'].map((n) => {
      const L = faceLight(n);
      return new THREE.MeshBasicMaterial({ map: getRepTex(tex, A[tex]), color: new THREE.Color(L[0] * 1.05, L[1] * 1.05, L[2] * 1.05) });
    });
    repMats.set(mk, mats);
  }
  const gk = size.join(',');
  let geo = repGeos.get(gk);
  if (!geo) {
    const [w, h, d] = size;
    geo = new THREE.BoxGeometry(w, h, d);
    const uv = geo.getAttribute('uv') as THREE.BufferAttribute;
    const rep: [number, number][] = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
    for (let i = 0; i < 24; i++) uv.setXY(i, uv.getX(i) * rep[Math.floor(i / 4)][0], uv.getY(i) * rep[Math.floor(i / 4)][1]);
    repGeos.set(gk, geo);
  }
  return <mesh geometry={geo} material={mats} position={position} castShadow />;
};

export const House: React.FC<{ spec: HouseSpec }> = ({ spec }) => {
  const A = useContext(AssetsCtx);
  const { w, d } = spec;
  const h = spec.h ?? 3;
  const lit = spec.lit ?? false;
  const zf = d / 2 + 0.05;
  const win = (x: number, key: number) => (
    <group key={key} position={[x, 1.75, zf + 0.01]}>
      <mesh position={[0, 0, -0.005]}><planeGeometry args={[1.0, 0.9]} /><meshBasicMaterial color="#3a2a18" /></mesh>
      <mesh><planeGeometry args={[0.76, 0.66]} /><meshBasicMaterial color={lit ? '#ffcf6a' : '#6f8fae'} /></mesh>
    </group>
  );
  const doorTex = (n: string) => <meshBasicMaterial map={getTex(n, A[n])} transparent alphaTest={0.1} color={(() => { const L = faceLight('pz'); return new THREE.Color(L[0], L[1], L[2]); })()} />;
  return (
    <group position={[spec.at[0], 0, spec.at[1]]}>
      <RepBox tex="cobblestone" size={[w + 0.06, 1, d + 0.06]} position={[0, 0.5, 0]} />
      <RepBox tex="oak_planks" size={[w - 0.04, h - 1, d - 0.04]} position={[0, 1 + (h - 1) / 2, 0]} />
      {[-1, 1].flatMap((sx) => [-1, 1].map((sz) => <RepBox key={`${sx}${sz}`} tex="oak_log" size={[0.34, h - 1, 0.34]} position={[(sx * (w - 0.34)) / 2, 1 + (h - 1) / 2, (sz * (d - 0.34)) / 2]} />))}
      {[0, 1, 2].map((i) => <RepBox key={i} tex="cobblestone" size={[w + 0.7, 0.5, Math.max(0.6, d + 0.7 - i * 1.2)]} position={[0, h + 0.25 + i * 0.5, 0]} />)}
      <mesh position={[0, 0.5, zf + 0.01]}><planeGeometry args={[1, 1]} />{doorTex('door_oak_lower')}</mesh>
      <mesh position={[0, 1.5, zf + 0.01]}><planeGeometry args={[1, 1]} />{doorTex('door_oak_upper')}</mesh>
      {w >= 4.2 ? [-w / 3, w / 3].map((x, i) => win(x, i)) : [win(w / 3.2, 0)]}
    </group>
  );
};

/* ------------------------------ library: wall of bookshelf cells, full (books) or empty (dark compartments) ------------------------------ */
export const libraryCount = (spec: LibrarySpec, f: number) => Math.max(0, Math.min(6, spec.fill + (spec.events ?? []).filter((e) => e.f <= f).reduce((n, e) => n + e.delta, 0)));
export const Library: React.FC<{ f: number; spec: LibrarySpec }> = ({ f, spec }) => {
  const n = libraryCount(spec, f);
  const last = [...(spec.events ?? [])].reverse().find((e) => e.f <= f);
  return (
    <group position={[spec.at[0], 0, spec.at[1]]}>
      {Array.from({ length: 6 }).map((_, i) => {
        const col = i % 3, row = Math.floor(i / 3);
        const full = i < n;
        const justAdded = full && last && last.delta > 0 && i === n - 1 && f - last.f < 10;
        const k = justAdded ? 0.6 + 0.4 * ease((f - last.f) / 10) : 1;
        return (
          <group key={i} position={[(col - 1) * 1, 0.5 + row, 0]} scale={[k, k, k]}>
            <Cuboid side={full ? 'bookshelf' : 'bookshelf_empty'} top="oak_planks" size={[1, 1, 1]} position={[0, 0, 0]} />
          </group>
        );
      })}
    </group>
  );
};
