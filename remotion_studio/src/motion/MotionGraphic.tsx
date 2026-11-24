import React, { useLayoutEffect, useMemo, useRef, useState } from 'react';
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from 'remotion';
import { Background, Hud, ThemeCtx, clamp } from './primitives';
import { ENTER, EXIT, pickTransition } from './transitions';
import { FilmFinish } from './polish';
import { Grid, Impact, Particles } from './fx';
import { PropField, pickIcons } from './props';
import { BigText, Card, CodeBlock, Counter, Curve, Flash, Footage, ListScene, Outro, ProgressBar, TextWithAccent } from './scenes';
import { Tier, Timeline, Verdict, Versus } from './formats';
import { UiScene } from './ui';
import { Headline, Quiz, Rank } from './scenes2';
import { Split, Units } from './scenes3';
import { CursorLayer } from './cursor';
import { Captions, captionSpaceFor, chunkCaptions } from './captions';
import { Callout, Decor, Shock } from './decor';
import { CAPTION_DROP, LookCtx, SceneCtx, lookFor, useSceneCtx } from './looks';
import { BIG_FX, BIG_FX_LIGHT, BigFxName, CAMERA_MOVES, CameraMove, REVEALS, Reveal, pickSeries } from './anim';
import { BigFx } from './bigfx';
import { Ambient, sceneFx } from './ambient';
import { STAGE_SCENES, STAGE_TEXT_MAX_BOTTOM, STAGE_TEXT_MIN_TOP, Stage, VisualName, pickVisuals, stageRoom } from './visuals';
import { HEIGHT, MotionGraphicProps, MotionScene, OVERLAP, SAFE_BOTTOM, SceneFx, WIDTH, defaultTheme } from './types';
import { EASE_IO, EASE_OUT } from './primitives';
import { useLook } from './looks';

const SCENES: Record<MotionScene['type'], React.FC<{ scene: MotionScene }>> = {
  bigText: BigText,
  textWithAccent: TextWithAccent,
  counter: Counter,
  list: ListScene,
  codeBlock: CodeBlock,
  progressBar: ProgressBar,
  outro: Outro,
  curve: Curve,
  flash: Flash,
  footage: Footage,
  tier: Tier,
  versus: Versus,
  verdict: Verdict,
  timeline: Timeline,
  ui: UiScene,
  card: Card,
  rank: Rank,
  quiz: Quiz,
  headline: Headline,
  split: Split,
  units: Units,
};

/** One scene wrapper: it enters with its own transition (varied per scene), drifts under a slow camera move, lands with an impact ring and thematic objects,
 *  and leaves with the matching exit while the next scene enters on top. */
