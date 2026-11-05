/**
 * Minecraft video kit — director: compiles a small, JSON-serialisable SCRIPT into a complete EpisodeSpec.
 *
 * A script says WHAT happens (stations in the world, who does what, what the subtitle says); the director decides HOW:
 *   - layout: stations are placed along the x axis with safe spacing; walls, chest, doors, ponds, ladders, signs and mobs are generated
 *   - choreography: actions become plan steps (auto-walk to the station, face it, act); every beat waits for the slowest actor so that
 *     subtitles, actions and camera stay in sync; the total length is stretched towards `seconds` (default 20 s)
 *   - camera: shots are planned from the real tracks (follow / pan / orbit / wide / close / swim / climb), >= 60 frames, a cut every ~3 s;
 *     still shots frame the subject from the front three-quarter side and are rejected if they clip an actor or a block hides the subject
 *   - hitboxes: the director uses the episode's own solids (collision.ts / solids.ts), so planned timing equals the rendered timing
 *   - props, hand items, hotbar, sounds: derived from the timeline (chest/door timing from the actor's acts, tool from the act...)
 * Gemini only has to produce the script (see services/mc_story_generator.py); everything the kit learned is applied here.
 * Docs: docs/minecraft_video_kit.md › "Guiones y generador".
 */
import { ActKind, ActorPlan, Step, Track, Vec2, planTrack } from './choreo';
import { Shot, cameraAt } from './camera';
import { Box, Solid, inBox, segHitsBox } from './collision';
import { rnd } from './core';
import { ActorSpec, Beat, EpisodeSpec, Transfer, buildTracks, pondBoxes, resolvePlan } from './episode';
import { ActorKind, KINDS, isHumanoid } from './kinds';
import type { Ore, PropSpec } from './props';
import type { SoundEvent } from './sfx';
import { planningSolids } from './solids';
import type { WorldSpec } from './world';

/* ------------------------------ script format ------------------------------ */
export type StationType = 'sign' | 'mine' | 'chest' | 'pond' | 'door' | 'ladder' | 'pen' | 'stall' | 'library';
export type PenKind = 'pig' | 'cow' | 'chicken' | 'sheep' | 'villager' | 'spider' | 'zombie' | 'skeleton' | 'creeper';
export interface StationSpec {
  id: string;
  type: StationType;
  label?: string[]; // text of a sign next to the station (max 4 lines, ~12 chars each); for type 'sign' this is the whole point
  ores?: Ore[]; // mine: ores of the vein, in breaking order
  kinds?: PenKind[]; // pen: mobs standing there
  keeper?: string; // stall: shopkeeper profession (default farmer: straw hat)
  items?: string[]; // stall: item textures on the counter (item_emerald, item_bread, item_diamond, item_gold_ingot...)
  gap?: number; // free blocks before this station (default 8)
}
export type ActName = 'go' | 'sprint' | 'mine' | 'open_chest' | 'swim' | 'open_door' | 'climb' | 'wave' | 'jump' | 'use' | 'attack' | 'look' | 'wait' | 'cheer' | 'give' | 'nod' | 'shake' | 'point' | 'read' | 'pace' | 'take_book' | 'put_book' | 'fetch' | 'show' | 'search';
export interface ActionSpec {
  actor?: string; // default: the hero
  act: ActName;
  target?: string; // station id (or actor id for 'look')
  seconds?: number; // duration for wave / use / attack / wait / cheer
  to?: string; // fetch: where the item is brought (station or actor id); target = where it is taken from
  item?: string; // give: item texture handed over (item_emerald, item_diamond...); target = station id or actor id
  swings?: number; // mine: blocks to break (1-6, default 6)
  fast?: boolean; // mine: quicker swings (more "power")
}
export type ShotStyle = 'sign' | 'close' | 'low' | 'orbit' | 'wide' | 'follow' | 'pan';
export interface ScriptBeat {
  text: string; // subtitle (Spanish or English), <= 60 characters recommended
  hl?: string; // one word of the text to highlight
  seconds?: number; // minimum on-screen time
  shot?: ShotStyle; // camera hint for the shot that starts here
  focus?: string; // station id (for 'sign'/'close') or actor id the camera looks at
  actions?: ActionSpec[]; // run in parallel for different actors, in order for the same actor
  sound?: string; // extra game sound event at the start of the beat, e.g. 'entity.pig.ambient'
  stock?: string[]; // from this beat on, the stall counter shows these items (new ones pop in with sparkles): data being copied / multiplied
  tag?: { now: string; was?: string; icon?: string }; // from this beat on, the stall shows a value plaque (old value struck through, new value below)
  stall?: string; // stall station for stock/tag (default: the first stall)
  words?: { s: number; e: number }[]; // narration timing of each word of `text` (seconds from the start of the voice clip); set by the pipeline, not by the author
}
export const PLAYER_SKINS = ['steve', 'alex', 'ari', 'efe', 'kai', 'makena', 'noor', 'sunny', 'zuri', 'tuxduck', 'shadow', 'duck', 'smiley', 'potato', 'goth']; // the last six come from NameMC (assets/skins/namemc)
export const PROFESSIONS = ['farmer', 'librarian', 'toolsmith', 'cleric', 'fisherman', 'mason', 'cartographer', 'armorer'];
/** Short skin name -> texture: players use skin_<name>, villagers mob_villager_<profession>. */
const skinTexture = (kind: ActorKind, skin?: string): string | undefined => {
  if (!skin) return undefined;
  if (kind === 'player') return PLAYER_SKINS.includes(skin) ? `skin_${skin}` : undefined;
  if (kind === 'villager') return PROFESSIONS.includes(skin) ? `mob_villager_${skin}` : undefined;
  return undefined;
};
export interface CastSpec { id: string; kind: ActorKind; at?: string; skin?: string } // skin: PLAYER_SKINS for players, PROFESSIONS for villagers
export interface McScript {
  id: string;
  time?: 'day' | 'dusk' | 'night'; // time of day (default day); dusk and night add torches by signs and stalls
  title: string; // on-screen title for the first 2 seconds
  cta: string; // call to action shown at the end
  seconds?: number; // target length (default 20; the Minecraft series uses 64 for TikTok monetisation)
  surface?: string; // footstep surface: grass (default), stone, sand, gravel, wood, snow
  hero?: string; // id of the main actor (default 'steve' = the player)
  cast?: CastSpec[]; // extra actors that follow actions (the hero is created automatically)
  stations: StationSpec[];
  beats: ScriptBeat[];
  inventory?: { items?: string[]; grow_at_beat?: number }; // hotbar contents (texture names) and the beat where the second row appears
}

export interface CompileResult { spec: EpisodeSpec | null; errors: string[]; warnings: string[]; frames: number; seconds: number }

/* ------------------------------ layout ------------------------------ */
const Z = 1.5; // actors walk along this z
const FPS = 30;
const STALL_ITEMS = ['item_emerald', 'item_bread', 'item_diamond', 'item_gold_ingot', 'item_diamond_sword', 'item_redstone', 'item_apple', 'item_coal', 'item_wheat', 'item_book', 'item_paper', 'item_writable_book'];
const STATION_TYPES: StationType[] = ['sign', 'mine', 'chest', 'pond', 'door', 'ladder', 'pen', 'stall', 'library'];
const PEN_KINDS: PenKind[] = ['pig', 'cow', 'chicken', 'sheep', 'villager', 'spider', 'zombie', 'skeleton', 'creeper'];
const ORES: Ore[] = ['coal', 'iron', 'gold', 'redstone', 'lapis', 'diamond'];
const MINE_CELLS: [number, number][] = [[0, 1], [1, 1], [2, 1], [0, 0], [1, 0], [2, 0]]; // [y, z] of the six blocks of a vein
const TOOL: Partial<Record<ActKind, string>> = { mine: 'item_diamond_pickaxe', attack: 'item_iron_sword' };

