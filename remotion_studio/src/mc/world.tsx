/**
 * Minecraft video kit — world: merged voxel terrain (atlas + per-vertex AO and sun shadows), trees, plants, clouds, sun shadow catcher.
 */
import React, { useContext, useEffect, useMemo } from 'react';
import * as THREE from 'three';
import { AssetsCtx, FACES, SUN, Sprite3D, TimeOfDay, faceLight, getTex, Imgs, rnd } from './core';

export interface WorldSpec {
  flatX: [number, number]; // area kept flat (hills grow outside it)
  flatZ: [number, number];
  paths: { z: number; x: [number, number] }[]; // dirt paths along x, with a little natural wobble
  trees: [number, number, number][]; // x, z, trunk height
  noPlants: [number, number, number, number][]; // boxes (x0, z0, x1, z1) kept free of grass and flowers
  plantArea: [number, number, number, number]; // x0, z0, x1, z1
  sunTarget: [number, number]; // x, z the shadow camera is centred on
  sunSpan?: number; // half width covered by the shadow map (blocks)
  time?: TimeOfDay; // day (default), dusk, night
  torches?: [number, number, number][]; // x, y, z: warm light baked into the terrain around them, with a flickering glow
  ponds?: [number, number, number, number, number][]; // x0, z0, x1, z1 (blocks) and depth: carved into the terrain and filled with water
}

/* ---- world atlas (4x4 tiles of 16 px) ---- */
const TILES = ['grass_top', 'grass_side', 'dirt', 'stone', 'dirt_path_top', 'dirt_path_side', 'oak_planks', 'oak_log', 'oak_log_top', 'leaves', 'coal_ore', 'iron_ore', 'gold_ore', 'redstone_ore', 'lapis_ore', 'diamond_ore'];
const tileIndex = (n: string) => TILES.indexOf(n);
type BlockDef = { top: string; side: string; bottom: string };
const BLOCKS: Record<string, BlockDef> = {
  grass: { top: 'grass_top', side: 'grass_side', bottom: 'dirt' },
  dirt: { top: 'dirt', side: 'dirt', bottom: 'dirt' },
  stone: { top: 'stone', side: 'stone', bottom: 'stone' },
  path: { top: 'dirt_path_top', side: 'dirt_path_side', bottom: 'dirt' },
  log: { top: 'oak_log_top', side: 'oak_log', bottom: 'oak_log_top' },
  leaves: { top: 'leaves', side: 'leaves', bottom: 'leaves' },
};

let atlasTex: THREE.CanvasTexture | null = null;
const getAtlas = (A: Imgs) => {
  if (atlasTex) return atlasTex;
  const c = document.createElement('canvas');
  c.width = c.height = 64;
  const g = c.getContext('2d')!;
  g.imageSmoothingEnabled = false;
  TILES.forEach((n, i) => {
    if (n === 'leaves') {
      g.fillStyle = '#1f4a10'; // opaque like fast-graphics leaves: holes show dark foliage, never sky
      g.fillRect((i % 4) * 16, Math.floor(i / 4) * 16, 16, 16);
    }
    g.drawImage(A[n], 0, 0, 16, 16, (i % 4) * 16, Math.floor(i / 4) * 16, 16, 16);
  });
  atlasTex = new THREE.CanvasTexture(c);
  atlasTex.magFilter = THREE.NearestFilter;
  atlasTex.minFilter = THREE.NearestFilter;
  atlasTex.generateMipmaps = false;
  atlasTex.colorSpace = THREE.SRGBColorSpace;
  return atlasTex;
};

/** Terrain height (blocks above the walking plane) of column (x, z): flat inside flatX/flatZ, low hills outside. */
export const terrainHeight = (spec: WorldSpec) => {
  const zc = (spec.flatZ[0] + spec.flatZ[1]) / 2, zh = (spec.flatZ[1] - spec.flatZ[0]) / 2;
  return (x: number, z: number) => {
    const rz = Math.max(0, Math.abs(z - zc) - zh);
    const rx = Math.max(0, spec.flatX[0] - x, x - spec.flatX[1]);
    const r = Math.max(rz, rx);
    if (r <= 0) return 0;
    const n = Math.sin(x * 0.35 + 1) * Math.sin(z * 0.3 + 2) * 0.5 + Math.sin(x * 0.13 + z * 0.21) * 0.5;
    return Math.max(0, Math.min(3, Math.round(n * 0.8 + r * 0.45)));
  };
};
/** Bounds of the generated terrain (x0, x1, z0, z1 inclusive). */
export const terrainBounds = (spec: WorldSpec) => [Math.floor(spec.flatX[0]) - 10, Math.ceil(spec.flatX[1]) + 10, Math.floor(spec.flatZ[0]) - 8, Math.ceil(spec.flatZ[1]) + 8];