const SceneShell: React.FC<{ scene: MotionScene; index: number; total: number; rehook: boolean; icons: string[]; fx: SceneFx | null; visual: VisualName | null; move: CameraMove; big: BigFxName | null; next?: MotionScene; last: boolean; children: React.ReactNode }> = ({ scene, index, total, rehook, icons, fx, visual, move, big, next, last, children }) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const { captionSpace } = useSceneCtx();
  // measure where the text block really is (layout values, so entrance animations and the camera do not matter): the block is lifted until it ends above STAGE_TEXT_MAX_BOTTOM
  // and the stage is drawn only in the room left under it; scenes without a stage keep the text where it is
  const holder = useRef<HTMLDivElement>(null);
  const [box, setBox] = useState<{ top: number; bottom: number } | null>(null);
  useLayoutEffect(() => {
    const sb = holder.current?.querySelector('[data-safebox]') as HTMLElement | null;
    if (!sb) return;
    let top = Infinity;
    let bottom = 0;
    sb.childNodes.forEach((n) => {
      const el = n as HTMLElement;
      if (!el.offsetHeight) return;
      top = Math.min(top, el.offsetTop);
      bottom = Math.max(bottom, el.offsetTop + el.offsetHeight);
    });
    if (!isFinite(top)) return;
    const t = sb.offsetTop + top;
    const b = sb.offsetTop + bottom;
    if (!box || Math.abs(box.top - t) > 1 || Math.abs(box.bottom - b) > 1) setBox({ top: t, bottom: b });
  });
  const staged = !!visual && STAGE_SCENES.has(scene.type);
  const edge = HEIGHT - SAFE_BOTTOM - captionSpace; // bottom of the content area; the caption strip starts CAPTION_DROP + 22 px below it
  const fade = `linear-gradient(180deg, #000 0, #000 ${edge + 6}px, transparent ${edge + 6 + Math.round(CAPTION_DROP * 0.8)}px)`;
  const lift = staged && box ? Math.max(0, Math.min(box.bottom - STAGE_TEXT_MAX_BOTTOM, box.top - STAGE_TEXT_MIN_TOP)) : 0;
  const room = staged ? (box ? stageRoom(box.bottom - lift, captionSpace) : 460) : 0;
  const hard = look.transitions.find((t) => t === 'whip' || t === 'glitch' || t === 'zoomThrough') ?? look.transitions[0];
  const name = index === 0 ? 'zoomThrough' : rehook ? hard : pickTransition(index, scene.transition, look.transitions, scene.type);
  const exitName = pickTransition(index + 1, next?.transition, look.transitions, next?.type); // the exit always matches the NEXT scene's entrance
  const pin = interpolate(frame, [0, OVERLAP], [0, 1], clamp);
  const pout = interpolate(frame, [scene.durationInFrames, scene.durationInFrames + OVERLAP], [0, 1], clamp);
  const coldOpen = index === 0 ? { transform: `scale(${interpolate(frame, [0, 10], [1.07, 1], { ...clamp, easing: EASE_OUT })})` } : null; // the hook is on screen at frame 0
  const style: React.CSSProperties = !last && pout > 0 ? EXIT[exitName](pout, index + 1) : coldOpen && pin < 1 ? coldOpen : ENTER[name](pin, index);
  // slow push-in with a sideways drift that alternates direction, so a static scene never sits still
  const prog = frame / Math.max(1, scene.durationInFrames);
  const dir = index % 2 === 0 ? 1 : -1;
  const calloutAt = scene.callout && scene.calloutCue != null ? Math.round(scene.calloutCue * 30) : null;
  const punch = calloutAt != null ? interpolate(frame, [calloutAt, calloutAt + 3, calloutAt + 12], [0, 1, 0], clamp) : 0; // a small zoom punch as the tag lands
  // camera: a different move for (almost) every scene, picked per scene (anim.ts), moving only the backdrop. Looks that ask for a still camera get a gentler version, never none.
  const amp = look.camera === 'still' ? 0.6 : 1; // calm by default: small moves that are felt more than seen
  const e = interpolate(prog, [0, 1], [0, 1], { ...clamp, easing: EASE_IO });
  const jump = index % 5 === 2 ? interpolate(frame, [Math.round(scene.durationInFrames * 0.5), Math.round(scene.durationInFrames * 0.5) + 5], [0, 1], { ...clamp, easing: EASE_OUT }) : 0; // a jump cut to a closer frame halfway through
  const cam = {
    pushIn: `scale(${1 + 0.08 * amp * e})`,
    pullOut: `scale(${1 + 0.08 * amp * (1 - e)})`,
    panLeft: `scale(1.07) translate(${(0.5 - e) * 56 * amp}px, 0px)`,
    panRight: `scale(1.07) translate(${(e - 0.5) * 56 * amp}px, 0px)`,
    tiltUp: `scale(1.07) translate(0px, ${(0.5 - e) * 60 * amp}px)`,
    tiltDown: `scale(1.07) translate(0px, ${(e - 0.5) * 60 * amp}px)`,
    dolly: `scale(${1.03 + 0.07 * amp * e}) translate(${dir * (e - 0.5) * 36 * amp}px, ${(0.5 - e) * 26 * amp}px)`,
    orbit: `scale(${1.04 + 0.03 * e}) rotate(${dir * (e - 0.5) * 2 * amp}deg) translate(${dir * (e - 0.5) * 30 * amp}px, 0px)`,
    crane: `scale(${1.05 + 0.04 * amp * e}) translate(0px, ${(1 - e) * 48 * amp}px)`,
    rollIn: `scale(${1.08 + 0.02 * e}) rotate(${dir * (0.5 - e) * 3.2 * amp}deg)`,
    slideDiag: `scale(1.09) translate(${dir * (e - 0.5) * 54 * amp}px, ${(0.5 - e) * 54 * amp}px)`,
    breathe: `scale(${1.035 + 0.035 * amp * Math.sin(e * Math.PI)})`,
    punch: `scale(${1 + 0.09 * amp * interpolate(frame, [0, 9], [1, 0], { ...clamp, easing: EASE_OUT }) + 0.03 * amp * e})`,
  }[move];
  const camPunch = `${cam} ${punch > 0.001 ? `scale(${1 + 0.035 * punch})` : ''} ${jump > 0 ? `scale(${1 + 0.05 * jump})` : ''}`;
  return (
    <AbsoluteFill style={style} data-scene={index}>
      {/* everything the scene draws fades out just above the caption strip, so a subtitle never sits on a text or an object */}
      <AbsoluteFill style={captionSpace > 0 ? { WebkitMaskImage: fade, maskImage: fade } : undefined}>
      {/* the camera moves only the backdrop (stage, decor, fly-bys, icons): type under a scale / rotation / tremor shimmers and reads as shaking */}
      <AbsoluteFill style={{ transform: camPunch }}>
        {big && <div style={{ position: 'absolute', inset: 0, opacity: 0.55 }}><BigFx name={big} scene={scene} index={index} /></div>}
        <Stage scene={scene} name={visual} index={index} avail={room} />
        {!staged && <Ambient fx={fx} />}
        {!staged && <Decor scene={scene} index={index} total={total} />}
        <PropField icons={icons} index={index} />
      </AbsoluteFill>
      <AbsoluteFill ref={holder} style={scene.cursor === 'toggle' ? { transform: 'translateY(-200px)' } : lift > 0 ? { transform: `translateY(${-lift}px)` } : undefined}>{children}</AbsoluteFill>
      </AbsoluteFill>
      <Impact seed={index} />
      {rehook && <Shock />}
      <Callout scene={scene} />
    </AbsoluteFill>
  );
};