interface Placed {
  spec: StationSpec;
  x: number; // left edge
  end: number; // right edge
  stand: Vec2; // where the hero stops to use it
  after?: Vec2; // where actors end up after crossing it (pond / door)
  swimTo?: Vec2;
  pond?: [number, number, number, number, number];
  door?: number; // x of the doorway
  focus: Vec2;
  signAt?: Vec2;
  obstacles: Box[];
  noPlants: Box[];
  mobs: { kind: PenKind; at: Vec2; skin?: string }[];
  props: PropSpec[]; // static props (the ones that depend on timing are added later)
  mines: number; // vein layers used
  opens: number;
}

const placeStations = (stations: StationSpec[]): Placed[] => {
  const out: Placed[] = [];
  let x = 3.2;
  stations.forEach((s, i) => {
    if (i > 0) x = out[i - 1].end + (s.gap ?? 8);
    const P: Placed = { spec: s, x, end: x + 2, stand: [x, Z], focus: [x + 1, Z], obstacles: [], noPlants: [], mobs: [], props: [], mines: 0, opens: 0 };
    const sign = (sx: number) => {
      if (!s.label?.length) return;
      P.signAt = [sx, -0.35];
      P.props.push({ type: 'sign', at: [sx, -0.35], lines: s.label.slice(0, 4), rotY: (rnd(i * 5.3 + 1) - 0.5) * 0.3 });
      P.noPlants.push([sx - 0.9, -1, sx + 0.9, 0.6]);
    };
    if (s.type === 'sign') {
      sign(x);
      P.stand = [x + 1.8, Z];
      P.focus = [x, -0.35];
      P.end = x + 2.4;
    } else {
      sign(x - 1.2);
      if (s.type === 'mine') {
        P.obstacles.push([x + 0.8, 0, x + 2.8, 2]); // both vein layers
        P.noPlants.push([x + 0.6, -0.5, x + 3.0, 2.5]);
        P.focus = [x + 0.8, Z];
        P.end = x + 3;
      } else if (s.type === 'chest') {
        P.props.push({ type: 'chest', at: [x + 1.6, Z], openAt: 0, closeAt: 0 }); // within arm's reach of the stand; timing filled in later
        P.noPlants.push([x + 0.9, 0.8, x + 2.5, 2.2]);
        P.focus = [x + 1.6, Z];
        P.end = x + 2.6;
      } else if (s.type === 'pond') {
        const x0 = Math.ceil(x + 0.7); // block aligned: the carved hole, the water surface and the swim area are the same cells
        P.pond = [x0, -1, x0 + 4, 4, 2];
        P.stand = [x0 - 0.8, Z];
        P.focus = [x0 + 2, Z];
        P.swimTo = [x0 + 3.4, Z];
        P.after = [x0 + 5, Z];
        P.end = x0 + 5;
      } else if (s.type === 'door') {
        const dx = x + 2;
        P.door = dx;
        P.obstacles.push([dx - 0.5, Z - 1.5, dx + 0.5, Z - 0.5], [dx - 0.5, Z + 0.5, dx + 0.5, Z + 1.5]);
        P.noPlants.push([dx - 1, Z - 1.8, dx + 1, Z + 1.8]);
        P.after = [dx + 2.2, Z];
        P.focus = [dx, Z];
        P.end = dx + 2.4;
      } else if (s.type === 'ladder') {
        const lx = x + 1;
        P.props.push({ type: 'ladder', at: [lx, Z], height: 4, rotY: -Math.PI / 2 });
        P.noPlants.push([lx - 1, Z - 1, lx + 1, Z + 1]);
        P.focus = [lx, Z];
        P.end = x + 2;
      } else if (s.type === 'stall') {
        const sx = x + 1.6;
        P.props.push({ type: 'stall', at: [sx, 0.55], items: (s.items ?? []).slice(0, 4) }); // only what the script puts there
        P.mobs.push({ kind: 'villager', at: [sx, -0.3], skin: skinTexture('villager', s.keeper ?? 'farmer') }); // the shopkeeper behind the counter
        P.noPlants.push([sx - 1.6, -1.2, sx + 1.6, 1.4]);
        P.stand = [sx - 1.15, Z]; // beside the counter, not in front of it: the camera sees the items and the shopkeeper past him
        P.focus = [sx, 0.55];
        P.end = sx + 1.5;
      } else if (s.type === 'library') {
        const lx = x + 1.9; // shelf wall behind the path; the hero stands at its left end so it never hides the shelves
        P.props.push({ type: 'library', at: [lx, 0.3], fill: 6 }); // libraries are always full of books
        P.noPlants.push([lx - 2, -1, lx + 2, 1.2]);
        P.stand = [lx - 1.35, Z];
        P.focus = [lx - 0.2, 0.3];
        P.end = lx + 2.2;
      } else if (s.type === 'pen') {
        const kinds = (s.kinds?.length ? s.kinds : (['pig'] as PenKind[])).slice(0, 4);
        let mx = x + 0.6;
        kinds.forEach((k, j) => { // spaced by their hitboxes; wide mobs stay further from the path
          const half = KINDS[k].w / 2;
          mx += half;
          P.mobs.push({ kind: k, at: [mx, (j % 2 ? 0.65 : 0.1) - Math.max(0, half - 0.45)] });
          mx += half + 0.6;
        });
        P.focus = [(x + mx) / 2, 0.4];
        P.end = mx + 0.6;
      }
    }
    out.push(P);
  });
  return out;
};

/** Props known from the layout alone (signs, ladder, the chest and door with their timing still unknown): enough for hitboxes. */
const layoutProps = (placed: Placed[]): PropSpec[] =>
  placed.flatMap((p) => [...p.props, ...(p.door != null ? [{ type: 'door' as const, at: [p.door, Z] as Vec2, rotY: Math.PI / 2, openAt: 99999, closeAt: 99999 }] : [])]);

/** Village houses in the background (behind the signs and stalls, facing the camera); trees and plants give way to them. */
const makeHouses = (placed: Placed[], world: WorldSpec): PropSpec[] => {
  const endX = Math.max(...placed.map((p) => p.end)) + 4;
  const out: PropSpec[] = [];
  let x = 1.5 + rnd(3.3) * 3;
  for (let k = 0; x < endX; k++) {
    const w = 4 + Math.round(rnd(k * 2.3 + 1) * 2) * 0.5 + (k % 2 ? 0.5 : 0), d = 3.4 + (k % 3 === 1 ? 0.6 : 0);
    const at: [number, number] = [x + w / 2, -4.3 - rnd(k + 5) * 0.5];
    out.push({ type: 'house', at, w, d, h: k % 3 === 2 ? 3.5 : 3, lit: true });
    world.noPlants.push([at[0] - w / 2 - 0.5, at[1] - d / 2 - 0.5, at[0] + w / 2 + 0.5, at[1] + d / 2 + 2.2]);
    world.trees = world.trees.filter(([tx, tz]) => !(tx > at[0] - w / 2 - 3.2 && tx < at[0] + w / 2 + 3.2 && tz > at[1] - d / 2 - 3.2 && tz < at[1] + d / 2 + 3.2));
    x += w + 3.2 + rnd(k * 1.7 + 8) * 3;
  }
  return out;
};

const makeWorld = (placed: Placed[]): WorldSpec => {
  const endX = Math.max(...placed.map((p) => p.end)) + 6;
  const trees: [number, number, number][] = [];
  for (let x = -9, k = 0; x < endX + 9; x += 5.5 + rnd(k * 2.7) * 3.5, k++) trees.push([Math.round(x + rnd(k) * 2), -5 - Math.round(rnd(k + 9) * 3), 4 + Math.round(rnd(k + 4))]);
  const ponds = placed.filter((p) => p.pond).map((p) => p.pond!);
  const paths: { z: number; x: [number, number] }[] = [];
  let px = -4;
  ponds.forEach(([x0, , x1]) => {
    paths.push({ z: 1, x: [px, x0 - 1] });
    px = x1;
  });
  paths.push({ z: 1, x: [px, endX - 2] });
  return {
    flatX: [-6, endX + 4],
    flatZ: [-7.5, 10.5],
    paths: paths.filter((s) => s.x[1] > s.x[0] + 1),
    trees,
    plantArea: [-6, -3, endX + 2, 4],
    noPlants: [[-6, 0.6, endX + 4, 2.4], ...placed.flatMap((p) => p.noPlants)],
    sunTarget: [endX / 2, Z],
    sunSpan: Math.max(26, endX / 2 + 8),
    ponds,
  };
};