const blockCache = new WeakMap<WorldSpec, ReturnType<typeof makeBlocks>>();
/** Voxel map of the world, built once per world spec (shared by terrain, plants and collisions). */
export const buildBlocks = (spec: WorldSpec) => {
  let b = blockCache.get(spec);
  if (!b) { b = makeBlocks(spec); blockCache.set(spec, b); }
  return b;
};
const makeBlocks = (spec: WorldSpec) => {
  const m = new Map<string, string>();
  const set = (x: number, y: number, z: number, t: string) => m.set(`${x},${y},${z}`, t);
  const heightAt = terrainHeight(spec);
  const onPath = (x: number, z: number) =>
    spec.paths.some((p) => x >= p.x[0] && x <= p.x[1] && (z === p.z || (z === p.z + 1 && rnd(x * 3.1) > 0.7) || (z === p.z - 1 && rnd(x * 7.3) > 0.8)));
  const [bx0, bx1, bz0, bz1] = terrainBounds(spec);
  for (let x = bx0; x <= bx1; x++)
    for (let z = bz0; z <= bz1; z++) {
      const h = heightAt(x, z);
      const pond = spec.ponds?.find(([x0, z0, x1, z1]) => x >= x0 && x < x1 && z >= z0 && z < z1);
      for (let y = -4; y < h; y++) {
        if (pond && y >= -pond[4]) continue; // carved out: water goes here
        const top = y === h - 1;
        let t = top ? 'grass' : y >= h - 3 ? 'dirt' : 'stone';
        if (top && h === 0 && onPath(x, z)) t = 'path';
        set(x, y, z, t);
      }
    }
  const tree = (tx: number, tz: number, H: number) => {
    const base = heightAt(tx, tz);
    for (let i = 0; i < H; i++) set(tx, base + i, tz, 'log');
    const T = base + H - 1;
    for (let dy = -1; dy <= 0; dy++)
      for (let dx = -2; dx <= 2; dx++)
        for (let dz = -2; dz <= 2; dz++) {
          if (dx === 0 && dz === 0) continue;
          if (Math.abs(dx) === 2 && Math.abs(dz) === 2 && rnd(tx * 9 + dx * 5 + dz * 3 + dy) > 0.5) continue;
          set(tx + dx, T + dy, tz + dz, 'leaves');
        }
    for (let dx = -1; dx <= 1; dx++) for (let dz = -1; dz <= 1; dz++) set(tx + dx, T + 1, tz + dz, 'leaves');
    for (const [dx, dz] of [[0, 0], [1, 0], [-1, 0], [0, 1], [0, -1]]) set(tx + dx, T + 2, tz + dz, 'leaves');
  };
  spec.trees.forEach(([x, z, H]) => tree(x, z, H));
  return { blocks: m, onPath, heightAt };
};

