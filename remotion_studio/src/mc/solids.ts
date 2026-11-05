/**
 * Minecraft video kit — the hitboxes of everything that is not an actor, derived from the episode data:
 * hills and tree trunks from the world spec, and chest, signs, ladder column, door frame, ore veins and the closed door leaf
 * from the props. Actors walk around them (choreo), pushed actors are kept out of them (collision.separate),
 * and the validator checks that nobody ends up inside one.
 */
import type { Track } from './choreo';
import { Box, Solid, rotBox } from './collision';
import { DoorSpec, PropSpec, doorOpenAmount, veinBreaks } from './props';
import { WorldSpec, terrainBounds, terrainHeight } from './world';

const Q = 1 / 16;

const worldSolids = (w: WorldSpec): Solid[] => {
  const out: Solid[] = [];
  const h = terrainHeight(w);
  const [x0, x1, z0, z1] = terrainBounds(w);
  for (let z = z0; z <= z1; z++) {
    let run = -1; // merge raised cells of a row into one box
    for (let x = x0; x <= x1 + 1; x++) {
      const up = x <= x1 && h(x, z) > 0;
      if (up && run < 0) run = x;
      if (!up && run >= 0) {
        out.push({ box: [run, z, x, z + 1], y0: 0, y1: 3, what: 'hill' });
        run = -1;
      }
    }
  }
  w.trees.forEach(([x, z, H]) => out.push({ box: [x, z, x + 1, z + 1], y0: 0, y1: H, what: 'tree' }));
  return out;
};

const doorLeaf = (d: DoorSpec): Box => rotBox(d.at[0], d.at[1], 0.5, 3 / 32, d.rotY ?? 0);

const propSolids = (p: PropSpec): Solid[] => {
  switch (p.type) {
    case 'sign':
      return [{ box: rotBox(p.at[0], p.at[1], 0.75, Q, p.rotY ?? 0), y0: 0, y1: 26 * Q, what: 'sign' }];
    case 'chest':
      return [{ box: [p.at[0] - 7 * Q, p.at[1] - 7 * Q, p.at[0] + 7 * Q, p.at[1] + 7 * Q], y0: 0, y1: 14 * Q, what: 'chest' }];
    case 'ladder':
      return [{ box: rotBox(p.at[0], p.at[1], 0.5, 0.55, p.rotY ?? 0, 0, 0.05), y0: 0, y1: p.height, what: 'ladder' }];
    case 'door':
      return p.frame === false ? [] : [-1, 1].map((dx) => ({ box: rotBox(p.at[0], p.at[1], 0.5, 0.5, p.rotY ?? 0, dx, 0), y0: 0, y1: 3, what: 'door frame' }));
    case 'stall':
      return [
        { box: rotBox(p.at[0], p.at[1], 1.0, 0.5, p.rotY ?? 0), y0: 0, y1: 1, what: 'stall counter' },
        ...[-1.3, 1.3].map((dx) => ({ box: rotBox(p.at[0], p.at[1], 0.125, 0.125, p.rotY ?? 0, dx, 0.45), y0: 0, y1: 2.2, what: 'stall post' })),
      ];
    case 'library':
      return [{ box: [p.at[0] - 1.5, p.at[1] - 0.5, p.at[0] + 1.5, p.at[1] + 0.5] as Box, y0: 0, y1: 2, what: 'library' }];
    case 'house':
      return [{ box: [p.at[0] - p.w / 2, p.at[1] - p.d / 2, p.at[0] + p.w / 2, p.at[1] + p.d / 2] as Box, y0: 0, y1: (p.h ?? 3) + 1.5, what: 'house' }];
    case 'vein':
      return p.cells.map(([y, z]) => ({ box: [p.x, z, p.x + 1, z + 1] as Box, y0: y, y1: y + 1, what: 'ore block' }));
  }
};

/** Static solids used to plan paths (the door leaf is left out: actors open it before walking through). */
export const planningSolids = (world: WorldSpec, props: PropSpec[]): Solid[] => [...worldSolids(world), ...props.flatMap(propSolids)];

/** Ground-level boxes that block a body of height h (anything starting below its head). */
export const blockingBoxes = (solids: Solid[], h = 1.8): Box[] => solids.filter((s) => s.y0 < h).map((s) => s.box);

/** Every solid with its time range (ore blocks disappear when they break, the door leaf only blocks while it is closed). */
export const episodeSolids = (world: WorldSpec, props: PropSpec[], tracks: Record<string, Track>): Solid[] => {
  const out = worldSolids(world);
  props.forEach((p) => {
    if (p.type === 'vein') {
      const info = veinBreaks(p, tracks);
      p.cells.forEach(([y, z], k) => out.push({ box: [p.x, z, p.x + 1, z + 1], y0: y, y1: y + 1, to: info?.breaks[k], what: 'ore block' }));
      return;
    }
    out.push(...propSolids(p));
    if (p.type === 'door') {
      // closed (less than ~45 degrees open) before openAt+6 and after closeAt+5
      let f = p.openAt;
      while (f < p.openAt + 30 && doorOpenAmount(f, p) < 0.5) f++;
      let g = p.closeAt;
      while (g < p.closeAt + 30 && doorOpenAmount(g, p) >= 0.5) g++;
      out.push({ box: doorLeaf(p), y0: 0, y1: 2, to: f, what: 'closed door' });
      out.push({ box: doorLeaf(p), y0: 0, y1: 2, from: g, what: 'closed door' });
    }
  });
  return out;
};
