/** Demo: swim across a pond, open a door and walk through, climb a ladder; with a villager, sheep and spiders around. */
import { ActorPlan, buildTrack } from '../choreo';
import type { EpisodeSpec } from '../episode';

const FR = 360;
const Z = 2.5;
const DOOR = { x: 16.5, z: Z };
const plan: ActorPlan = {
  start: [0.5, Z],
  face: Math.PI / 2,
  obstacles: [[16, 3, 17, 4], [16, 1, 17, 2]], // the planks either side of the doorway
  steps: [
    { t: 'wait', frames: 20 },
    { t: 'walk', to: [3.4, Z] },
    { t: 'walk', to: [7.4, Z], swim: true }, // across the pond (swimming is decided by being inside the water)
    { t: 'walk', to: [14.5, Z] },
    { t: 'act', kind: 'reach', frames: 36 }, // open the door
    { t: 'walk', to: [19.2, Z] }, // through the doorway
    { t: 'walk', to: [22.0, Z] },
    { t: 'act', kind: 'climb', frames: 44, rise: 3.4 }, // up the ladder
    { t: 'wait', frames: 30 },
  ],
};
const T = buildTrack(plan, FR);
const m = T.marks;
const reach = T.acts.find((a) => a.kind === 'reach')!;
const pastDoor = T.x.findIndex((x) => x > 18.4);

export const actionsDemo: EpisodeSpec = {
  id: 'actions-demo',
  title: 'ACCIONES',
  cta: '',
  frames: FR,
  titleFrames: 50,
  beats: [
    { from: 0, to: m[3], text: 'Nadar', hl: 'Nadar' },
    { from: m[3], to: m[5], text: 'Abrir puertas', hl: 'puertas' },
    { from: m[5], to: FR, text: 'Trepar escaleras', hl: 'Trepar' },
  ],
  world: {
    flatX: [-8, 26], flatZ: [-8, 10], paths: [], trees: [[-4, -4, 5], [12, -6, 4], [26, -4, 5]],
    plantArea: [-8, -3, 12, 8], noPlants: [], sunTarget: [13, 2.5], sunSpan: 22, ponds: [[4, -1, 8, 6, 2]],
  },
  shots: [
    { from: 0, to: m[3] - 30, p0: [1.0, 1.4, 4.8], p1: [2.2, 1.0, 4.2], l0: [0.8, 0.4, 0], l1: [1.2, 0.2, 0], fov: 56, follow: 'steve' }, // walk to the pond and swim
    { from: m[3] - 30, to: reach.start - 6, p0: [-1.5, 1.5, 4.6], p1: [2.0, 1.7, 4.2], l0: [1.5, 0.9, 0], l1: [2.5, 1.0, 0], fov: 54, follow: 'steve' }, // out of the water, towards the door
    { from: reach.start - 6, to: m[6], p0: [-4.6, 1.7, 5.4], p1: [-3.4, 1.8, 5.8], l0: [2.6, 1.0, 0], l1: [3.2, 1.0, 0], fov: 52, follow: 'steve' }, // door opens, walk through (seen from the approach side)
    { from: m[6], to: FR, p0: [-2.6, 1.8, 3.4], p1: [-2.8, 3.9, 3.4], l0: [0.6, 1.4, 0], l1: [0.6, 3.5, 0], fov: 54, follow: 'steve' }, // ladder, three-quarter view of the ladder face
  ],
  actors: [
    { id: 'steve', kind: 'player', plan },
    { id: 'villager', kind: 'villager', plan: { start: [19.8, 6.4], face: -Math.PI / 2, steps: [{ t: 'wait', frames: 60 }, { t: 'walk', to: [19.0, 7.2], speed: 1.4 }] } },
    { id: 'sheep', kind: 'sheep', plan: { start: [10, -3.5], face: Math.PI / 2, steps: [{ t: 'walk', to: [13.5, -3.5], speed: 1.3 }] } },
    { id: 'spider', kind: 'spider', plan: { start: [14, 7.5], face: -Math.PI / 2, steps: [{ t: 'wait', frames: 80 }, { t: 'walk', to: [10, 7.5], speed: 1.5 }] } },
  ],
  props: [
    { type: 'door', at: [DOOR.x, DOOR.z], rotY: Math.PI / 2, openAt: reach.start + 6, closeAt: Math.max(pastDoor + 4, reach.start + 40) },
    { type: 'ladder', at: [23.0, Z], height: 4, rotY: -Math.PI / 2 },
  ],
  sounds: [{ f: 30, event: 'entity.sheep.ambient' }, { f: 140, event: 'entity.villager.ambient' }, { f: 200, event: 'entity.spider.ambient' }],
};
