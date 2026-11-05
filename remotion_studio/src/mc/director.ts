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
import { ActorSpec, Beat, EpisodeSpec, buildTracks, pondBoxes, resolvePlan } from './episode';
import { ActorKind, KINDS, isHumanoid } from './kinds';
import type { Ore, PropSpec } from './props';
import type { SoundEvent } from './sfx';
import { planningSolids } from './solids';
import type { WorldSpec } from './world';

/* ------------------------------ script format ------------------------------ */
export type StationType = 'sign' | 'mine' | 'chest' | 'pond' | 'door' | 'ladder' | 'pen';
export type PenKind = 'pig' | 'cow' | 'chicken' | 'sheep' | 'villager' | 'spider' | 'zombie' | 'skeleton' | 'creeper';
export interface StationSpec {
  id: string;
  type: StationType;
  label?: string[]; // text of a sign next to the station (max 4 lines, ~12 chars each); for type 'sign' this is the whole point
  ores?: Ore[]; // mine: ores of the vein, in breaking order
  kinds?: PenKind[]; // pen: mobs standing there
  gap?: number; // free blocks before this station (default 8)
}
export type ActName = 'go' | 'sprint' | 'mine' | 'open_chest' | 'swim' | 'open_door' | 'climb' | 'wave' | 'jump' | 'use' | 'attack' | 'look' | 'wait';
export interface ActionSpec {
  actor?: string; // default: the hero
  act: ActName;
  target?: string; // station id (or actor id for 'look')
  seconds?: number; // duration for wave / use / attack / wait
  swings?: number; // mine: blocks to break (1-6, default 6)
  fast?: boolean; // mine: quicker swings (more "power")
}
export type ShotStyle = 'sign' | 'close' | 'orbit' | 'wide' | 'follow' | 'pan';
export interface ScriptBeat {
  text: string; // subtitle (Spanish or English), <= 60 characters recommended
  hl?: string; // one word of the text to highlight
  seconds?: number; // minimum on-screen time
  shot?: ShotStyle; // camera hint for the shot that starts here
  focus?: string; // station id (for 'sign'/'close') or actor id the camera looks at
  actions?: ActionSpec[]; // run in parallel for different actors, in order for the same actor
  sound?: string; // extra game sound event at the start of the beat, e.g. 'entity.pig.ambient'
}
export interface CastSpec { id: string; kind: ActorKind; at?: string; skin?: string }
export interface McScript {
  id: string;
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
const STATION_TYPES: StationType[] = ['sign', 'mine', 'chest', 'pond', 'door', 'ladder', 'pen'];
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
  mobs: { kind: PenKind; at: Vec2 }[];
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
  (script.cast ?? []).forEach((c) => {
    if (states[c.id]) return;
    if (!KINDS[c.kind]) return errors.push(`cast "${c.id}": unknown kind "${c.kind}"`);
    const st = c.at ? byId.get(c.at) : undefined;
    if (c.at && !st) errors.push(`cast "${c.id}": unknown station "${c.at}"`);
    const base = st ?? first;
    mk(c.id, c.kind, base ? [base.stand[0] - 0.7, Z - 1.0] : [4.4, Z - 1.0], c.skin);
  });

