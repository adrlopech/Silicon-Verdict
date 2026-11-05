/**
 * Minecraft video kit — episode: a data-driven composition.
 * An EpisodeSpec describes the world, the actors' choreography, the props, the camera shots, the script (beats) and extra sounds;
 * everything else (animations, sounds on footsteps / hits / breaks / chest, hotbar pickups, transitions, validation) is automatic.
 * See docs/minecraft_video_kit.md.
 */
import React, { useMemo } from 'react';
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from 'remotion';
import { ThreeCanvas } from '@remotion/three';
import * as THREE from 'three';
import { Humanoid, Mob } from './actors';
import { ActorPlan, Track, finishTrack, planTrack } from './choreo';
import { Body, Box, Solid, applyHits, inBox, minGap, separate, uniqBoxes } from './collision';
import { AssetsCtx, PIXEL, SoundMapCtx, Sprite3D, TIMES, setTimeOfDay, clamp, shortestDelta, sstep, useAssets } from './core';
import { ActorKind, KINDS, isHumanoid } from './kinds';
import { blockingBoxes, episodeSolids, planningSolids } from './solids';
import { CUT_FRAMES, Rig, Shot, cameraAt, cutIntensity } from './camera';
import { BigTitle, Hotbar, Subtitle } from './hud';
import { Post } from './post';
import { Burst, Chest, Door, House, Ladder, Library, ORE_ITEM, PropSpec, SignPost, Stall, Vein, veinBreaks } from './props';
import { SoundEvent, Sounds } from './sfx';
import { Clouds, Plants, SunShadow, Torches, Water, World, WorldSpec } from './world';

export interface Beat { from: number; to: number; text: string; hl?: string; words?: { s: number; e: number }[] } // words: start/end frame of each word relative to `from` (narration timing)
export type { ActorKind };
export interface ActorSpec {
  id: string;
  kind: ActorKind;
  skin?: string; // texture name override (player: 'skin')
  hand?: string | { f: number; item: string }[]; // item sprite in the right hand (humanoids); a list swaps items over time
  sneak?: boolean;
  swell?: number; // creeper
  priority?: number; // who gives way on contact (default from kinds.ts: player 3, other humanoids/villager 2, mobs 1)
  plan: ActorPlan;
}
export interface Transfer { f0: number; f1: number; from: string; to: [number, number]; item: string }
export interface HotbarSpec {
  base: string[]; // initial items (texture names), slot 0 is selected
  row2At?: number; // frame when the second row appears ("bigger inventory")
  selected?: { f: number; slot: number }[]; // selected slot over time (default slot 0)
}
export interface EpisodeSpec {
  id: string;
  title: string;
  cta: string;
  frames: number; // 30 fps; 600 = 20 s
  beats: Beat[];
  shots: Shot[];
  world: WorldSpec;
  actors: ActorSpec[];
  props: PropSpec[];
  hotbar?: HotbarSpec;
  sounds?: SoundEvent[]; // extra sounds (mob ambience, UI...)
  surface?: string; // footstep surface for players: 'grass' (default), 'stone', 'sand', 'gravel', 'wood', 'snow'...
  transfers?: Transfer[]; // items handed from an actor to a point (the 'give' action)
  titleFrames?: number;
  dof?: number; // depth-of-field blur strength (default 2; 0 disables)
}

