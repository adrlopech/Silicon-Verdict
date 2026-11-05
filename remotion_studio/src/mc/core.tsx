/**
 * Minecraft video kit — core: asset loading, math helpers, vanilla lighting, textured boxes and item sprites.
 * Textures come from public/mc/ (extracted from the user's own game install, git-ignored).
 */
import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { continueRender, delayRender, interpolate, staticFile } from 'remotion';
import * as THREE from 'three';
import { loadFont } from '@remotion/google-fonts/PressStart2P';

export const { fontFamily: PIXEL } = loadFont();

export type V3 = [number, number, number];
export type Rot = [number, number, number];

/* ---------------- math ---------------- */
export const clamp = { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' } as const;
export const sstep = (x: number) => {
  const t = Math.min(1, Math.max(0, x));
  return t * t * (3 - 2 * t);
};
/** Keyframe interpolation with a smoothstep on every segment (nothing ever starts or stops abruptly). */
export const keyedS = (f: number, fr: number[], v: number[]) => interpolate(f, fr, v, { ...clamp, easing: sstep });
/** Position along a path: almost constant speed with a soft start and stop. */
export const pos01 = (t: number) => {
  const u = Math.min(1, Math.max(0, t));
  return u * 0.5 + sstep(u) * 0.5;
};
export const ramp = (f: number, a: number, b: number, c: number, d: number) => sstep((f - a) / (b - a)) * sstep((d - f) / (d - c));
export const rnd = (n: number) => {
  const s = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return s - Math.floor(s);
};
export const shortestDelta = (from: number, to: number) => {
  let d = (to - from) % (2 * Math.PI);
  if (d > Math.PI) d -= 2 * Math.PI;
  if (d < -Math.PI) d += 2 * Math.PI;
  return d;
};
export const lerpAngle = (a: number, b: number, t: number) => a + shortestDelta(a, b) * t;

/* ---------------- assets ---------------- */
export const BASE_TEXTURES = [
  'grass_top', 'grass_side', 'dirt', 'stone', 'dirt_path_top', 'dirt_path_side', 'oak_planks', 'oak_log', 'oak_log_top', 'leaves',
  'coal_ore', 'iron_ore', 'gold_ore', 'redstone_ore', 'lapis_ore', 'diamond_ore', 'torch', 'chest', 'sign', 'skin', 'widgets',
  'item_diamond_pickaxe', 'item_iron_pickaxe', 'item_iron_sword', 'item_coal', 'item_raw_iron', 'item_gold_ingot',
  'item_redstone', 'item_lapis_lazuli', 'item_diamond', 'item_apple', 'item_stick',
  'clouds', 'icons', 'plant_grass', 'plant_poppy', 'plant_dandelion', 'plant_azure_bluet', 'plant_oxeye_daisy',
  'destroy_0', 'destroy_1', 'destroy_2', 'destroy_3', 'destroy_4', 'destroy_5', 'destroy_6', 'destroy_7', 'destroy_8', 'destroy_9',
  'mob_zombie', 'mob_skeleton', 'mob_creeper', 'mob_pig', 'mob_cow', 'mob_chicken',
  'mob_sheep', 'mob_sheep_fur', 'mob_spider', 'mob_cave_spider', 'mob_villager',
  'ladder', 'water_still', 'door_oak_lower', 'door_oak_upper',
];
export type Imgs = Record<string, HTMLImageElement>;
export type SoundMap = Record<string, string[]>; // game event -> sound files (from sounds.json)
export const AssetsCtx = createContext<Imgs>({});
export const SoundMapCtx = createContext<SoundMap>({});

export const useAssets = (extra: string[] = []): { imgs: Imgs; sounds: SoundMap } | null => {
  const [res, setRes] = useState<{ imgs: Imgs; sounds: SoundMap } | null>(null);
  const [handle] = useState(() => delayRender('minecraft assets'));
  useEffect(() => {
    const names = Array.from(new Set([...BASE_TEXTURES, ...extra]));
    Promise.all([
      Promise.all(
        names.map(
          (n) =>
            new Promise<[string, HTMLImageElement]>((res, rej) => {
              const i = new Image();
              i.onload = () => res([n, i]);
              i.onerror = () => rej(new Error('missing texture public/mc/' + n + '.png (run scripts/extract_minecraft_assets.py)'));
              i.src = staticFile(`mc/${n}.png`);
            }),
        ),
      ),
      fetch(staticFile('mc/sound_events.json')).then((r) => r.json()) as Promise<SoundMap>,
      document.fonts.load(`16px ${PIXEL}`),
    ]).then(([imgList, sounds]) => {
      setRes({ imgs: Object.fromEntries(imgList), sounds });
      continueRender(handle);
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [handle]);
  return res;
};

const texCache = new Map<string, THREE.Texture>();
export const getTex = (name: string, img: HTMLImageElement): THREE.Texture => {
  let t = texCache.get(name);
  if (!t) {
    t = new THREE.Texture(img);
    t.magFilter = THREE.NearestFilter;
    t.minFilter = THREE.NearestFilter;
    t.generateMipmaps = false;
    t.colorSpace = THREE.SRGBColorSpace;
    t.needsUpdate = true;
    texCache.set(name, t);
  }
  return t;
};

/* ---------------- faces + lighting (projectLUMA colour model) ---------------- */
export const FACES = [
  { n: 'px', d: [1, 0, 0], c: [[1, 0, 1], [1, 0, 0], [1, 1, 0], [1, 1, 1]] },
  { n: 'nx', d: [-1, 0, 0], c: [[0, 0, 0], [0, 0, 1], [0, 1, 1], [0, 1, 0]] },
  { n: 'py', d: [0, 1, 0], c: [[0, 1, 1], [1, 1, 1], [1, 1, 0], [0, 1, 0]] },
  { n: 'ny', d: [0, -1, 0], c: [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]] },
  { n: 'pz', d: [0, 0, 1], c: [[0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]] },
  { n: 'nz', d: [0, 0, -1], c: [[1, 0, 0], [0, 0, 0], [0, 1, 0], [1, 1, 0]] },
] as const;
export const FACE_ORDER = ['px', 'nx', 'py', 'ny', 'pz', 'nz'] as const;
export const SUN = (() => {
  const v = [0.55, 1, 0.3];
  const l = Math.hypot(...v);
  return v.map((a) => a / l);
})();
const AMBIENT = [0.6, 0.75, 1.0];
const SUN_COLOR = [1.0, 0.9, 0.8];
const FACE_N: Record<string, number[]> = { px: [1, 0, 0], nx: [-1, 0, 0], py: [0, 1, 0], ny: [0, -1, 0], pz: [0, 0, 1], nz: [0, 0, -1] };
/** Cool ambient + warm sun; `ao` darkens corners, `sunAmt` is 0 inside a shadow. */
export const faceLight = (n: string, ao = 1, sunAmt = 1): [number, number, number] => {
  const N = FACE_N[n];
  const ndl = Math.max(0, N[0] * SUN[0] + N[1] * SUN[1] + N[2] * SUN[2]);
  const dir = n === 'py' ? 1 : n === 'ny' ? 0.55 : 0.82;
  const a = 0.68 * ao * (0.7 + 0.3 * dir);
  const sn = 0.72 * ndl * sunAmt;
  return [AMBIENT[0] * a + SUN_COLOR[0] * sn, AMBIENT[1] * a + SUN_COLOR[1] * sn, AMBIENT[2] * a + SUN_COLOR[2] * sn];
};

/* ---------------- textured boxes (entities, ore blocks, chest, signs) ---------------- */
type Region = [number, number, number, number];
const boxRegions = (u: number, v: number, w: number, h: number, d: number): Record<string, Region> => ({
  px: [u + d + w, v + d, d, h],
  nx: [u, v + d, d, h],
  py: [u + d, v, w, d],
  ny: [u + d + w, v, w, d],
  pz: [u + d, v + d, w, h],
  nz: [u + 2 * d + w, v + d, w, h],
});

/** Materials with the per-face light baked in, shared by every box that uses the same texture (and tint). */
const matCache = new Map<string, THREE.MeshBasicMaterial[]>();
export const shadedMats = (tex: THREE.Texture, alphaTest = 0, tint?: [number, number, number]) => {
  const key = `${tex.uuid}|${alphaTest}|${tint?.join(',') ?? ''}`;
  let m = matCache.get(key);
  if (!m) {
    m = FACE_ORDER.map((f) => {
      const L = faceLight(f);
      const t = tint ?? [1, 1, 1];
      return new THREE.MeshBasicMaterial({ map: tex, color: new THREE.Color(L[0] * t[0], L[1] * t[1], L[2] * t[2]), alphaTest });
    });
    matCache.set(key, m);
  }
  return m;
};
export const useShadedMats = (tex: THREE.Texture, alphaTest = 0) => shadedMats(tex, alphaTest);

/** Vanilla hurt overlay (red flash), as a colour multiplier. */
export const HURT_TINT: [number, number, number] = [1.0, 0.42, 0.42];

/** Box geometries with Minecraft box-UV, built once per (size, uv, scale...) and reused every frame. */
const boxGeoCache = new Map<string, THREE.BoxGeometry>();
const boxGeometry = (size: [number, number, number], origin: [number, number], texSize: [number, number], unit: number, inflate: number, swapVert: boolean, mirror: boolean) => {
  const key = `${size}|${origin}|${texSize}|${unit}|${inflate}|${swapVert}|${mirror}`;
  const hit = boxGeoCache.get(key);
  if (hit) return hit;
  const [w, h, d] = size;
  const g = new THREE.BoxGeometry((w + inflate) * unit, (h + inflate) * unit, (d + inflate) * unit);
  const reg = boxRegions(origin[0], origin[1], w, h, d);
  if (swapVert) [reg.py, reg.ny] = [reg.ny, reg.py];
  if (mirror) [reg.px, reg.nx] = [reg.nx, reg.px];
  const uvA = g.getAttribute('uv') as THREE.BufferAttribute;
  FACE_ORDER.forEach((f, i) => {
    const [rx, ry, rw, rh] = reg[f];
    let x0 = rx / texSize[0];
    let x1 = (rx + rw) / texSize[0];
    if (mirror) [x0, x1] = [x1, x0];
    const y0 = 1 - ry / texSize[1];
    const y1 = 1 - (ry + rh) / texSize[1];
    uvA.setXY(i * 4 + 0, x0, y0);
    uvA.setXY(i * 4 + 1, x1, y0);
    uvA.setXY(i * 4 + 2, x0, y1);
    uvA.setXY(i * 4 + 3, x1, y1);
  });
  boxGeoCache.set(key, g);
  return g;
};

export const TexBox: React.FC<{
  name: string;
  size: [number, number, number]; // px
  origin: [number, number]; // texture origin (u,v)
  texSize?: [number, number];
  position?: [number, number, number];
  unit?: number;
  inflate?: number;
  swapVert?: boolean; // chest-style boxes: top/bottom regions swapped
  mirror?: boolean; // left limbs that reuse the right limb's UV (skeleton, zombie legs on old skins, ...)
  tint?: [number, number, number]; // colour multiplier (hurt flash)
}> = ({ name, size, origin, texSize = [64, 64], position, unit = 1 / 16, inflate = 0, swapVert = false, mirror = false, tint }) => {
  const A = useContext(AssetsCtx);
  const mats = shadedMats(getTex(name, A[name]), 0.1, tint);
  const geo = boxGeometry(size, origin, texSize, unit, inflate, swapVert, mirror);
  return <mesh geometry={geo} material={mats} position={position} castShadow />;
};

/* ---------------- extruded item sprites (held / dropped items, like the game) ---------------- */
const spriteCache = new Map<string, THREE.BufferGeometry>();
const spriteGeometry = (name: string, img: HTMLImageElement) => {
  const hit = spriteCache.get(name);
  if (hit) return hit;
  const c = document.createElement('canvas');
  c.width = c.height = 16;
  const g2 = c.getContext('2d')!;
  g2.drawImage(img, 0, 0);
  const data = g2.getImageData(0, 0, 16, 16).data;
  const solid = (x: number, y: number) => x >= 0 && y >= 0 && x < 16 && y < 16 && data[(y * 16 + x) * 4 + 3] > 40;
  const pos: number[] = [];
  const col: number[] = [];
  const idx: number[] = [];
  const t = 0.5 / 16;
  for (let y = 0; y < 16; y++)
    for (let x = 0; x < 16; x++) {
      if (!solid(x, y)) continue;
      const i = (y * 16 + x) * 4;
      const r = data[i] / 255, g = data[i + 1] / 255, b = data[i + 2] / 255;
      const x0 = (x - 8) / 16, x1 = x0 + 1 / 16, y1 = (8 - y) / 16, y0 = y1 - 1 / 16;
      const faces: [number[][], number, boolean][] = [
        [[[x0, y0, t], [x1, y0, t], [x1, y1, t], [x0, y1, t]], 1, true],
        [[[x1, y0, -t], [x0, y0, -t], [x0, y1, -t], [x1, y1, -t]], 0.8, true],
        [[[x1, y0, t], [x1, y0, -t], [x1, y1, -t], [x1, y1, t]], 0.7, !solid(x + 1, y)],
        [[[x0, y0, -t], [x0, y0, t], [x0, y1, t], [x0, y1, -t]], 0.7, !solid(x - 1, y)],
        [[[x0, y1, t], [x1, y1, t], [x1, y1, -t], [x0, y1, -t]], 0.9, !solid(x, y - 1)],
        [[[x0, y0, -t], [x1, y0, -t], [x1, y0, t], [x0, y0, t]], 0.6, !solid(x, y + 1)],
      ];
      for (const [q, s, on] of faces) {
        if (!on) continue;
        const base = pos.length / 3;
        q.forEach((v) => {
          pos.push(v[0], v[1], v[2]);
          col.push(r * s, g * s, b * s);
        });
        idx.push(base, base + 1, base + 2, base, base + 2, base + 3);
      }
    }
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  geo.setAttribute('color', new THREE.Float32BufferAttribute(col, 3));
  geo.setIndex(idx);
  spriteCache.set(name, geo);
  return geo;
};

let spriteMaterial: THREE.MeshBasicMaterial | null = null;
const spriteMat = () => (spriteMaterial ??= new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.DoubleSide }));

export const Sprite3D: React.FC<{ name: string; scale?: number; position?: [number, number, number]; rotation?: [number, number, number] }> = ({ name, scale = 1, position, rotation }) => {
  const A = useContext(AssetsCtx);
  const geo = useMemo(() => spriteGeometry(name, A[name]), [name, A]);
  return (
    <mesh geometry={geo} material={spriteMat()} position={position} rotation={rotation} scale={scale} castShadow />
  );
};

/** Vanilla model angles (y-down frame) -> three.js Euler. */
export const e3 = (r: Rot) => new THREE.Euler(r[0], -r[1], -r[2], 'ZYX');
/** Player-sized model scale: 1 px = 0.0586 blocks. */
export const U1 = 0.9375 / 16;