/* ------------------------------ timeline ------------------------------ */
interface AState {
  id: string;
  kind: ActorKind;
  skin?: string;
  start: Vec2;
  face: number;
  steps: Step[];
  pos: Vec2;
  at: string | null;
  acts: number; // act steps pushed so far (index into track.acts)
  tags: { idx: number; kind: ActKind; station?: string; extra?: string }[];
  lenAt: number; // memo of the plan length (steps are only ever appended)
  lenVal: number;
}

/** Where a non-hero actor stands at a station: behind the hero, or beside him in front of a stall (the counter is behind). */
const sideSpot = (st: Placed): Vec2 => (st.spec.type === 'stall' ? [st.focus[0] - 2.2, st.stand[1]] : st.spec.type === 'library' ? [st.focus[0] + 2.1, st.stand[1]] : [st.stand[0] - 0.7, st.stand[1] - 1.0]);

/** What the hero does in a beat the script left empty, taken from the meaning of the line and from what exists in the world:
 *  walk to / search / take from / hand over to the stations the line is about. No decorative nodding: every action has a purpose. */
const fillerFor = (b: ScriptBeat, bi: number, placed: Placed[], at: string | null): ActionSpec[] => {
  const t = b.text.toLowerCase();
  const real = placed.filter((p) => p.spec.type !== 'sign');
  const focus = b.focus ? placed.find((p) => p.spec.id === b.focus) : undefined;
  const lib = real.find((p) => p.spec.type === 'library');
  const stall = real.find((p) => p.spec.type === 'stall');
  const others = real.filter((p) => p.spec.id !== at);
  const hasWord = (re: RegExp) => re.test(t);
  if (lib && hasWord(/\b(find|finds|found|search|searching|look up|looks up|lookup|index|indexed|catalog|where)\b/)) return [{ act: 'search', target: lib.spec.id }];
  if (lib && hasWord(/\b(book|books|library|libraries|import|imports|reuse|ready-made|pre-made|grab|grabs|use|uses|get|gets)\b/)) return [{ act: bi % 2 ? 'take_book' : 'read', target: lib.spec.id }];
  if (hasWord(/\b(book|books|read|reads|reading|document|documents|docs|page|pages|text|file|files)\b/)) return [{ act: 'read' }];
  if (stall && hasWord(/\b(request|requests|ask|asks|asking|send|sends|sending|call|calls|query|queries|answer|answers|response|responds|deliver|delivers|order|orders|data)\b/))
    return [{ act: 'give', target: stall.spec.id, item: stall.props.find((p) => p.type === 'stall' && p.items?.length) ? (stall.props.find((p) => p.type === 'stall') as { items: string[] }).items[0] : 'item_paper' }];
  if (others.length && hasWord(/\b(walk|walks|walking|far|distant|fetch|fetches|fetching|travel|travels|go|goes|going|move|moves|slow|slower|wait|waits|waiting)\b/))
    return [{ act: hasWord(/\b(fast|quick|quickly|instant)\b/) ? 'sprint' : 'go', target: (focus && focus.spec.id !== at ? focus : others[bi % others.length]).spec.id }];
  if (hasWord(/\b(fast|faster|quick|quickly|instant|instantly|speed|nearby|close|closer)\b/) && others.length) return [{ act: 'sprint', target: (focus && focus.spec.id !== at ? focus : others[bi % others.length]).spec.id }];
  if (hasWord(/\b(this|here|there|look|see|show|shows|example)\b/)) return [{ act: focus ? 'point' : 'show', target: focus?.spec.id }];
  if (focus && focus.spec.id !== at) return [{ act: 'go', target: focus.spec.id }];
  if (focus) return [{ act: 'point', target: focus.spec.id }];
  return [{ act: 'pace' }];
};

const fr = (s: number) => Math.round(s * FPS);
const readFrames = (text: string) => fr(Math.max(1.8, text.length / 20 + 0.3));

const tokenFor = (text: string, hl?: string) => {
  if (!hl) return undefined;
  const clean = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');
  return text.split(' ').find((w) => clean(w) === clean(hl));
};

interface Ctx { solids: Solid[]; water: Box[]; obstacles: Box[] }
/** The plan an actor gets in the final episode (scripted actors may wade through ponds; mobs walk around them). */
const actorPlan = (a: { kind: ActorKind; start: Vec2; face: number; steps: Step[] }, ctx: Ctx, mob = false): ActorPlan =>
  resolvePlan(a.kind, { start: a.start, face: a.face, steps: a.steps, obstacles: ctx.obstacles, avoidWater: mob }, ctx.solids, ctx.water);

interface Timeline {
  states: Record<string, AState>;
  beats: { from: number; to: number; script: ScriptBeat }[];
  frames: number;
  ambient: { f: number; event: string }[];
  errors: string[];
  warnings: string[];
}

