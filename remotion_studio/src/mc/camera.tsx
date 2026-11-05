/**
 * Minecraft video kit — camera: shots with slow moves, whip-zoom transitions (zoom in before a cut, zoom out after it) and a rig.
 * Rules that came out of testing: few long shots (>= ~60 frames), transitions of 12 frames per side, fov dip of 28 %.
 * More cuts or faster zooms make the video dizzy.
 */
import { useLayoutEffect } from 'react';
import { useThree } from '@react-three/fiber';
import * as THREE from 'three';
import type { Track } from './choreo';
import { V3 } from './core';

export interface Shot {
  from: number;
  to: number;
  p0: V3; // camera position at the start / end of the shot
  p1: V3;
  l0: V3; // look-at point at the start / end
  l1: V3;
  fov?: number;
  follow?: string; // actor id: camera and look-at positions are offsets from that actor's (x, z)
  eased?: boolean; // smoothstep the move (use for pans)
}

export const CUT_FRAMES = 12;

export const cutIntensity = (shots: Shot[], f: number) => {
  let d = 99;
  shots.forEach((sh, i) => {
    if (i > 0) d = Math.min(d, Math.abs(f - sh.from + 0.5));
  });
  const x = Math.max(0, 1 - d / CUT_FRAMES);
  return x * x * (3 - 2 * x);
};

export interface CamState { pos: V3; look: V3; fov: number }
/** Camera position, look-at point and field of view at frame f (before the transition zoom). */
export const cameraAt = (shots: Shot[], tracks: Record<string, Track>, f: number): CamState => {
  const sh = shots.find((x) => f >= x.from && f < x.to) ?? shots[shots.length - 1];
  let t = Math.min(1, Math.max(0, (f - sh.from) / (sh.to - sh.from)));
  if (sh.eased) t = t * t * (3 - 2 * t);
  const T = sh.follow ? tracks[sh.follow] : undefined;
  const cx = T ? T.x[T.at(f)] : 0;
  const cz = T ? T.z[T.at(f)] : 0;
  const L = (a: V3, b: V3, i: number) => a[i] + (b[i] - a[i]) * t;
  const sway = Math.sin(f * 0.11) * 0.012;
  return {
    pos: [cx + L(sh.p0, sh.p1, 0), L(sh.p0, sh.p1, 1) + sway, cz + L(sh.p0, sh.p1, 2)],
    look: [cx + L(sh.l0, sh.l1, 0), L(sh.l0, sh.l1, 1), cz + L(sh.l0, sh.l1, 2)],
    fov: sh.fov ?? 52,
  };
};

export const Rig: React.FC<{ f: number; shots: Shot[]; tracks: Record<string, Track> }> = ({ f, shots, tracks }) => {
  const camera = useThree((s) => s.camera) as THREE.PerspectiveCamera;
  const c = cameraAt(shots, tracks, f);
  const zoom = cutIntensity(shots, f);
  useLayoutEffect(() => {
    camera.fov = c.fov * (1 - 0.28 * zoom);
    camera.position.set(...c.pos);
    camera.lookAt(...c.look);
    camera.updateProjectionMatrix();
    camera.updateMatrixWorld();
  });
  return null;
};