const lookTowardsPlayers = (spec: EpisodeSpec, tracks: Record<string, Track>) => {
  const players = spec.actors.filter((a) => a.kind === 'player').map((a) => tracks[a.id]);
  spec.actors.forEach((a) => {
    if (a.kind === 'player' || !players.length) return;
    const T = tracks[a.id];
    const want = new Float32Array(spec.frames);
    for (let f = 0; f < spec.frames; f++) {
      let best = 99, rel = 0;
      players.forEach((P) => {
        const dx = P.x[f] - T.x[f], dz = P.z[f] - T.z[f];
        const d = Math.hypot(dx, dz);
        if (d < best) { best = d; rel = shortestDelta(T.face[f], Math.atan2(dx, dz)); }
      });
      // vanilla LookAtPlayerGoal: within ~6 blocks, head only (clamped), never over the shoulder
      const wgt = sstep((6 - best) / 2) * (Math.abs(rel) < 2.0 ? 1 : 0);
      want[f] = Math.max(-0.9, Math.min(0.9, rel)) * wgt;
    }
    // zero-phase low-pass: the head eases towards the player instead of snapping
    const out = T.look;
    let v = want[0];
    for (let f = 0; f < spec.frames; f++) out[f] = v += (want[f] - v) * 0.12;
    v = out[spec.frames - 1];
    for (let f = spec.frames - 1; f >= 0; f--) out[f] = v += (out[f] - v) * 0.12;
  });
};

export const pondBoxes = (world: WorldSpec): Box[] => (world.ponds ?? []).map(([x0, z0, x1, z1]) => [x0, z0, x1, z1]);

/** A plan completed with the actor kind's defaults (stride, hitbox radius, footstep rate) and every solid of the episode.
 *  The director uses the same function while it lays out the timeline, so its timing matches the final tracks. */
export const resolvePlan = (kind: ActorKind, plan: ActorPlan, solids: Solid[], water: Box[]): ActorPlan => {
  const K = KINDS[kind];
  return {
    ...plan,
    stride: plan.stride ?? K.stride,
    stepEvery: plan.stepEvery ?? K.stepEvery,
    radius: plan.radius ?? K.w / 2,
    water: plan.water ?? water,
    obstacles: uniqBoxes([...(plan.obstacles ?? []), ...blockingBoxes(solids, K.h)]),
  };
};

/**
 * Tracks for every actor, with hitboxes: paths go around all solids (props, trees, hills, ponds for non-swimmers),
 * attacks knock their target back, overlapping actors give way by priority, and mobs look at players nearby.
 */
export const buildTracks = (spec: EpisodeSpec): Record<string, Track> => {
  const solids = planningSolids(spec.world, spec.props);
  const water = pondBoxes(spec.world);
  const plans = spec.actors.map((a) => resolvePlan(a.kind, a.plan, solids, water));
  const raws = plans.map((p) => planTrack(p, spec.frames));
  const bodies: Body[] = spec.actors.map((a, i) => {
    const K = KINDS[a.kind], R = raws[i], P = plans[i];
    const swims = P.steps.some((s) => s.t === 'walk' && s.swim);
    return {
      id: a.id, kind: a.kind, r: K.w / 2, h: K.h, priority: a.priority ?? K.priority,
      X: R.X, Z: R.Z, Y: R.Yb, F: R.F, hop: R.hop, hurts: R.hurts,
      attacks: R.acts.filter((q) => q.kind === 'attack'),
      avoid: uniqBoxes([...(P.obstacles ?? []), ...((P.avoidWater ?? !swims) ? water : [])]),
    };
  });
  applyHits(bodies, spec.frames);
  separate(bodies, spec.frames);
  const tracks = Object.fromEntries(spec.actors.map((a, i) => [a.id, finishTrack(raws[i], plans[i])]));
  lookTowardsPlayers(spec, tracks);
  return tracks;
};

