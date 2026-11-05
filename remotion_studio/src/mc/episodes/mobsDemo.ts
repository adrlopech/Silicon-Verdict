/** Demo episode used to check every actor type: player (wave), zombie, skeleton, creeper, pig, cow and chicken. */
import type { EpisodeSpec } from '../episode';

const world = {
  flatX: [-8, 24] as [number, number],
  flatZ: [-8, 10] as [number, number],
  paths: [{ z: 1, x: [-6, 22] as [number, number] }],
  trees: [[-5, -5, 5], [10, -6, 4], [17, -5, 5]] as [number, number, number][],
  plantArea: [100, 100, 99, 99] as [number, number, number, number], // no plants in this test scene
  noPlants: [] as [number, number, number, number][],
  sunTarget: [7, 2] as [number, number],
  sunSpan: 18,
};

export const mobsDemo: EpisodeSpec = {
  id: 'mobs-demo',
  title: 'MOBS DEL JUEGO',
  cta: '',
  frames: 240,
  beats: [{ from: 0, to: 240, text: 'Todos los mobs, con animación vainilla suave' }],
  world,
  shots: [
    { from: 0, to: 120, p0: [2.5, 1.5, 5.2], p1: [4.5, 1.5, 5.2], l0: [0.6, 1, 0], l1: [0.6, 1, 0], fov: 50, follow: 'p' }, // follow the player: wave, jump, walk
    { from: 120, to: 240, p0: [19, 2.2, 8], p1: [15, 2.0, 7], l0: [16, 0.9, 1.8], l1: [13, 0.9, 1.5], fov: 48 },
  ],

  actors: [
    { id: 'p', kind: 'player', hand: [{ f: 0, item: 'item_iron_pickaxe' }, { f: 150, item: 'item_iron_sword' }], plan: { start: [0, 3], face: 0, steps: [{ t: 'act', kind: 'wave', frames: 50 }, { t: 'act', kind: 'jump', frames: 20 }, { t: 'walk', to: [9, 3] }, { t: 'act', kind: 'attack', frames: 60 }] } },
    { id: 'z', kind: 'zombie', plan: { start: [16, 3], face: -Math.PI / 2, steps: [{ t: 'wait', frames: 20 }, { t: 'walk', to: [10.5, 3], speed: 2.4 }] } },
    { id: 's', kind: 'skeleton', plan: { start: [18, 5], face: -Math.PI / 2, steps: [{ t: 'walk', to: [11, 5.5], speed: 3.2 }] } },
    { id: 'c', kind: 'creeper', swell: 0, plan: { start: [20, 1], face: -Math.PI / 2, steps: [{ t: 'wait', frames: 40 }, { t: 'walk', to: [13, 1.2], speed: 2.8 }] } },
    { id: 'pig', kind: 'pig', plan: { start: [2, -1], face: Math.PI / 2, steps: [{ t: 'walk', to: [7, -1], speed: 1.6 }, { t: 'face', to: 0.4 }] } },
    { id: 'cow', kind: 'cow', plan: { start: [5, -3], face: Math.PI / 2, steps: [{ t: 'wait', frames: 30 }, { t: 'walk', to: [9, -2.6], speed: 1.4 }] } },
    { id: 'hen', kind: 'chicken', plan: { start: [1, 1], face: Math.PI / 2, steps: [{ t: 'walk', to: [4.5, 1.5], speed: 1.5 }, { t: 'walk', to: [3.5, 0.5], speed: 1.2 }] } },
  ],
  props: [],
  sounds: [
    { f: 30, event: 'entity.pig.ambient' },
    { f: 90, event: 'entity.cow.ambient' },
    { f: 130, event: 'entity.zombie.ambient' },
    { f: 170, event: 'entity.chicken.ambient' },
  ],
};

/** Inspection scene: one follow camera per mob (pig, cow, chicken, creeper, zombie, skeleton), each walking in a straight line. */
const mk = (id: string, kind: 'pig' | 'cow' | 'chicken' | 'creeper' | 'zombie' | 'skeleton' | 'sheep' | 'villager' | 'spider' | 'cave_spider', x: number, z: number, speed: number) =>
  ({ id, kind, plan: { start: [x, z] as [number, number], face: Math.PI / 2, steps: [{ t: 'walk' as const, to: [x + 5, z] as [number, number], speed }] } });
const cam = (id: string, from: number) => ({ from, to: from + 40, p0: [1.0, 1.2, 3.4] as [number, number, number], p1: [1.6, 1.2, 3.0] as [number, number, number], l0: [0.6, 0.8, 0] as [number, number, number], l1: [0.8, 0.8, 0] as [number, number, number], fov: 50, follow: id });
export const mobsLine: EpisodeSpec = {
  id: 'mobs-line',
  title: '',
  cta: '',
  frames: 400,
  beats: [],
  world: { ...world, flatX: [-8, 32], flatZ: [-8, 13], trees: [[-5, -8, 5], [10, -8, 4], [17, -8, 5]], sunTarget: [5, 2] }, // room for the follow cameras
  shots: [cam('pig', 0), cam('cow', 40), cam('hen', 80), cam('creeper', 120), cam('zombie', 160), cam('skel', 200), cam('sheep', 240), cam('villager', 280), cam('spider', 320), cam('cave', 360)],
  actors: [mk('pig', 'pig', -6, 4, 1.7), mk('cow', 'cow', 3, 4, 1.5), mk('hen', 'chicken', 12, 4, 1.6), mk('creeper', 'creeper', -6, -4, 2.4), mk('zombie', 'zombie', 3, -4, 2.6), mk('skel', 'skeleton', 12, -4, 3.2), mk('sheep', 'sheep', -6, 8, 1.5), mk('villager', 'villager', 3, 8, 1.6), mk('spider', 'spider', 18, 8, 1.8), mk('cave', 'cave_spider', 24, 8, 1.8)],
  props: [],
};