  const len = (a: AState) => {
    if (a.lenAt !== a.steps.length) {
      a.lenVal = planTrack(actorPlan({ ...a, steps: [...a.steps, { t: 'wait', frames: 0 }] }, ctx), 1).marks[a.steps.length];
      a.lenAt = a.steps.length;
    }
    return a.lenVal;
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

    (b.actions ?? []).forEach((ac, ai) => {
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
      const standOf = (st: Placed): Vec2 => (who.id === heroId ? st.stand : [st.stand[0] - 0.7, st.stand[1] - 1.0]);
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
    Object.values(states).forEach((a) => padTo(a, E));
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
  return segs.map((sg, si): Shot => {
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
    const [D0, H, fov, swing] = style === 'wide' ? [8.6, 2.6, 54, 0.12] : style === 'close' ? [3.6, 1.5, 46, 0.18] : [5.8, 1.7, 52, 0.5];
    const D = working ? Math.max(D0, 6) : D0;
    const order = working ? [1.4, -1.4, 0.8, -0.8, 1.8, -1.8] : [0.8, -0.8, 1.3, -1.3, 0.45, -0.45];
    const az = order.map((k) => face + k * side).map((a) => Math.atan2(Math.sin(a), Math.cos(a)));
    const angles = [...az.filter((a) => Math.cos(a) > 0.05), 0.5 * side, -0.5 * side, 0];
    const cands = [1, 1.5, 2.1].flatMap((k) => // further back only if nothing closer is clean (crowded pens, walls)
      angles.map((a): Shot => {
        const at = (da: number, d: number, h: number): [number, number, number] => [lx + Math.sin(a + da) * d, h, lz + Math.cos(a + da) * d];
        const d = Math.min(D * k, 10), h = H + (k - 1) * 0.8;
        return { ...base, p0: at(-swing, d, h), p1: at(swing, d * 0.94, h + (style === 'wide' ? 0.5 : 0.1)), l0: [lx, 1.15, lz], l1: [lx, 1.1, lz], fov };
      }),
    );
    return pick(cands);
  });
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
    if (s.type === 'pen') (s.kinds ?? []).forEach((k) => !PEN_KINDS.includes(k) && errs.push(`station "${s.id}": unknown mob "${k}"`));
  });
  if (errs.length) return fail(errs);

  const placed0 = placeStations(script.stations);
  const fresh = () => placed0.map((p) => ({ ...p, mines: 0, opens: 0 })); // build() counts mines / chest openings on its copy
  const world = makeWorld(placed0);
  const staticProps = layoutProps(placed0);
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
    actors.push({ id: m.id, kind: m.kind, plan: { start: m.at, face: rnd(k + 1) * 6.28, steps, obstacles: ctx.obstacles, avoidWater: true } });
  });
  const draft: EpisodeSpec = { id: script.id, title: script.title, cta: script.cta, frames, beats: [], shots: [], world, actors, props: staticProps };
  const tracks = buildTracks(draft); // same tracks the episode will render (hitboxes, pushes, knockback included)

  // props that depend on timing
  const tagsAt = (station: string, kind: ActKind) => Object.values(tl.states).flatMap((a) => a.tags.filter((t) => t.station === station && t.kind === kind).map((t) => ({ a, t })));
  const props: PropSpec[] = [];
  placed.forEach((p) => {
    p.props.forEach((pr) => {
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
  placed.forEach((p) => p.spec.type === 'pond' && !tl.beats.some((b) => (b.script.actions ?? []).some((a) => a.act === 'swim' && (!a.target || a.target === p.spec.id))) && warnings.push(`pond "${p.spec.id}" is never crossed`));

  // hand items and hotbar
  const heroT = tracks[heroId];
  const hand: { f: number; item: string }[] = [];
  heroT.acts.filter((a) => TOOL[a.kind]).sort((a, b) => a.start - b.start).forEach((a, i) => {
    const item = TOOL[a.kind]!;
    if (i === 0) hand.push({ f: 0, item });
    else if (hand[hand.length - 1].item !== item) hand.push({ f: Math.max(1, a.start - 12), item });
  });
  actors.find((a) => a.id === heroId)!.hand = hand.length ? hand : undefined;
  const baseItems = script.inventory?.items ?? (hand.length ? ['item_diamond_pickaxe', 'item_iron_sword', 'torch'] : []);
  const hotbar = baseItems.length
    ? {
        base: baseItems,
        row2At: script.inventory?.grow_at_beat != null ? tl.beats[Math.min(tl.beats.length - 1, script.inventory.grow_at_beat)]?.from : undefined,
        selected: hand.map((h) => ({ f: h.f, slot: Math.max(0, baseItems.indexOf(h.item)) })),
      }
    : undefined;

  const sounds: SoundEvent[] = tl.ambient.map((a) => ({ f: a.f, event: a.event, vol: 0.7 }));
  const beats: Beat[] = tl.beats.map((b) => ({ from: b.from, to: b.to, text: b.script.text, hl: tokenFor(b.script.text, b.script.hl) }));
  const shots = planShots(placed, tl, tracks, actors, heroId, solids);

  const spec: EpisodeSpec = { id: script.id, title: script.title, cta: script.cta, frames, surface: script.surface ?? 'grass', beats, world, actors, props, hotbar, shots, sounds };
  if (Math.abs(frames - target) > 45) warnings.push(`length is ${(frames / FPS).toFixed(1)} s, target ${(target / FPS).toFixed(1)} s`);
  Object.values(tl.states).forEach((a) => {
    const k = a.tags.findIndex((t) => t.kind === 'climb');
    if (k >= 0 && a.tags.length > k + 1) warnings.push(`${a.id}: acts after climbing happen in the air; put the ladder last`);
  });
  return { spec, errors: [], warnings, frames, seconds: frames / FPS };
};