/** Sounds derived from the choreography: footsteps, tool hits, block breaks, pickups, attacks, chest. */
export const buildSoundtrack = (spec: EpisodeSpec, tracks: Record<string, Track>): SoundEvent[] => {
  const out: SoundEvent[] = [...(spec.sounds ?? [])];
  const stepEvent = (k: ActorKind) =>
    k === 'player' || k === 'creeper' || k === 'villager' ? `block.${spec.surface ?? 'grass'}.step` : k === 'cave_spider' ? 'entity.spider.step' : `entity.${k}.step`;
  spec.actors.forEach((a) => {
    const T = tracks[a.id];
    T.steps.forEach((f) => {
      if (T.swim(f) > 0.3 || T.amt('climb', f) > 0.3) return; // no footsteps in the water or on the ladder
      out.push({ f, event: stepEvent(a.kind), vol: 0.7 + 0.25 * Math.min(1, T.speed[f] / 4) });
    });
    // swimming: a splash when entering and a stroke sound every ~14 frames; climbing: a rung sound every ~9 frames
    let wasIn = false;
    for (let f = 0; f < spec.frames; f++) {
      const inWater = T.swim(f) > 0.5;
      if (inWater && !wasIn) out.push({ f, event: 'entity.player.splash', vol: 0.9 });
      if (inWater && f % 14 === 0) out.push({ f, event: 'entity.player.swim', vol: 0.55 });
      if (T.amt('climb', f) > 0.5 && f % 9 === 0) out.push({ f, event: 'block.ladder.step', vol: 0.7 });
      wasIn = inWater;
    }
    T.acts.filter((q) => q.kind === 'attack').forEach((q) => T.hits.filter((h) => h >= q.start && h < q.start + q.frames).forEach((h, k) => out.push({ f: h, event: k % 3 === 2 ? 'entity.player.attack.strong' : 'entity.player.attack.weak' })));
    T.hurts.forEach((h) => out.push({ f: h + 1, event: `entity.${a.kind === 'cave_spider' ? 'spider' : a.kind}.hurt`, vol: 0.75 }));
  });
  spec.props.forEach((p) => {
    if (p.type === 'chest') {
      out.push({ f: p.openAt, event: 'block.chest.open' });
      out.push({ f: p.closeAt + 10, event: 'block.chest.close' });
    }
    if (p.type === 'door') {
      out.push({ f: p.openAt, event: 'block.wooden_door.open' });
      out.push({ f: p.closeAt + 8, event: 'block.wooden_door.close' });
    }
    if (p.type === 'vein') {
      const v = veinBreaks(p, tracks);
      if (!v) return;
      v.breaks.forEach((bf) => {
        out.push({ f: bf - v.act.cycle + Math.round(v.act.cycle * 0.34), event: 'block.stone.hit' }); // pickaxe hit
        out.push({ f: bf, event: 'block.stone.break' });
        out.push({ f: bf + 28, event: 'entity.item.pickup' });
      });
    }
  });
  return out.filter((e) => e.f >= 0 && e.f < spec.frames);
};

const isHitboxNote = (m: string) => /hitbox|no free path/.test(m);

/** Hitbox checks: actors overlapping each other or a solid (at the time it exists), and the camera inside an actor or a block. */
export const collisionReport = (spec: EpisodeSpec, tracks: Record<string, Track>): string[] => {
  const w: string[] = Object.entries(tracks).flatMap(([id, T]) => T.warnings.filter(isHitboxNote).map((m) => `${id}: ${m}`));
  const bodies = spec.actors.map((a) => {
    const T = tracks[a.id], K = KINDS[a.kind];
    return { id: a.id, kind: a.kind, r: K.w / 2, h: K.h, priority: K.priority, X: T.x, Z: T.z, Y: T.y, F: T.face, hop: [], hurts: [], attacks: [], avoid: [] } as Body;
  });
  for (let i = 0; i < bodies.length; i++)
    for (let j = i + 1; j < bodies.length; j++) {
      const g = minGap(bodies[i], bodies[j], spec.frames);
      if (g.gap < -0.05) w.push(`${bodies[i].id} and ${bodies[j].id} overlap by ${(-g.gap).toFixed(2)} blocks at frame ${g.at}`);
    }
  const solids = episodeSolids(spec.world, spec.props, tracks);
  bodies.forEach((b) => {
    const seen = new Set<string>();
    for (let f = 0; f < spec.frames; f += 2)
      for (const s of solids) {
        if ((s.from != null && f < s.from) || (s.to != null && f >= s.to) || b.Y[f] >= s.y1 || b.Y[f] + b.h <= s.y0) continue;
        if (inBox(b.X[f], b.Z[f], s.box, b.r - 0.06) && !seen.has(s.what)) {
          seen.add(s.what);
          w.push(`${b.id} walks into a ${s.what} at frame ${f}`);
        }
      }
  });
  const near = new Set<string>();
  for (let f = 0; f < spec.frames; f += 3) {
    const c = cameraAt(spec.shots, tracks, f).pos;
    bodies.forEach((b) => {
      if (near.has(b.id)) return;
      const dy = c[1] < b.Y[f] ? b.Y[f] - c[1] : c[1] > b.Y[f] + b.h ? c[1] - b.Y[f] - b.h : 0;
      if (Math.hypot(Math.hypot(c[0] - b.X[f], c[2] - b.Z[f]) - b.r, dy) < 0.6) { near.add(b.id); w.push(`camera almost touches ${b.id} at frame ${f}`); }
    });
    const inside = solids.find((s) => c[1] > s.y0 && c[1] < s.y1 && inBox(c[0], c[2], s.box, 0.15));
    if (inside && !near.has('#' + inside.what)) { near.add('#' + inside.what); w.push(`camera inside a ${inside.what} at frame ${f}`); }
  }
  return w;
};