/** The scene whose start is closest to the middle of the video (never the first two or the last two): it gets the re-hook jolt. -1 for short videos. Same rule as services/motion_pipeline.py rehook_index. */
export const rehookIndex = (starts: number[], durations: number[]): number => {
  const n = starts.length;
  if (n < 8) return -1;
  const total = starts[n - 1] + durations[n - 1];
  let best = -1;
  for (let i = 2; i <= n - 3; i++) if (best < 0 || Math.abs(starts[i] - total / 2) < Math.abs(starts[best] - total / 2)) best = i;
  return best;
};

/** The last moments of the video fade to the hook headline, so the loop that restarts the video feels continuous (a viewer who stays for the replay counts twice). */
const LoopTease: React.FC<{ text: string; total: number }> = ({ text, total }) => {
  const frame = useCurrentFrame();
  const look = lookFor(useLook().name);
  const p = interpolate(frame, [total - 26, total - 4], [0, 1], clamp);
  if (p <= 0.001) return null;
  return (
    <AbsoluteFill style={{ opacity: p, background: `radial-gradient(ellipse 80% 60% at 50% 50%, ${look.background}F2 0%, ${look.background}CC 100%)`, alignItems: 'center', justifyContent: 'center', padding: 80 }}>
      <div style={{ fontFamily: look.sans, fontWeight: 900, fontSize: 118, lineHeight: 1.04, textAlign: 'center', color: look.text, textTransform: look.upper ? 'uppercase' : 'none', letterSpacing: -3, transform: `scale(${0.94 + 0.06 * p})` }}>{text}</div>
    </AbsoluteFill>
  );
};