const build = (script: McScript, placed: Placed[], extra: number, ctx: Ctx): Timeline => {
  const errors: string[] = [], warnings: string[] = [];
  const byId = new Map(placed.map((p) => [p.spec.id, p]));
  const heroId = script.hero ?? 'steve';
  const states: Record<string, AState> = {};
  const mk = (id: string, kind: ActorKind, at: Vec2, skin?: string): AState =>
    (states[id] = { id, kind, skin, start: at, face: Math.PI / 2, steps: [], pos: at, at: null, acts: 0, tags: [], lenAt: -1, lenVal: 0 });
  const first = placed[0];
  mk(heroId, 'player', first ? first.stand : [3.2, Z]);
  states[heroId].at = first?.spec.id ?? null;
  const castAt: Record<string, number> = {}; // cast members sharing a station start side by side, not on the same spot
  (script.cast ?? []).forEach((c) => {
    if (states[c.id]) return;
    if (!KINDS[c.kind]) return errors.push(`cast "${c.id}": unknown kind "${c.kind}"`);
    const st = c.at ? byId.get(c.at) : undefined;
    if (c.at && !st) errors.push(`cast "${c.id}": unknown station "${c.at}"`);
    const base = st ?? first;
    const k = base ? (castAt[base.spec.id] = (castAt[base.spec.id] ?? -1) + 1) : 0;
    const spot: Vec2 = base ? sideSpot(base) : [4.4, Z - 1.0];
    mk(c.id, c.kind, [spot[0] + (base?.spec.type === 'library' ? 1 : -1) * k * 0.95, spot[1] + (k % 2 ? 0.55 : 0)], skinTexture(c.kind, c.skin));
  });

  const len = (a: AState) => {
    if (a.lenAt !== a.steps.length) {
      a.lenVal = planTrack(actorPlan({ ...a, steps: [...a.steps, { t: 'wait', frames: 0 }] }, ctx), 1).marks[a.steps.length];
      a.lenAt = a.steps.length;
    }
    return a.lenVal;
  };
  /** The hero never stands frozen: a long gap in a beat is filled with something that fits the line (look up the thing, walk a little, read, show it). */
  const lifePad = (a: AState, E: number, text: string, bi: number) => {
    const gap = E - len(a);
    if (gap < 80) return padTo(a, E);
    const t = text.toLowerCase();
    const reading = /\b(book|books|read|reads|document|documents|docs|page|pages|text|file|files)\b/.test(t);
    const walking = /\b(walk|walks|far|distant|search|searching|wait|waits|waiting|slow|slower|fetch|fetching)\b/.test(t);
    if (reading) {
      a.steps.push({ t: 'wait', frames: 14 }, { t: 'act', kind: 'read', frames: Math.min(90, gap - 30) });
      a.tags.push({ idx: a.acts++, kind: 'read', extra: 'hand|item_book' });
    } else if (walking && gap >= 110) {
      const [px, pz] = a.pos;
      a.steps.push({ t: 'walk', to: [px - 0.8, pz], speed: 1.8 }, { t: 'walk', to: [px, pz], speed: 1.8 });
    } else {
      const [px, pz] = a.pos; // nothing specific to do: look around the scene (towards the village, then back at what he was working on)
      a.steps.push({ t: 'wait', frames: Math.max(8, Math.floor(gap / 3)) }, { t: 'face', to: [px + 1.5, pz - 2], frames: 28 }, { t: 'wait', frames: 20 }, { t: 'face', to: [px - 0.5, pz - 2], frames: 28 });
    }
    void bi;
    padTo(a, E);
  };
  const padTo = (a: AState, f: number) => {
    const n = f - len(a);
    if (n > 0) a.steps.push({ t: 'wait', frames: n });
  };
  const ambient: { f: number; event: string }[] = [];
  const beatsOut: Timeline['beats'] = [];

  script.beats.forEach((b, bi) => {
    const S = Math.max(0, ...Object.values(states).map(len));
    Object.values(states).forEach((a) => padTo(a, S));

    const scripted = b.actions ?? [];
    const heroIdle = scripted.every((a) => (a.actor && a.actor !== heroId) || a.act === 'look' || a.act === 'wait');
    const actionsNow: ActionSpec[] = heroIdle ? [...scripted, ...fillerFor(b, bi, placed, states[heroId].at)] : scripted;
    actionsNow.forEach((ac, ai) => {
      const who = states[ac.actor ?? heroId];
      const where = `beat ${bi + 1} action ${ai + 1} (${ac.act})`;
      if (!who) return errors.push(`${where}: unknown actor "${ac.actor}"`);
      const humanoid = isHumanoid(who.kind);
      const station = (type: StationType): Placed | null => {
        let st = ac.target ? byId.get(ac.target) : undefined;
        if (ac.target && !st) {
          errors.push(`${where}: unknown station "${ac.target}"`);
          return null;
        }
        if (!st) st = who.at ? byId.get(who.at) : undefined;
        if (!st || st.spec.type !== type) st = placed.find((p) => p.spec.type === type && (type !== 'mine' || p.mines < 2) && (type !== 'chest' || p.opens < 1));
        if (!st) {
          errors.push(`${where}: needs a station of type ${type}`);
          return null;
        }
        return st;
      };
      // the hero uses the station's spot; other actors stand beside it (behind, away from the camera) so nobody shares a hitbox
      const standOf = (st: Placed): Vec2 => (who.id === heroId ? st.stand : sideSpot(st));
      const goTo = (st: Placed, speed?: number) => {
        const to = standOf(st);
        if (who.at !== st.spec.id || Math.hypot(who.pos[0] - to[0], who.pos[1] - to[1]) > 0.6) {
          who.steps.push({ t: 'walk', to, speed });
          who.pos = to;
        }
        who.at = st.spec.id;
        if (st.spec.type === 'pen' && st.mobs[0]) ambient.push({ f: S + 24, event: `entity.${st.mobs[0].kind}.ambient` });
      };
      const faceTo = (p: Vec2) => who.steps.push({ t: 'face', to: p, dir: 'front' });
      const act = (kind: ActKind, frames: number, opts: Partial<Extract<Step, { t: 'act' }>> = {}, tagStation?: string, tagExtra?: string) => {
        who.steps.push({ t: 'act', kind, frames, ...opts });
        who.tags.push({ idx: who.acts++, kind, station: tagStation, extra: tagExtra });
      };
      /** Walk next to a station or actor, face it and hand an item over (the item flies to it). Returns false for an unknown target. */
      const handOver = (targetId: string | undefined, item: string): boolean => {
        const st = targetId ? byId.get(targetId) : undefined;
        const other = targetId ? states[targetId] : undefined;
        if (!st && !other) return false;
        let to: Vec2;
        if (st) {
          goTo(st);
          to = st.mobs[0] ? st.mobs[0].at : st.focus;
        } else {
          to = other!.pos;
          const dx = to[0] - who.pos[0], dz = to[1] - who.pos[1], dist = Math.hypot(dx, dz);
          if (dist > 1.6) {
            const stand: Vec2 = [to[0] - (dx / dist) * 1.2, to[1] - (dz / dist) * 1.2];
            who.steps.push({ t: 'walk', to: stand });
            who.pos = stand;
          }
        }
        faceTo(to);
        act('reach', 30, {}, undefined, `give|${item}|${to[0].toFixed(2)}|${to[1].toFixed(2)}`);
        return true;
      };
      const cross = (st: Placed, swim: boolean) => {
        if (swim) who.steps.push({ t: 'walk', to: st.swimTo!, swim: true });
        who.steps.push({ t: 'walk', to: st.after! });
        who.pos = st.after!;
      };

      switch (ac.act) {
        case 'go':
        case 'sprint': {
          const st = ac.target ? byId.get(ac.target) : undefined;
          if (!st) return errors.push(`${where}: "go" needs a target station`);
          goTo(st, ac.act === 'sprint' ? 5.6 : undefined);
          break;
        }
        case 'mine': {
          if (!humanoid) return errors.push(`${where}: only humanoids can mine`);
          const st = station('mine');
          if (!st) return;
          if (st.mines >= 2) return warnings.push(`${where}: station "${st.spec.id}" only has 2 vein layers; ignored`);
          goTo(st);
          faceTo([st.x + 1.5, Z]);
          const swings = Math.max(1, Math.min(6, ac.swings ?? 6));
          const cycle = ac.fast ? 11 : 16;
          act('mine', swings * cycle + 2, { cycle }, st.spec.id, String(st.mines++));
          break;
        }
        case 'open_chest': {
          const st = station('chest');
          if (!st) return;
          if (st.opens >= 1) return warnings.push(`${where}: chest "${st.spec.id}" already opened once; ignored`);
          goTo(st);
          faceTo(st.focus);
          st.opens++;
          act('reach', 40, {}, st.spec.id);
          break;
        }
        case 'swim': {
          const st = station('pond');
          if (!st) return;
          goTo(st);
          cross(st, true);
          break;
        }
        case 'open_door': {
          const st = station('door');
          if (!st) return;
          goTo(st);
          faceTo(st.focus);
          act('reach', 36, {}, st.spec.id);
          cross(st, false);
          break;
        }
        case 'climb': {
          if (!humanoid) return errors.push(`${where}: only humanoids can climb`);
          const st = station('ladder');
          if (!st) return;
          goTo(st);
          faceTo(st.focus);
          act('climb', 52, { rise: 3.4 }, st.spec.id);
          break;
        }
        case 'wave':
          act('wave', fr(ac.seconds ?? 2));
          break;
        case 'nod':
        case 'shake': {
          if (!humanoid) return errors.push(`${where}: only humanoids can ${ac.act}`);
          act(ac.act, fr(ac.seconds ?? 1.3));
          break;
        }
        case 'point': {
          if (!humanoid) return errors.push(`${where}: only humanoids can point`);
          const st = ac.target ? byId.get(ac.target) : undefined;
          const other = ac.target ? states[ac.target] : undefined;
          if (ac.target && !st && !other) return errors.push(`${where}: unknown target "${ac.target}"`);
          if (st || other) faceTo(st ? st.focus : other!.pos);
          act('point', fr(ac.seconds ?? 1.8));
          break;
        }
        case 'read': {
          if (!humanoid) return errors.push(`${where}: only humanoids can read`);
          act('read', fr(ac.seconds ?? 2.6), {}, undefined, 'hand|item_book');
          break;
        }
        case 'pace': { // a short walk away and back along the path: waiting, wandering, looking for something
          if (!humanoid) return errors.push(`${where}: only humanoids can pace`);
          const [px, pz] = who.pos;
          const a: Vec2 = [px - 1.1, pz]; // always back along the path (the stations' props are on the other side)
          who.steps.push({ t: 'walk', to: a, speed: 2.4 }, { t: 'walk', to: [px, pz], speed: 2.4 });
          break;
        }
        case 'take_book':
        case 'put_book': {
          if (!humanoid) return errors.push(`${where}: only humanoids can handle books`);
          const st = station('library');
          if (!st) return;
          goTo(st);
          faceTo(st.focus);
          if (ac.act === 'take_book') act('reach', 30, {}, st.spec.id, 'take|item_book');
          else act('reach', 30, {}, st.spec.id, `give|item_book|${st.focus[0].toFixed(2)}|${st.focus[1].toFixed(2)}`);
          break;
        }
        case 'cheer':
          if (!humanoid) return errors.push(`${where}: only humanoids can cheer`);
          act('cheer', fr(ac.seconds ?? 1.6));
          break;
        case 'give': {
          if (!humanoid) return errors.push(`${where}: only humanoids can give`);
          if (!handOver(ac.target, ac.item ?? 'item_emerald')) errors.push(`${where}: "give" needs a target station or actor`);
          break;
        }
        case 'fetch': { // take an item from one place and bring it to another: walk, grab, walk, hand it over
          if (!humanoid) return errors.push(`${where}: only humanoids can fetch`);
          const src = ac.target ? byId.get(ac.target) : undefined;
          if (!src || !ac.to) return errors.push(`${where}: "fetch" needs target (where the item is taken) and to (where it goes)`);
          const item = ac.item ?? (src.spec.type === 'library' ? 'item_book' : 'item_emerald');
          goTo(src);
          faceTo(src.focus);
          act('reach', 24, {}, src.spec.id, `take|${item}`);
          if (!handOver(ac.to, item)) errors.push(`${where}: unknown destination "${ac.to}"`);
          break;
        }
        case 'show': { // hold an item up to the viewer ("this is the data")
          if (!humanoid) return errors.push(`${where}: only humanoids can show`);
          act('show', fr(ac.seconds ?? 2), {}, undefined, `hand|${ac.item ?? 'item_book'}`);
          break;
        }
        case 'search': { // walk slowly along a station looking for something
          if (!humanoid) return errors.push(`${where}: only humanoids can search`);
          const st = ac.target ? byId.get(ac.target) : undefined;
          if (ac.target && !st) return errors.push(`${where}: unknown station "${ac.target}"`);
          if (st) { goTo(st); faceTo(st.focus); }
          const [px, pz] = who.pos;
          who.steps.push({ t: 'walk', to: [px + 1.8, pz], speed: 1.5 }, { t: 'face', to: st ? st.focus : [px + 1.8, pz - 1], frames: 20 }, { t: 'walk', to: [px, pz], speed: 1.5 }, { t: 'face', to: st ? st.focus : [px, pz - 1], frames: 20 });
          break;
        }
        case 'jump':
          act('jump', 20);
          break;
        case 'use':
          act('use', fr(ac.seconds ?? 1.6));
          break;
        case 'attack': {
          if (!humanoid) return errors.push(`${where}: only humanoids can attack`);
          const st = station('pen');
          if (!st) return;
          goTo(st);
          faceTo(st.mobs[0] ? st.mobs[0].at : st.focus);
          act('attack', fr(ac.seconds ?? 2));
          break;
        }
        case 'look': {
          const st = ac.target ? byId.get(ac.target) : undefined;
          const other = ac.target ? states[ac.target] : undefined;
          if (!st && !other) return errors.push(`${where}: "look" needs a target station or actor`);
          who.steps.push({ t: 'face', to: st ? st.focus : other!.pos, frames: 24 });
          break;
        }
        case 'wait':
          who.steps.push({ t: 'wait', frames: fr(ac.seconds ?? 1) });
          break;
        default:
          errors.push(`${where}: unknown action "${ac.act}"`);
      }
    });

    const minF = Math.max(fr(b.seconds ?? 0), readFrames(b.text)) + extra;
    const E = Math.max(S + minF, ...Object.values(states).map(len));
    Object.values(states).forEach((a) => (a.id === heroId ? lifePad(a, E, b.text, bi) : padTo(a, E)));
    beatsOut.push({ from: S, to: E, script: b });
    if (b.text.length > 70) warnings.push(`beat ${bi + 1}: subtitle has ${b.text.length} characters (aim for <= 60)`);
    if (b.sound) ambient.push({ f: S + 8, event: b.sound });
  });

  const frames = beatsOut.length ? beatsOut[beatsOut.length - 1].to + 20 : 0;
  if (beatsOut.length) beatsOut[beatsOut.length - 1].to = frames;
  return { states, beats: beatsOut, frames, ambient, errors, warnings };
};