/** Authoring checks: prints warnings for the things that made earlier videos look wrong. */
/** Authoring warnings (script / episode mistakes) and, unless `collisions` is false, the hitbox and camera report. */
export const validateEpisode = (spec: EpisodeSpec, tracks: Record<string, Track>, opts: { collisions?: boolean } = {}): string[] => {
  const w: string[] = [];
  spec.shots.forEach((s, i) => {
    if (s.to - s.from < 60 && i > 0) w.push(`shot ${i} (${s.from}-${s.to}) is shorter than 60 frames: with 12-frame transitions it will feel jittery`);
    if (i > 0 && s.from !== spec.shots[i - 1].to) w.push(`shot ${i} does not start where shot ${i - 1} ends`);
  });
  if (spec.shots.length > spec.frames / 75 + 1) w.push(`${spec.shots.length} shots in ${spec.frames / 30}s: too many cuts make the video dizzy (aim for one every ~3 s)`);
  if (spec.shots[spec.shots.length - 1].to < spec.frames) w.push('the last shot ends before the video does');
  Object.entries(tracks).forEach(([id, T]) => T.warnings.filter((m) => !isHitboxNote(m)) /* reported by collisionReport */.forEach((m) => w.push(`${id}: ${m}`)));
  spec.actors.forEach((a) => {
    const T = tracks[a.id];
    const top = Math.max(...T.speed);
    if (top > 4.9 && a.kind !== 'creeper') w.push(`${a.id}: top speed ${top.toFixed(1)} blocks/s looks like x2 playback; use longer walks or sprint deliberately`);
  });
  if (spec.beats.length && spec.beats[spec.beats.length - 1].to < spec.frames) w.push('subtitles end before the video does');
  if (opts.collisions !== false) w.push(...collisionReport(spec, tracks));
  return w;
};

/** An item flying in an arc from the giver's hand to the receiver, with a green sparkle on arrival. */
const Handover: React.FC<{ t: Transfer; f: number; T: Track }> = ({ t, f, T }) => {
  if (f < t.f0 || f > t.f1 + 16) return null;
  const k = Math.min(1, (f - t.f0) / Math.max(1, t.f1 - t.f0));
  const e = k * k * (3 - 2 * k);
  const [px, pz] = T.pos(Math.min(f, t.f1));
  const x = px + (t.to[0] - px) * e, z = pz + (t.to[1] - pz) * e;
  const y = 1.0 + 0.25 * e + Math.sin(Math.PI * e) * 0.35;
  return (
    <>
      {f <= t.f1 && <Sprite3D name={t.item} scale={0.45} position={[x, y, z]} rotation={[0, f * 0.18, 0]} />}
      <Burst p={[t.to[0], 1.15, t.to[1]]} age={f - t.f1} color="#55ff55" seed={t.f0} />
    </>
  );
};