export const MotionGraphic: React.FC<MotionGraphicProps> = ({ scenes, theme = defaultTheme, title, series, look: lookName, captions }) => {
  if (!scenes?.length) throw new Error('MotionGraphic needs at least one scene');
  const frame = useCurrentFrame();
  const look = lookFor(lookName);
  // the look sets the palette; a video without a look keeps the props' own theme (obsidian)
  const th = lookName ? { ...defaultTheme, ...theme, accent: look.accent, accent2: look.accent2, background: look.background, text: look.text } : { ...defaultTheme, ...theme };
  const chunks = useMemo(() => chunkCaptions(captions ?? []), [captions]);
  const hasCaptions = chunks.length > 0;
  // everything that depends only on the props (scene starts, icons, effects, visuals, reveals, camera moves) is computed once, not again on every one of the ~2000 frames
  const plan = useMemo(() => {
    let at = 0;
    const starts: number[] = [];
    scenes.forEach((s) => {
      starts.push(at);
      at += s.durationInFrames;
    });
    const sceneIcons: string[][] = [];
    // the Control Center panel and the caption strip take the place of the floating icon tiles
    scenes.forEach((sc, i) => sceneIcons.push(sc.cursor === 'toggle' || captionSpaceFor(sc, hasCaptions) > 0 ? [] : pickIcons(sc, sceneIcons[i - 1] ?? [])));
    const fxs = sceneFx(scenes);
    const visuals = pickVisuals(scenes);
    const NO_EXTRAS = new Set(['flash', 'footage', 'tier', 'ui', 'outro']);
    const salt = `${title}|${lookName ?? ''}`;
    const reveals = pickSeries<Reveal>(scenes, REVEALS, `${salt}r`, 2, () => REVEALS);
    const moves = pickSeries<CameraMove>(scenes, CAMERA_MOVES, `${salt}c`, 4, () => CAMERA_MOVES);
    const bigs = pickSeries<BigFxName>(scenes, BIG_FX, `${salt}b`, 5, (i) => (NO_EXTRAS.has(scenes[i].type) || i % 3 !== 0 ? null : STAGE_SCENES.has(scenes[i].type) && visuals[i] ? BIG_FX_LIGHT : BIG_FX));
    const segments = scenes.map((sc, i) => ({ start: starts[i], len: sc.durationInFrames }));
    const rehookAt = rehookIndex(starts, scenes.map((sc) => sc.durationInFrames));
    return { starts, total: at, sceneIcons, fxs, visuals, reveals, moves, bigs, segments, rehookAt };
  }, [scenes, title, lookName, hasCaptions]);
  const { starts, total: start, sceneIcons, fxs, visuals, reveals, moves, bigs, segments, rehookAt } = plan;
  // which scene is current (decides the light/dark variant of the shared background)
  let current = scenes.length - 1;
  for (let i = 0; i < scenes.length; i++) {
    if (frame >= starts[i] && frame < starts[i] + scenes[i].durationInFrames) {
      current = i;
      break;
    }
  }
  const isLight = (sc: MotionScene) => look.light || !!sc.light; // a light look is light everywhere; otherwise a scene may ask for the light variant
  const light = isLight(scenes[current]);
  const flash = scenes[current].type === 'flash';
  return (
    <LookCtx.Provider value={look}>
      <ThemeCtx.Provider value={{ theme: th, light }}>
        <AbsoluteFill style={{ width: WIDTH, height: HEIGHT }} data-cursor-root="1">
          <Background light={light} background={th.background} accent={th.accent} />
          {!flash && look.floorGrid && <Grid accent={th.accent} light={light} />}
          <Particles accent={th.accent} accent2={th.accent2} light={light} style={look.particles} />
          {scenes.map((scene, i) => {
            const C = SCENES[scene.type] ?? BigText;
            const last = i === scenes.length - 1;
            return (
              <Sequence key={i} from={starts[i]} durationInFrames={scene.durationInFrames + (last ? 0 : OVERLAP)} layout="none">
                <ThemeCtx.Provider value={{ theme: th, light: isLight(scene) }}>
                  <SceneCtx.Provider value={{ scene, captionSpace: captionSpaceFor(scene, chunks.length > 0), reveal: i === 0 ? 'slam' : reveals[i] ?? 'pop' }}>
                    <SceneShell scene={scene} index={i} total={scenes.length} rehook={i === rehookAt} icons={sceneIcons[i]} fx={fxs[i]} visual={visuals[i]} move={moves[i] ?? 'pushIn'} big={bigs[i]} next={scenes[i + 1]} last={last}>
                      <C scene={scene} />
                    </SceneShell>
                  </SceneCtx.Provider>
                </ThemeCtx.Provider>
              </Sequence>
            );
          })}
          {!flash && <FilmFinish scenes={scenes} starts={starts} current={current} />}
          {!flash && <Captions chunks={chunks} scene={scenes[current]} />}
          <LoopTease text={scenes[0].text} total={start} />
          {!flash && <CursorLayer scenes={scenes} starts={starts} current={current} accent={th.accent} />}
          {!flash && <Hud index={current} total={scenes.length} label={title} series={series} segments={segments} />}
        </AbsoluteFill>
      </ThemeCtx.Provider>
    </LookCtx.Provider>
  );
};

export const totalFrames = (scenes: MotionScene[]) => scenes.reduce((a, s) => a + s.durationInFrames, 0);