const buildWorldGeometry = (blocks: Map<string, string>, torches: [number, number, number][] = []) => {
  const pos: number[] = [];
  const uv: number[] = [];
  const col: number[] = [];
  const idx: number[] = [];
  const get = (x: number, y: number, z: number) => blocks.get(`${x},${y},${z}`);
  const E = 0.5 / 64;
  blocks.forEach((type, k) => {
    const [x, y, z] = k.split(',').map(Number);
    const def = BLOCKS[type];
    for (const f of FACES) {
      const nb = get(x + f.d[0], y + f.d[1], z + f.d[2]);
      if (nb && nb !== 'leaves') continue;
      if (nb === 'leaves' && (type === 'leaves' || type === 'log')) continue;
      const tile = f.n === 'py' ? def.top : f.n === 'ny' ? def.bottom : def.side;
      const ti = tileIndex(tile);
      const u0 = (ti % 4) / 4 + E;
      const u1 = (ti % 4) / 4 + 0.25 - E;
      const v1 = 1 - Math.floor(ti / 4) / 4 - E;
      const v0 = 1 - Math.floor(ti / 4) / 4 - 0.25 + E;
      const base = pos.length / 3;
      const ax = f.d[0] !== 0 ? 0 : f.d[1] !== 0 ? 1 : 2;
      const [t1, t2] = [0, 1, 2].filter((a) => a !== ax);
      f.c.forEach((c, i) => {
        // vertex ambient occlusion (smooth lighting)
        const d1 = c[t1] ? 1 : -1;
        const d2 = c[t2] ? 1 : -1;
        const at = (a: number, b: number) => {
          const o = [x + f.d[0], y + f.d[1], z + f.d[2]];
          o[t1] += a * d1;
          o[t2] += b * d2;
          return get(o[0], o[1], o[2]) ? 1 : 0;
        };
        const s1 = at(1, 0), s2 = at(0, 1), cr = at(1, 1);
        const ao = s1 && s2 ? 0 : 3 - (s1 + s2 + cr);
        // sun shadow: march from the vertex towards the sun
        let lit = 1;
        const vx = x + c[0] + f.d[0] * 0.02, vy = y + c[1] + f.d[1] * 0.02, vz = z + c[2] + f.d[2] * 0.02;
        for (let kk = 1; kk <= 22; kk++) {
          if (get(Math.floor(vx + SUN[0] * kk * 0.5), Math.floor(vy + SUN[1] * kk * 0.5), Math.floor(vz + SUN[2] * kk * 0.5))) {
            lit = 0;
            break;
          }
        }
        const L = faceLight(f.n, [0.5, 0.68, 0.84, 1][ao], lit);
        torches.forEach(([tx, ty, tz]) => { // warm torch light, brighter on faces that look at the torch
          const dx = tx - vx, dy = ty - vy, dz = tz - vz, dd = Math.hypot(dx, dy, dz);
          if (dd > 4) return;
          const facing = Math.max(0.25, (f.d[0] * dx + f.d[1] * dy + f.d[2] * dz) / (dd || 1) + 0.35);
          const k = Math.pow(1 - dd / 4, 2) * 0.5 * Math.min(1.2, facing) * [0.6, 0.78, 0.9, 1][ao];
          L[0] += 1.0 * k; L[1] += 0.6 * k; L[2] += 0.25 * k;
        });
        pos.push(x + c[0], y + c[1], z + c[2]);
        col.push(L[0], L[1], L[2]);
        uv.push(i === 0 || i === 3 ? u0 : u1, i < 2 ? v0 : v1);
      });
      idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
    }
  });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  g.setIndex(idx);
  return g;
};

export const World: React.FC<{ spec: WorldSpec }> = ({ spec }) => {
  const A = useContext(AssetsCtx);
  const geo = useMemo(() => buildWorldGeometry(buildBlocks(spec).blocks, spec.torches), [spec]);
  useEffect(() => () => geo.dispose(), [geo]);
  return (
    <mesh geometry={geo}>
      <meshBasicMaterial map={getAtlas(A)} vertexColors alphaTest={0.5} />
    </mesh>
  );
};

/* ---- clouds (vanilla clouds.png, 12-block cells) ---- */
export const Clouds: React.FC<{ f: number }> = ({ f }) => {
  const A = useContext(AssetsCtx);
  const geo = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = c.height = 256;
    const g = c.getContext('2d')!;
    g.drawImage(A.clouds, 0, 0);
    const d = g.getImageData(0, 0, 256, 256).data;
    const has = (i: number, j: number) => d[(((j + 256) % 256) * 256 + ((i + 256) % 256)) * 4 + 3] > 40;
    const pos: number[] = [], col: number[] = [], idx: number[] = [];
    const CS = 12, H = 4;
    for (let i = -4; i < 20; i++)
      for (let j = -12; j < 0; j++) {
        if (!has(i, j)) continue;
        for (const fc of FACES) {
          const ni = i + (fc.d[0] as number), nj = j + (fc.d[2] as number);
          if ((fc.d[0] || fc.d[2]) && has(ni, nj)) continue;
          const sh = fc.n === 'py' ? 1 : fc.n === 'ny' ? 0.72 : fc.n === 'pz' || fc.n === 'nz' ? 0.88 : 0.82;
          const base = pos.length / 3;
          fc.c.forEach((v) => {
            pos.push((i + v[0]) * CS, v[1] * H, (j + v[2]) * CS);
            col.push(sh, sh, sh);
          });
          idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
        }
      }
    const g2 = new THREE.BufferGeometry();
    g2.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g2.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
    g2.setIndex(idx);
    return g2;
  }, [A]);
  return (
    <mesh geometry={geo} position={[f * 0.03, 11, -6]}>
      <meshBasicMaterial vertexColors transparent opacity={0.85} fog={false} depthWrite={false} />
    </mesh>
  );
};