/** Torch light on an actor: sum of falloffs of the torches within 4 blocks, quantised to 0.08 steps (bounded material cache). */
const torchWarm = (world: WorldSpec, T: Track, f: number) => {
  if (!world.torches?.length) return 0;
  const [x, z] = T.pos(f);
  let w = 0;
  world.torches.forEach(([tx, ty, tz]) => {
    const d = Math.hypot(tx - x, ty - 1.0, tz - z);
    if (d < 4) w += Math.pow(1 - d / 4, 2) * 0.55;
  });
  return Math.min(0.56, Math.round(w / 0.08) * 0.08);
};

const Actor: React.FC<{ a: ActorSpec; T: Track; f: number; world: WorldSpec }> = ({ a, T, f, world }) =>
  isHumanoid(a.kind) ? (
    <Humanoid track={T} f={f} kind={a.kind} skin={a.skin} hand={typeof a.hand === 'string' || !a.hand ? a.hand : [...a.hand].reverse().find((h) => h.f <= f)?.item ?? a.hand[0].item} sneak={a.sneak} warm={torchWarm(world, T, f)} />
  ) : (
    <Mob track={T} f={f} kind={a.kind as Exclude<ActorKind, 'player' | 'zombie' | 'skeleton'>} skin={a.skin} swell={a.swell} warm={torchWarm(world, T, f)} />
  );