/* ------------------------------ camera planner ------------------------------ */
/**
 * A shot is usable when, over its whole length, the camera stays clear of every actor's hitbox (>= 1 block) and of tall blocks,
 * and no tall block (walls, trees, ladders, door frames) stands between the camera and what it looks at.
 */
const shotIssues = (sh: Shot, tracks: Record<string, Track>, actors: ActorSpec[], tall: Solid[], subject: string) => {
  let bad = 0;
  for (let f = sh.from; f < sh.to; f += 5) if (frameIssue(sh, f, tracks, actors, tall, subject)) bad++;
  return bad;
};
const frameIssue = (sh: Shot, f: number, tracks: Record<string, Track>, actors: ActorSpec[], tall: Solid[], subject: string) => {
  const c = cameraAt([sh], tracks, f);
  const S = tracks[subject];
  const cx = c.pos[0], cz = c.pos[2], sx = S.x[f] - cx, sz = S.z[f] - cz, sl = Math.hypot(sx, sz) || 1;
  for (const a of actors) {
    const T = tracks[a.id], K = KINDS[a.kind];
    const ax = T.x[f] - cx, az = T.z[f] - cz;
    // the subject may come close; anyone else that near fills the frame
    if (c.pos[1] < T.y[f] + K.h + 0.6 && Math.hypot(ax, az) < K.w / 2 + (a.id === subject ? 1.0 : 2.2)) return true;
    if (a.id === subject) continue;
    // another actor standing between the camera and the subject hides it
    const t = (ax * sx + az * sz) / (sl * sl);
    if (t > 0.05 && t < 0.9 && Math.abs(ax * sz - az * sx) / sl < K.w / 2 + 0.25 && T.y[f] + K.h > 0.8) return true;
  }
  for (const s of tall) {
    if (c.pos[1] < s.y1 + 0.2 && inBox(c.pos[0], c.pos[2], s.box, 0.3)) return true;
    if (c.pos[1] < s.y1 + 0.5 && segHitsBox([c.pos[0], c.pos[2]], [c.look[0], c.look[2]], s.box, 0.05)) return true;
  }
  return false;
};

