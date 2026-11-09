import React, { useMemo } from 'react';
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from 'remotion';
import { Background, Hud, ThemeCtx, clamp } from './primitives';
import { ENTER, EXIT, pickTransition } from './transitions';
import { Grid, Impact, Particles } from './fx';
import { PropField, pickIcons } from './props';
import { BigText, Card, CodeBlock, Counter, Curve, Flash, Footage, ListScene, Outro, ProgressBar, TextWithAccent } from './scenes';
import { Tier, Timeline, Verdict, Versus } from './formats';
import { UiScene } from './ui';
import { CursorLayer } from './cursor';
import { Captions, captionSpaceFor, chunkCaptions } from './captions';
import { Callout, Decor, Shock } from './decor';
import { LookCtx, SceneCtx, lookFor } from './looks';
import { Ambient, sceneFx } from './ambient';
import { HEIGHT, MotionGraphicProps, MotionScene, OVERLAP, SceneFx, WIDTH, defaultTheme } from './types';
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
};

/** One scene wrapper: it enters with its own transition (varied per scene), drifts under a slow camera move, lands with an impact ring and thematic objects,
 *  and leaves with the matching exit while the next scene enters on top. */
const SceneShell: React.FC<{ scene: MotionScene; index: number; total: number; rehook: boolean; icons: string[]; fx: SceneFx | null; next?: MotionScene; last: boolean; children: React.ReactNode }> = ({ scene, index, total, rehook, icons, fx, next, last, children }) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const hard = look.transitions.find((t) => t === 'whip' || t === 'glitch' || t === 'zoomThrough') ?? look.transitions[0];
  const name = index === 0 ? 'zoomThrough' : rehook ? hard : pickTransition(index, scene.transition, look.transitions);
  const exitName = pickTransition(index + 1, next?.transition, look.transitions); // the exit always matches the NEXT scene's entrance
  const pin = interpolate(frame, [0, OVERLAP], [0, 1], clamp);
  const pout = interpolate(frame, [scene.durationInFrames, scene.durationInFrames + OVERLAP], [0, 1], clamp);
  const style: React.CSSProperties = !last && pout > 0 ? EXIT[exitName](pout, index + 1) : ENTER[name](pin, index);
  // slow push-in with a sideways drift that alternates direction, so a static scene never sits still
  const prog = frame / Math.max(1, scene.durationInFrames);
  const dir = index % 2 === 0 ? 1 : -1;
  const shake = (k: number) => Math.sin(frame * 0.9 + index * 3 + k) * 3.2 + Math.sin(frame * 2.3 + k * 5) * 1.6; // handheld: a small, constant tremor
  const calloutAt = scene.callout && scene.calloutCue != null ? Math.round(scene.calloutCue * 30) : null;
  const punch = calloutAt != null ? interpolate(frame, [calloutAt, calloutAt + 3, calloutAt + 12], [0, 1, 0], clamp) : 0; // a small zoom punch as the tag lands
  const cam = {
    drift: `scale(${1 + 0.07 * prog}) translate(${dir * (prog - 0.5) * 36}px, ${(0.5 - prog) * 22}px) rotate(${dir * (prog - 0.5) * 0.8}deg)`,
    push: `scale(${1 + 0.12 * prog})`,
    orbit: `scale(${1.03 + 0.05 * prog}) rotate(${dir * (prog - 0.5) * 3.2}deg) translate(${dir * (prog - 0.5) * 50}px, 0px)`,
    handheld: `scale(1.025) translate(${shake(1)}px, ${shake(2)}px) rotate(${shake(3) * 0.06}deg)`,
    still: 'none',
  }[look.camera];
  const camPunch = punch > 0.001 ? `${cam === 'none' ? '' : cam} scale(${1 + 0.035 * punch})` : cam;
  return (
    <AbsoluteFill style={style} data-scene={index}>
      <AbsoluteFill style={{ transform: camPunch }}>
        <Ambient fx={fx} />
        <Decor scene={scene} index={index} total={total} />
        <PropField icons={icons} index={index} />
        <AbsoluteFill style={scene.cursor === 'toggle' ? { transform: 'translateY(-200px)' } : undefined}>{children}</AbsoluteFill>
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

export const MotionGraphic: React.FC<MotionGraphicProps> = ({ scenes, theme = defaultTheme, title, look: lookName, captions }) => {
  if (!scenes?.length) throw new Error('MotionGraphic needs at least one scene');
  const frame = useCurrentFrame();
  const look = lookFor(lookName);
  // the look sets the palette; a video without a look keeps the props' own theme (obsidian)
  const th = lookName ? { ...defaultTheme, ...theme, accent: look.accent, accent2: look.accent2, background: look.background, text: look.text } : { ...defaultTheme, ...theme };
  // which scene is current (decides the light/dark variant of the shared background)
  let start = 0;
  let current = scenes.length - 1;
  const starts: number[] = [];
  scenes.forEach((s, i) => {
    starts.push(start);
    if (frame >= start && frame < start + s.durationInFrames) current = i;
    start += s.durationInFrames;
  });
  const chunks = useMemo(() => chunkCaptions(captions ?? []), [captions]);
  const sceneIcons: string[][] = [];
  // the Control Center panel and the caption strip take the place of the floating icon tiles
  scenes.forEach((sc, i) => sceneIcons.push(sc.cursor === 'toggle' || captionSpaceFor(sc, chunks.length > 0) > 0 ? [] : pickIcons(sc, sceneIcons[i - 1] ?? [])));
  const fxs = sceneFx(scenes);
  const isLight = (sc: MotionScene) => look.light || !!sc.light; // a light look is light everywhere; otherwise a scene may ask for the light variant
  const light = isLight(scenes[current]);
  const flash = scenes[current].type === 'flash';
  const segments = scenes.map((sc, i) => ({ start: starts[i], len: sc.durationInFrames }));
  const rehookAt = rehookIndex(starts, scenes.map((sc) => sc.durationInFrames));
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
                  <SceneCtx.Provider value={{ scene, captionSpace: captionSpaceFor(scene, chunks.length > 0) }}>
                    <SceneShell scene={scene} index={i} total={scenes.length} rehook={i === rehookAt} icons={sceneIcons[i]} fx={fxs[i]} next={scenes[i + 1]} last={last}>
                      <C scene={scene} />
                    </SceneShell>
                  </SceneCtx.Provider>
                </ThemeCtx.Provider>
              </Sequence>
            );
          })}
          {!flash && <Captions chunks={chunks} scene={scenes[current]} />}
          <LoopTease text={scenes[0].text} total={start} />
          {!flash && <CursorLayer scenes={scenes} starts={starts} current={current} accent={th.accent} />}
          {!flash && <Hud index={current} total={scenes.length} label={title} segments={segments} />}
        </AbsoluteFill>
      </ThemeCtx.Provider>
    </LookCtx.Provider>
  );
};

export const totalFrames = (scenes: MotionScene[]) => scenes.reduce((a, s) => a + s.durationInFrames, 0);