/* ---- grass tufts and flowers ---- */
const PLANTS = ['plant_grass', 'plant_poppy', 'plant_dandelion', 'plant_azure_bluet', 'plant_oxeye_daisy'];
/** `avoid`: points (x, z) the camera passes through — no plant within 1.4 blocks, so nothing grows into the lens. */
export const Plants: React.FC<{ spec: WorldSpec; avoid?: [number, number][] }> = ({ spec, avoid = [] }) => {
  const A = useContext(AssetsCtx);
  const geos = useMemo(() => {
    const { onPath } = buildBlocks(spec);
    const out: Record<string, { pos: number[]; uv: number[]; idx: number[]; col: number[] }> = {};
    PLANTS.forEach((n) => (out[n] = { pos: [], uv: [], idx: [], col: [] }));
    const [x0, z0, x1, z1] = spec.plantArea;
    for (let x = x0; x <= x1; x++)
      for (let z = z0; z <= z1; z++) {
        const r = rnd(x * 12.7 + z * 78.3);
        if (avoid.some(([ax, az]) => Math.hypot(ax - x - 0.5, az - z - 0.5) < 1.4) || onPath(x, z) || spec.ponds?.some(([a, b, c, d]) => x >= a - 1 && x < c + 1 && z >= b - 1 && z < d + 1) || spec.noPlants.some(([a, b, c, d]) => x >= a && x <= c && z >= b && z <= d)) continue;
        let n: string | null = null;
        if (r < 0.2) n = 'plant_grass';
        else if (r < 0.235) n = 'plant_poppy';
        else if (r < 0.265) n = 'plant_dandelion';
        else if (r < 0.28) n = 'plant_azure_bluet';
        else if (r < 0.295) n = 'plant_oxeye_daisy';
        if (!n) continue;
        const g = out[n];
        const ox = x + 0.5 + (rnd(x * 5 + z) - 0.5) * 0.4, oz = z + 0.5 + (rnd(z * 9 + x) - 0.5) * 0.4;
        const hh = n === 'plant_grass' ? 0.95 : 0.8;
        const w = 0.45;
        [[-w, -w, w, w], [-w, w, w, -w]].forEach(([ax, az, bx, bz]) => {
          const base = g.pos.length / 3;
          g.pos.push(ox + ax, 0, oz + az, ox + bx, 0, oz + bz, ox + bx, hh, oz + bz, ox + ax, hh, oz + az);
          g.uv.push(0, 0, 1, 0, 1, 1, 0, 1);
          for (let k = 0; k < 4; k++) g.col.push(0.95, 0.95, 0.95);
          g.idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
        });
      }
    return out;
  }, [spec, avoid]);
  const geometries = useMemo(
    () =>
      PLANTS.map((n) => {
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.Float32BufferAttribute(geos[n].pos, 3));
        g.setAttribute('uv', new THREE.Float32BufferAttribute(geos[n].uv, 2));
        g.setAttribute('color', new THREE.Float32BufferAttribute(geos[n].col, 3));
        g.setIndex(geos[n].idx);
        return g;
      }),
    [geos],
  );
  return (
    <>
      {PLANTS.map((n, i) => (
        <mesh key={n} geometry={geometries[i]}>
          <meshBasicMaterial map={getTex(n, A[n])} alphaTest={0.5} side={THREE.DoubleSide} vertexColors />
        </mesh>
      ))}
    </>
  );
};