const planShots = (placed: Placed[], tl: Timeline, tracks: Record<string, Track>, actors: ActorSpec[], heroId: string, solids: Solid[]): Shot[] => {
  const byId = new Map(placed.map((p) => [p.spec.id, p]));
  const F = tl.frames;
  const tall = solids.filter((s) => s.y1 >= 1.4);
  // 1. segments: >= 90 frames each (a cut every ~3 s); a beat with a camera hint may start a segment once 60 frames have passed
  type Seg = { from: number; to: number; hint?: ScriptBeat };
  const segs: Seg[] = [];
  tl.beats.forEach((b) => {
    const cur = segs[segs.length - 1];
    const hinted = !!b.script.shot;
    if (!cur || b.from - cur.from >= 90 || (hinted && b.from - cur.from >= 60)) {
      if (cur) cur.to = b.from;
      segs.push({ from: b.from, to: F, hint: hinted ? b.script : undefined });
    } else if (hinted && !cur.hint) cur.hint = b.script;
  });
  if (segs.length > 1 && segs[segs.length - 1].to - segs[segs.length - 1].from < 75) {
    const last = segs.pop()!;
    segs[segs.length - 1].to = last.to;
  }
  if (!segs.length) return [{ from: 0, to: F, p0: [4, 2, 8], p1: [4, 2, 8], l0: [4, 1, 1], l1: [4, 1, 1], fov: 52 }];
  segs[0].from = 0;
  // 2. a segment longer than ~7 s (one beat with a long walk) is split, cutting where the hero starts a new step when possible
  const marks = tl.states[heroId] ? tracks[heroId].marks : [];
  for (let i = 0; i < segs.length; i++) {
    const sg = segs[i];
    if (sg.to - sg.from <= 210) continue;
    const n = Math.max(2, Math.round((sg.to - sg.from) / 150));
    let cut = sg.from + Math.round((sg.to - sg.from) / n);
    const snap = marks.filter((m) => Math.abs(m - cut) <= 40 && m - sg.from >= 90 && sg.to - m >= 90).sort((a, b) => Math.abs(a - cut) - Math.abs(b - cut))[0];
    if (snap != null) cut = snap;
    segs.splice(i + 1, 0, { from: cut, to: sg.to });
    sg.to = cut;
  }

  let walkCount = 0, still = 0;
  const planOne = (sg: Seg, si: number): Shot => {
    const focusActor = sg.hint?.focus && tracks[sg.hint.focus] ? sg.hint.focus : heroId;
    const T = tracks[focusActor];
    const f0 = sg.from, f1 = Math.max(sg.from, sg.to - 1), fm = Math.round((f0 + f1) / 2);
    const [x0, z0] = T.pos(f0), [x1, z1] = T.pos(f1);
    const disp = Math.hypot(x1 - x0, z1 - z0);
    const has = (kind: ActKind) => T.acts.some((a) => a.kind === kind && a.start < sg.to && a.start + a.frames > sg.from);
    const swimming = Array.from({ length: Math.ceil((sg.to - sg.from) / 6) }, (_, k) => T.swim(sg.from + k * 6)).filter((v) => v > 0.5).length > 3;
    const side = si % 2 ? -1 : 1;
    const dir = Math.sign(x1 - x0) || 1;
    const base = { from: sg.from, to: sg.to };
    /** First clean candidate, otherwise the one with the fewest problem frames (candidates are listed best-looking first). */
    const pick = (cands: Shot[]) => {
      let best = cands[0], bestBad = Infinity;
      for (const c of cands) {
        const bad = shotIssues(c, tracks, actors, tall, focusActor);
        if (bad === 0) return c;
        if (bad < bestBad) { best = c; bestBad = bad; }
      }
      return best;
    };
    let style: ShotStyle | 'climb' | 'swim' | undefined = sg.hint?.shot;
    if (!style) {
      if (has('climb')) style = 'climb';
      else if (swimming) style = 'swim';
      else if (disp >= 5) style = walkCount++ === 0 ? 'pan' : 'follow';
      else if (si === 0 && placed.some((p) => p.signAt)) style = 'sign';
      else style = (['orbit', 'wide', 'close'] as ShotStyle[])[still++ % 3];
    }
    if (style === 'climb') return { ...base, p0: [-1.4, 1.8, 4.0], p1: [-1.6, 3.9, 4.0], l0: [0.4, 1.4, 0], l1: [0.4, 3.5, 0], fov: 54, follow: focusActor }; // side-on: hands and rungs visible
    if (style === 'swim') return { ...base, p0: [1.0, 1.4, 4.8], p1: [2.2, 1.0, 4.2], l0: [0.8, 0.4, 0], l1: [1.2, 0.2, 0], fov: 56, follow: focusActor };
    if (style === 'follow')
      return pick([
        { ...base, p0: [dir * 4.6, 1.3, 3.3], p1: [dir * 3.6, 1.1, 2.4], l0: [0, 1, 0], l1: [0, 1, 0], fov: 58, follow: focusActor },
        { ...base, p0: [dir * 3.0, 1.7, 4.8], p1: [dir * 2.4, 1.5, 4.2], l0: [0, 1, 0], l1: [0, 1, 0], fov: 56, follow: focusActor },
        { ...base, p0: [dir * 1.0, 2.6, 6.0], p1: [dir * 0.6, 2.4, 5.4], l0: [0, 1, 0], l1: [0, 1, 0], fov: 54, follow: focusActor },
        { ...base, p0: [dir * 4.4, 1.5, 0.7], p1: [dir * 3.6, 1.4, 0.6], l0: [0, 1, 0], l1: [0, 1, 0], fov: 56, follow: focusActor }, // along the path (doorways, walls on the side)
        { ...base, p0: [-dir * 3.8, 1.9, 0.9], p1: [-dir * 3.2, 1.8, 0.8], l0: [dir * 1.5, 1, 0], l1: [dir * 1.5, 1, 0], fov: 56, follow: focusActor },
      ]);
    if (style === 'pan')
      return pick([
        { ...base, p0: [x0 + 1.8, 2.1, z0 + 5.3], p1: [x1 + 0.9, 2.0, z1 + 5.5], l0: [x0, 1.1, z0], l1: [x1 - 0.4, 1.1, z1 - 0.4], fov: 52, eased: true },
        { ...base, p0: [x0 + 1.2, 3.0, z0 + 7.0], p1: [x1 + 0.6, 2.8, z1 + 7.2], l0: [x0, 1.1, z0], l1: [x1 - 0.4, 1.1, z1 - 0.4], fov: 52, eased: true },
      ]);
    if (style === 'sign') {
      const st = (sg.hint?.focus ? byId.get(sg.hint.focus) : undefined) ?? placed.find((p) => p.signAt) ?? placed[0];
      const s = st?.signAt ?? st?.focus ?? [x0, z0];
      return pick([
        { ...base, p0: [s[0] - 0.2, 1.7, s[1] + 7.0], p1: [s[0] + 0.3, 1.6, s[1] + 6.2], l0: [s[0] + 0.6, 1.25, s[1]], l1: [s[0] + 0.7, 1.25, s[1]], fov: 50 }, // far enough to keep a hero beside the sign in frame
        { ...base, p0: [s[0] - 1.4, 2.0, s[1] + 6.2], p1: [s[0] - 0.8, 1.9, s[1] + 5.6], l0: [s[0] + 0.6, 1.2, s[1]], l1: [s[0] + 0.7, 1.2, s[1]], fov: 50 },
      ]);
    }
    // orbit / wide / close: framed from the subject's front three-quarter side (never its back), on the camera side of the world (+z)
    const st = sg.hint?.focus ? byId.get(sg.hint.focus) : undefined;
    const [hx, hz] = T.pos(fm);
    const nearest = placed.map((p) => ({ p, d: Math.hypot(p.focus[0] - hx, p.focus[1] - hz) })).sort((a, b) => a.d - b.d)[0];
    const target = st ? st.focus : nearest && nearest.d < 4.5 ? nearest.p.focus : undefined; // the station the subject is at during this shot
    // working on something (mining, attacking, opening): side-on, aimed between the actor and its target, never tighter than ~4.6 blocks
    // (a vertical 9:16 frame is narrow: a close shot would leave the target outside)
    const working = has('mine') || has('attack') || has('reach');
    // aim a little towards the target, but never more than 0.7 blocks off the subject: the subject has to stay in frame
    const pull = working ? 0.45 : style === 'close' ? 0.15 : 0.35;
    const tx = target ? (target[0] - hx) * pull : 0, tz = target ? (target[1] - hz) * pull : 0;
    const k = Math.min(1, 0.7 / (Math.hypot(tx, tz) || 1));
    const lx = hx + tx * k, lz = hz + tz * k;
    const face = T.face[fm];
    const [D0, H, fov, swing] = style === 'wide' ? [8.6, 2.6, 54, 0.12] : style === 'low' ? [3.9, 0.75, 50, 0.16] : style === 'close' ? [3.6, 1.5, 46, 0.18] : [5.8, 1.7, 52, 0.5];
    const D = working ? Math.max(D0, 6) : D0;
    const order = working ? [1.4, -1.4, 0.8, -0.8, 1.8, -1.8] : [0.8, -0.8, 1.3, -1.3, 0.45, -0.45];
    const az = order.map((k) => face + k * side).map((a) => Math.atan2(Math.sin(a), Math.cos(a)));
    const angles = [...az.filter((a) => Math.cos(a) > 0.05), 0.5 * side, -0.5 * side, 0];
    const cands = [1, 1.5, 2.1].flatMap((k) => // further back only if nothing closer is clean (crowded pens, walls)
      angles.map((a): Shot => {
        const at = (da: number, d: number, h: number): [number, number, number] => [lx + Math.sin(a + da) * d, h, lz + Math.cos(a + da) * d];
        const d = Math.min(D * k, 10), h = H + (k - 1) * 0.8;
        return { ...base, p0: at(-swing, d, h), p1: at(swing, d * 0.94, h + (style === 'wide' ? 0.5 : 0.1)), l0: [lx, style === 'low' ? 1.45 : 1.15, lz], l1: [lx, style === 'low' ? 1.5 : 1.1, lz], fov };
      }),
    );
    return pick(cands);
  };
  /** The camera must never lag behind: a shot whose subject moves more than ~0.4 blocks becomes a follow shot (the camera and the point it looks at
   *  move with the actor, keeping the framing the planner chose at the middle of the shot). Still subjects keep a fixed camera. */
  const keepUp = (sh: Shot, sg: Seg): Shot => {
    if (sh.follow) return sh;
    const focusActor = sg.hint?.focus && tracks[sg.hint.focus] ? sg.hint.focus : heroId;
    const T = tracks[focusActor];
    const fm = Math.round((sh.from + sh.to - 1) / 2);
    const [rx, rz] = T.pos(fm);
    let dev = 0;
    for (let f = sh.from; f < sh.to; f += 3) dev = Math.max(dev, Math.hypot(T.x[Math.min(f, T.x.length - 1)] - rx, T.z[Math.min(f, T.z.length - 1)] - rz));
    if (dev < 0.4) return sh;
    // keep the geometry between camera and look-at point, but put the look-at point on the actor (at most 0.7 blocks off, as the planner allows)
    const rel = (p: [number, number, number], l: [number, number, number]): { p: [number, number, number]; l: [number, number, number] } => {
      let lx = l[0] - rx, lz = l[2] - rz;
      const n = Math.hypot(lx, lz);
      if (n > 0.7) { lx *= 0.7 / n; lz *= 0.7 / n; }
      return { p: [p[0] - l[0] + lx, p[1], p[2] - l[2] + lz], l: [lx, l[1], lz] };
    };
    if (sh.eased) { // a pan was designed to travel with the walk: as a follow shot it keeps one constant framing (the average of its start and end)
      const avg = (a: [number, number, number], b: [number, number, number]): [number, number, number] => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2];
      const r = rel(avg(sh.p0, sh.p1), avg(sh.l0, sh.l1));
      return { ...sh, follow: focusActor, eased: false, p0: r.p, p1: r.p, l0: r.l, l1: r.l };
    }
    const a = rel(sh.p0, sh.l0), b = rel(sh.p1, sh.l1);
    return { ...sh, follow: focusActor, p0: a.p, p1: b.p, l0: a.l, l1: b.l };
  };
  return segs.map((sg, si) => keepUp(planOne(sg, si), sg));
};

