import React, { useMemo } from 'react';
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from 'remotion';
import { Background, Hud, ThemeCtx, clamp } from './primitives';
import { ENTER, EXIT, pickTransition } from './transitions';
import { Grid, Impact, Particles } from './fx';
import { PropField, pickIcons } from './props';
import { BigText, CodeBlock, Counter, Curve, Flash, Footage, ListScene, Outro, ProgressBar, TextWithAccent } from './scenes';
import { Tier, Timeline, Verdict, Versus } from './formats';
import { UiScene } from './ui';
import { CursorLayer } from './cursor';
import { Captions, captionSpaceFor, chunkCaptions } from './captions';
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
};

/** One scene wrapper: it enters with its own transition (varied per scene), drifts under a slow camera move, lands with an impact ring and thematic objects,
 *  and leaves with the matching exit while the next scene enters on top. */
const SceneShell: React.FC<{ scene: MotionScene; index: number; icons: string[]; fx: SceneFx | null; next?: MotionScene; last: boolean; children: React.ReactNode }> = ({ scene, index, icons, fx, next, last, children }) => {
  const frame = useCurrentFrame();
  const look = useLook();
  const name = index === 0 ? 'zoomThrough' : pickTransition(index, scene.transition, look.transitions);
  const exitName = pickTransition(index + 1, next?.transition, look.transitions); // the exit always matches the NEXT scene's entrance
  const pin = interpolate(frame, [0, OVERLAP], [0, 1], clamp);
  const pout = interpolate(frame, [scene.durationInFrames, scene.durationInFrames + OVERLAP], [0, 1], clamp);
  const style: React.CSSProperties = !last && pout > 0 ? EXIT[exitName](pout, index + 1) : ENTER[name](pin, index);
  // slow push-in with a sideways drift that alternates direction, so a static scene never sits still
  const prog = frame / Math.max(1, scene.durationInFrames);
  const dir = index % 2 === 0 ? 1 : -1;
  const shake = (k: number) => Math.sin(frame * 0.9 + index * 3 + k) * 3.2 + Math.sin(frame * 2.3 + k * 5) * 1.6; // handheld: a small, constant tremor
  const cam = {
    drift: `scale(${1 + 0.07 * prog}) translate(${dir * (prog - 0.5) * 36}px, ${(0.5 - prog) * 22}px) rotate(${dir * (prog - 0.5) * 0.8}deg)`,
    push: `scale(${1 + 0.12 * prog})`,
    orbit: `scale(${1.03 + 0.05 * prog}) rotate(${dir * (prog - 0.5) * 3.2}deg) translate(${dir * (prog - 0.5) * 50}px, 0px)`,
    handheld: `scale(1.025) translate(${shake(1)}px, ${shake(2)}px) rotate(${shake(3) * 0.06}deg)`,
    still: 'none',
  }[look.camera];
  return (
    <AbsoluteFill style={style} data-scene={index}>
      <AbsoluteFill style={{ transform: cam }}>
        <Ambient fx={fx} />
        <PropField icons={icons} index={index} />
        <AbsoluteFill style={scene.cursor === 'toggle' ? { transform: 'translateY(-200px)' } : undefined}>{children}</AbsoluteFill>
      </AbsoluteFill>
      <Impact seed={index} />
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
                    <SceneShell scene={scene} index={i} icons={sceneIcons[i]} fx={fxs[i]} next={scenes[i + 1]} last={last}>
                      <C scene={scene} />
                    </SceneShell>
                  </SceneCtx.Provider>
                </ThemeCtx.Provider>
              </Sequence>
            );
          })}
          {!flash && <Captions chunks={chunks} scene={scenes[current]} />}
          {!flash && <CursorLayer scenes={scenes} starts={starts} current={current} accent={th.accent} />}
          {!flash && <Hud index={current} total={scenes.length} label={title} segments={segments} />}
        </AbsoluteFill>
      </ThemeCtx.Provider>
    </LookCtx.Provider>
  );
};

export const totalFrames = (scenes: MotionScene[]) => scenes.reduce((a, s) => a + s.durationInFrames, 0);