const Inner: React.FC<{ spec: EpisodeSpec }> = ({ spec }) => {
  setTimeOfDay(spec.world.time);
  const TOD = TIMES[spec.world.time ?? 'day'];
  const f = useCurrentFrame();
  const { width, height, durationInFrames } = useVideoConfig();
  const tracks = useMemo(() => buildTracks(spec), [spec]);
  const sounds = useMemo(() => buildSoundtrack(spec, tracks), [spec, tracks]);
  const camPath = useMemo(() => {
    const pts: [number, number][] = [];
    for (let k = 0; k < spec.frames; k += 4) {
      const c = cameraAt(spec.shots, tracks, k).pos;
      if (c[1] < 2.6) pts.push([c[0], c[2]]); // only low cameras can have a plant in front of the lens
    }
    return pts;
  }, [spec, tracks]);
  useMemo(() => {
    const w = validateEpisode(spec, tracks);
    console.log(`[${spec.id}] validator: ${w.length} warning(s)` + (w.length ? ':\n - ' + w.join('\n - ') : ''));
  }, [spec, tracks]);

  const pickups = useMemo(
    () =>
      spec.props
        .flatMap((p) => {
          if (p.type !== 'vein') return [];
          const v = veinBreaks(p, tracks);
          return v ? v.breaks.map((bf, k) => ({ f: bf + 28, item: ORE_ITEM[p.ores[k]] })) : [];
        })
        .sort((a, b) => a.f - b.f),
    [spec, tracks],
  );
  const items = spec.hotbar ? [...spec.hotbar.base, ...pickups.filter((p) => p.f <= f).map((p) => p.item)] : [];
  const row2 = spec.hotbar?.row2At != null ? interpolate(f, [spec.hotbar.row2At, spec.hotbar.row2At + 12], [0, 1], clamp) : 0;

  const beat = spec.beats.find((b) => f >= b.from && f < b.to) ?? spec.beats[spec.beats.length - 1];
  const subIn = beat ? interpolate(f - beat.from, [0, 6], [0, 1], clamp) : 0;
  const tf = spec.titleFrames ?? 75;
    const ctaOp = interpolate(f, [durationInFrames - 50, durationInFrames - 38], [0, 1], clamp);
  const cut = cutIntensity(spec.shots, f);
  const cam = cameraAt(spec.shots, tracks, f);
  const focus = Math.hypot(cam.pos[0] - cam.look[0], cam.pos[1] - cam.look[1], cam.pos[2] - cam.look[2]);

  return (
    <AbsoluteFill style={{ backgroundColor: TOD.sky }}>
      <div style={{ position: 'absolute', inset: 0, filter: `blur(${cut * 2.5}px)` }}>
        <ThreeCanvas width={width} height={height} shadows camera={{ fov: 52, position: [0, 2, 8], near: 0.1, far: 200 }} gl={{ antialias: false, toneMapping: THREE.NoToneMapping }}>
          <Rig f={f} shots={spec.shots} tracks={tracks} />
          <color attach="background" args={[TOD.sky]} />
          <fog attach="fog" args={[TOD.fog, 28, 75]} />
          <World spec={spec.world} />
          <Plants spec={spec.world} avoid={camPath} />
          <Water spec={spec.world} f={f} />
          {spec.world.time !== 'night' && <Clouds f={f} />}
          <Torches spec={spec.world} f={f} />
          {spec.props.map((p, i) =>
            p.type === 'chest' ? <Chest key={i} f={f} spec={p} /> : p.type === 'sign' ? <SignPost key={i} spec={p} /> : p.type === 'ladder' ? <Ladder key={i} spec={p} /> : p.type === 'door' ? <Door key={i} f={f} spec={p} /> : p.type === 'stall' ? <Stall key={i} f={f} spec={p} /> : p.type === 'house' ? <House key={i} spec={p} /> : p.type === 'library' ? <Library key={i} f={f} spec={p} /> : <Vein key={i} f={f} spec={p} tracks={tracks} index={i} />,
          )}
          {spec.actors.map((a) => (
            <Actor key={a.id} a={a} T={tracks[a.id]} f={f} world={spec.world} />
          ))}
          {(spec.transfers ?? []).map((t, i) => <Handover key={i} t={t} f={f} T={tracks[t.from]} />)}
          <SunShadow spec={spec.world} />
          <Post focus={focus} bokeh={spec.dof ?? 2} exposure={TOD.exposure} />
        </ThreeCanvas>
      </div>

      <div style={{ position: 'absolute', inset: 0, pointerEvents: 'none', background: 'radial-gradient(ellipse at 50% 42%, rgba(255,240,205,0.10) 0%, rgba(255,255,255,0) 45%, rgba(0,10,30,0.34) 100%)' }} />
      <BigTitle text={spec.title} f={f} frames={tf} />

      {spec.hotbar && row2 > 0 && (
        <div style={{ position: 'absolute', inset: 0, opacity: row2, transform: `translateY(${(1 - row2) * 30}px)` }}>
          <Hotbar items={items} start={9} bottom={540 + 22 * 4 + 10} />
        </div>
      )}
      {spec.hotbar && <Hotbar items={items} start={0} bottom={540} selected={[...(spec.hotbar.selected ?? [])].reverse().find((s) => s.f <= f)?.slot ?? 0} />}
      <Sounds events={sounds} />

      {beat && (
        <div style={{ position: 'absolute', inset: 0, opacity: subIn, transform: `translateY(${(1 - subIn) * 16}px)` }}>
          <Subtitle text={beat.text} hl={beat.hl} words={beat.words} t={f - beat.from} progress={Math.min(1, (f - beat.from) / Math.max(1, beat.to - beat.from - 11))} />
        </div>
      )}
      <div style={{ position: 'absolute', bottom: 150, left: 0, right: 0, textAlign: 'center', opacity: ctaOp }}>
        <span style={{ fontFamily: PIXEL, fontSize: 30, color: '#55ffff', textShadow: '3px 3px 0 #0b3b3b' }}>{spec.cta}</span>
      </div>
    </AbsoluteFill>
  );
};

export const McEpisode: React.FC<{ spec: EpisodeSpec }> = ({ spec }) => {
  const A = useAssets();
  if (!A) return null;
  return (
    <AssetsCtx.Provider value={A.imgs}>
      <SoundMapCtx.Provider value={A.sounds}>
        <Inner spec={spec} />
      </SoundMapCtx.Provider>
    </AssetsCtx.Provider>
  );
};

export { CUT_FRAMES };