/* ------------------------------ compile ------------------------------ */
export const compileScript = (script: McScript): CompileResult => {
  const fail = (errors: string[]): CompileResult => ({ spec: null, errors, warnings: [], frames: 0, seconds: 0 });
  const errs: string[] = [];
  if (!script.stations?.length) errs.push('the script needs at least one station');
  if (!script.beats?.length) errs.push('the script needs at least one beat');
  const ids = new Set<string>();
  (script.stations ?? []).forEach((s) => {
    if (!STATION_TYPES.includes(s.type)) errs.push(`station "${s.id}": unknown type "${s.type}"`);
    if (ids.has(s.id)) errs.push(`duplicate station id "${s.id}"`);
    ids.add(s.id);
    if (s.type === 'mine') (s.ores ?? []).forEach((o) => !ORES.includes(o) && errs.push(`station "${s.id}": unknown ore "${o}"`));
    if (s.type === 'stall') (s.items ?? []).forEach((it) => !STALL_ITEMS.includes(it) && errs.push(`station "${s.id}": unknown stall item "${it}"`));
    if (s.type === 'pen') (s.kinds ?? []).forEach((k) => !PEN_KINDS.includes(k) && errs.push(`station "${s.id}": unknown mob "${k}"`));
  });
  (script.cast ?? []).forEach((c) => {
    if (c.skin && !skinTexture(c.kind, c.skin)) errs.push(`cast "${c.id}": unknown skin "${c.skin}" for ${c.kind} (players: ${PLAYER_SKINS.join(', ')}; villagers: ${PROFESSIONS.join(', ')})`);
  });
    (script.stations ?? []).forEach((s) => s.keeper && !PROFESSIONS.includes(s.keeper) && errs.push(`station "${s.id}": unknown keeper profession "${s.keeper}"`));
  (script.beats ?? []).forEach((b, bi) => (b.actions ?? []).forEach((a) => (a.act === 'give' || a.act === 'fetch' || a.act === 'show') && a.item && !STALL_ITEMS.includes(a.item) && errs.push(`beat ${bi + 1}: unknown give item "${a.item}"`)));
  const hasStall = (id?: string) => (script.stations ?? []).some((s) => s.type === 'stall' && (!id || s.id === id));
  (script.beats ?? []).forEach((b, bi) => {
    if (!b.stock && !b.tag) return;
    if (!hasStall(b.stall)) errs.push(`beat ${bi + 1}: stock/tag needs a stall station${b.stall ? ` "${b.stall}"` : ''}`);
    (b.stock ?? []).forEach((it) => !STALL_ITEMS.includes(it) && errs.push(`beat ${bi + 1}: unknown stock item "${it}"`));
    if (b.tag && (!b.tag.now || b.tag.now.length > 12 || (b.tag.was?.length ?? 0) > 12)) errs.push(`beat ${bi + 1}: tag texts need 1-12 characters`);
    if (b.tag?.icon && !STALL_ITEMS.includes(b.tag.icon)) errs.push(`beat ${bi + 1}: unknown tag icon "${b.tag.icon}"`);
  });
  if (errs.length) return fail(errs);

  const placed0 = placeStations(script.stations);
  const fresh = () => placed0.map((p) => ({ ...p, mines: 0, opens: 0 })); // build() counts mines / chest openings on its copy
  const world = makeWorld(placed0);
  const houses = makeHouses(placed0, world);
  const staticProps = [...layoutProps(placed0), ...houses];
  if (script.time && script.time !== 'day') { // torches beside signs and on the front posts of stalls, warm light baked into the terrain around them
    world.time = script.time;
    world.torches = staticProps.flatMap((p): [number, number, number][] =>
      p.type === 'sign' ? [[p.at[0] + 0.75, 0.62, p.at[1] + 0.25]] : p.type === 'house' ? [[p.at[0] + 0.95, 1.3, p.at[1] + p.d / 2 + 0.2]] : p.type === 'stall' ? [-1.3, 1.3].map((dx): [number, number, number] => [p.at[0] + dx, 1.75, p.at[1] + 0.8]) : [],
    );
  }
  const solids = planningSolids(world, staticProps);
  const ctx: Ctx = { solids, water: pondBoxes(world), obstacles: placed0.flatMap((p) => p.obstacles) };

  // stretch the beats evenly until the video reaches the target length
  const target = fr(script.seconds ?? 20);
  let extra = 0;
  let placed = fresh();
  let tl = build(script, placed, 0, ctx);
  for (let i = 0; i < 8 && tl.frames < target - 8 && !tl.errors.length; i++) {
    extra += Math.ceil((target - tl.frames) / script.beats.length);
    placed = fresh();
    tl = build(script, placed, extra, ctx);
  }
  if (tl.errors.length) return fail(tl.errors);
  const warnings = [...tl.warnings];
  if (tl.frames < target && tl.beats.length) { // never shorter than the target: hold the last beat
    tl.frames = target;
    tl.beats[tl.beats.length - 1].to = target;
  }
  const heroId = script.hero ?? 'steve';
  const frames = tl.frames;

  // actors: scripted ones + pen mobs ambling around their spot (they walk around ponds and solids)
  const actors: ActorSpec[] = Object.values(tl.states).map((a) => ({ id: a.id, kind: a.kind, skin: a.skin, plan: { start: a.start, face: a.face, steps: a.steps, obstacles: ctx.obstacles, avoidWater: false } }));
  placed.flatMap((p) => p.mobs.map((m, j) => ({ id: `${p.spec.id}_${j}`, ...m }))).forEach((m, k) => {
    const steps: Step[] = [{ t: 'wait', frames: 20 + Math.round(rnd(k * 3.1) * 60) }];
    for (let j = 0; j < Math.ceil(frames / 90) + 1; j++) {
      steps.push({ t: 'walk', to: [m.at[0] + (rnd(k * 7.7 + j) - 0.5) * 0.7, m.at[1] + (rnd(k * 3.3 + j * 1.7) - 0.5) * 0.4], speed: 0.9 + rnd(k + j * 2.3) * 0.4 });
      steps.push({ t: 'wait', frames: 30 + Math.round(rnd(k * 1.9 + j * 4.1) * 70) });
    }
    actors.push({ id: m.id, kind: m.kind, skin: m.skin, plan: { start: m.at, face: rnd(k + 1) * 6.28, steps, obstacles: ctx.obstacles, avoidWater: true } });
  });
  const draft: EpisodeSpec = { id: script.id, title: script.title, cta: script.cta, frames, beats: [], shots: [], world, actors, props: staticProps };
  const tracks = buildTracks(draft); // same tracks the episode will render (hitboxes, pushes, knockback included)

  // props that depend on timing
  const tagsAt = (station: string, kind: ActKind) => Object.values(tl.states).flatMap((a) => a.tags.filter((t) => t.station === station && t.kind === kind).map((t) => ({ a, t })));
  const props: PropSpec[] = [];
  placed.forEach((p) => {
    p.props.forEach((pr) => {
      if (pr.type === 'stall') {
        const first = placed.find((q) => q.spec.type === 'stall')?.spec.id;
        const mine = tl.beats.filter((b) => (b.script.stall ?? first) === p.spec.id);
        return props.push({
          ...pr,
          stock: mine.filter((b) => b.script.stock?.length).map((b) => ({ f: b.from, items: b.script.stock!.slice(0, 6) })),
          tags: mine.filter((b) => b.script.tag).map((b) => ({ f: b.from + 6, ...b.script.tag! })),
        });
      }
      if (pr.type !== 'chest') return props.push(pr);
      const tag = tagsAt(p.spec.id, 'reach')[0];
      if (!tag) return props.push({ ...pr, openAt: 99999, closeAt: 99999 }); // nobody opens it: closed chest
      const act = tracks[tag.a.id].acts[tag.t.idx];
      props.push({ ...pr, openAt: act.start + 4, closeAt: act.start + 24 });
    });
    if (p.door != null) {
      const dx = p.door;
      const tag = tagsAt(p.spec.id, 'reach')[0];
      if (tag) {
        const T = tracks[tag.a.id];
        const act = T.acts[tag.t.idx];
        const past = T.x.findIndex((x, f) => f >= act.start && x > dx + 1.4);
        props.push({ type: 'door', at: [dx, Z], rotY: Math.PI / 2, openAt: act.start + 6, closeAt: Math.max(past < 0 ? act.start + 60 : past + 4, act.start + 40) });
      } else props.push({ type: 'door', at: [dx, Z], rotY: Math.PI / 2, openAt: 99999, closeAt: 99999 });
    }
    if (p.spec.type === 'mine') {
      const ores = p.spec.ores?.length ? p.spec.ores : ORES;
      const mined = tagsAt(p.spec.id, 'mine');
      mined.forEach(({ a, t }) => {
        const layer = Number(t.extra);
        props.push({ type: 'vein', actor: a.id, act: a.tags.filter((q) => q.kind === 'mine').findIndex((q) => q.idx === t.idx), x: p.x + 0.8 + layer, cells: MINE_CELLS, ores: MINE_CELLS.map((_, k) => ores[(k + layer * 2) % ores.length]) });
      });
      if (!mined.length) warnings.push(`mine station "${p.spec.id}" is never mined`);
    }
  });
  props.push(...houses);
  placed.forEach((p) => p.spec.type === 'pond' && !tl.beats.some((b) => (b.script.actions ?? []).some((a) => a.act === 'swim' && (!a.target || a.target === p.spec.id))) && warnings.push(`pond "${p.spec.id}" is never crossed`));

  // hand items and hotbar
  const heroT = tracks[heroId];
  const hand: { f: number; item: string }[] = [];
  heroT.acts.filter((a) => TOOL[a.kind]).sort((a, b) => a.start - b.start).forEach((a, i) => {
    const item = TOOL[a.kind]!;
    if (i === 0) hand.push({ f: 0, item });
    else if (hand[hand.length - 1].item !== item) hand.push({ f: Math.max(1, a.start - 12), item });
  });
  const toolAt = (f: number) => [...hand].reverse().find((h) => h.f <= f)?.item ?? '';
  const heroActs = tracks[heroId].acts;
  const bookHand: { f: number; item: string }[] = [];
  tl.states[heroId].tags.forEach((t) => { // items in the hand: held while reading/showing, carried after taking, released when handed over
    const ac = heroActs[t.idx];
    if (!ac || !t.extra) return;
    const [kind, item] = t.extra.split('|');
    if (kind === 'hand') bookHand.push({ f: Math.max(1, ac.start - 8), item }, { f: ac.start + ac.frames, item: toolAt(ac.start + ac.frames) });
    else if (kind === 'take') bookHand.push({ f: ac.start + 12, item });
    else if (kind === 'give') bookHand.push({ f: ac.start + 8, item: toolAt(ac.start + 8) });
  });
  const handAll = [...hand, ...bookHand].sort((x, y) => x.f - y.f);
  actors.find((a) => a.id === heroId)!.hand = handAll.length ? handAll : undefined;
  const baseItems = script.inventory?.items ?? (hand.length ? ['item_diamond_pickaxe', 'item_iron_sword', 'torch'] : []);
  const hotbar = baseItems.length
    ? {
        base: baseItems,
        row2At: script.inventory?.grow_at_beat != null ? tl.beats[Math.min(tl.beats.length - 1, script.inventory.grow_at_beat)]?.from : undefined,
        selected: hand.map((h) => ({ f: h.f, slot: Math.max(0, baseItems.indexOf(h.item)) })),
      }
    : undefined;

  const transfers: Transfer[] = Object.values(tl.states).flatMap((a) =>
    a.tags.filter((t) => t.extra?.startsWith('give|')).map((t) => {
      const [, item, tx, tz] = t.extra!.split('|');
      const act = tracks[a.id].acts[t.idx];
      return { f0: act.start + 8, f1: act.start + 26, from: a.id, to: [Number(tx), Number(tz)] as [number, number], item };
    }),
  );
  const sounds: SoundEvent[] = [...transfers.map((t) => ({ f: t.f1, event: 'entity.item.pickup', vol: 0.7 })), ...tl.ambient.map((a) => ({ f: a.f, event: a.event, vol: 0.7 })), ...tl.beats.filter((b) => b.script.stock?.length).map((b) => ({ f: b.from + 2, event: 'entity.experience_orb.pickup', vol: 0.6 }))];
  const beats: Beat[] = tl.beats.map((b) => ({
    from: b.from, to: b.to, text: b.script.text, hl: tokenFor(b.script.text, b.script.hl),
    words: b.script.words?.length === b.script.text.trim().split(/\s+/).length ? b.script.words.map((w) => ({ s: Math.round(w.s * FPS) + 4, e: Math.round(w.e * FPS) + 4 })) : undefined, // +4 frames: the clip starts 120 ms after the beat
  }));
  const shots = planShots(placed, tl, tracks, actors, heroId, solids);

  const spec: EpisodeSpec = { id: script.id, title: script.title, cta: script.cta, frames, surface: script.surface ?? 'grass', beats, world, actors, props, hotbar, shots, sounds, transfers };
  if (Math.abs(frames - target) > 45) warnings.push(`length is ${(frames / FPS).toFixed(1)} s, target ${(target / FPS).toFixed(1)} s`);
  Object.values(tl.states).forEach((a) => {
    const k = a.tags.findIndex((t) => t.kind === 'climb');
    if (k >= 0 && a.tags.length > k + 1) warnings.push(`${a.id}: acts after climbing happen in the air; put the ladder last`);
  });
  return { spec, errors: [], warnings, frames, seconds: frames / FPS };
};