/* ---- real sun shadows of entities and props onto the ground ---- */
export const SunShadow: React.FC<{ spec: WorldSpec }> = ({ spec }) => {
  const [tx, tz] = spec.sunTarget;
  const span = spec.sunSpan ?? 26;
  return (
    <>
      <directionalLight
        position={[tx + SUN[0] * 40, SUN[1] * 40, tz + SUN[2] * 40]}
        target-position={[tx, 0, tz]}
        intensity={0}
        castShadow
        shadow-mapSize={[2048, 2048]}
        shadow-camera-left={-span}
        shadow-camera-right={span}
        shadow-camera-top={10}
        shadow-camera-bottom={-10}
        shadow-camera-near={1}
        shadow-camera-far={120}
        shadow-radius={9}
        shadow-bias={-0.0004}
      />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[tx, 0.02, tz]} receiveShadow>
        <planeGeometry args={[span * 2 + 8, 14]} />
        <shadowMaterial color="#0a1424" opacity={0.5} depthWrite={false} /> {/* must not write depth: it would hide the water below it */}
      </mesh>
    </>
  );
};

/** Pond surface: vanilla animated water texture (32 frames, 2 ticks each), biome tint, slightly below the block top like the game.
 *  One merged mesh for all ponds (one quad per block so the texture tiles at the block scale). */
export const Water: React.FC<{ spec: WorldSpec; f: number }> = ({ spec, f }) => {
  const A = useContext(AssetsCtx);
  const tex = useMemo(() => {
    const t = getTex('water_still', A.water_still).clone();
    t.repeat.set(1, 1 / 32);
    t.needsUpdate = true;
    return t;
  }, [A]);
  const geo = useMemo(() => {
    const pos: number[] = [], uv: number[] = [], idx: number[] = [];
    (spec.ponds ?? []).forEach(([x0, z0, x1, z1]) => {
      for (let x = Math.ceil(x0); x < x1; x++) // same cells the terrain carves (integer x >= x0 and < x1)
        for (let z = Math.ceil(z0); z < z1; z++) {
          const b = pos.length / 3;
          pos.push(x, -0.11, z + 1, x + 1, -0.11, z + 1, x + 1, -0.11, z, x, -0.11, z);
          uv.push(0, 0, 1, 0, 1, 1, 0, 1);
          idx.push(b, b + 1, b + 2, b, b + 2, b + 3);
        }
    });
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
    g.setIndex(idx);
    return g;
  }, [spec]);
  useEffect(() => () => geo.dispose(), [geo]);
  const frame = Math.floor(((f * 20) / 30 / 2) % 32);
  tex.offset.set(0, 1 - (frame + 1) / 32);
  if (!spec.ponds?.length) return null;
  return (
    <mesh geometry={geo}>
      <meshBasicMaterial map={tex} transparent opacity={0.92} depthWrite={false} side={THREE.DoubleSide} />
    </mesh>
  );
};

/** Torch sprites with a flickering additive glow. */
export const Torches: React.FC<{ spec: WorldSpec; f: number }> = ({ spec, f }) => {
  const glow = useMemo(() => {
    const c = document.createElement('canvas');
    c.width = c.height = 64;
    const g = c.getContext('2d')!;
    const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,190,90,0.95)');
    gr.addColorStop(0.35, 'rgba(255,140,50,0.35)');
    gr.addColorStop(1, 'rgba(255,100,20,0)');
    g.fillStyle = gr;
    g.fillRect(0, 0, 64, 64);
    return new THREE.CanvasTexture(c);
  }, []);
  return (
    <>
      {(spec.torches ?? []).map(([x, y, z], i) => {
        const fl = 1 + Math.sin(f * 0.33 + i * 2.1) * 0.08 + Math.sin(f * 0.71 + i) * 0.05;
        return (
          <React.Fragment key={i}>
            <Sprite3D name="torch" scale={0.8} position={[x, y - 0.15, z]} />
            <sprite position={[x, y + 0.12, z]} scale={[2.0 * fl, 2.0 * fl, 1]}>
              <spriteMaterial map={glow} blending={THREE.AdditiveBlending} depthWrite={false} transparent opacity={0.4} />
            </sprite>
          </React.Fragment>
        );
      })}
    </>
  );
};
