import React from 'react';
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from 'remotion';
import { Background, Hud, ThemeCtx, clamp } from './primitives';
import { ENTER, EXIT, pickTransition } from './transitions';
import { Grid, Impact, Particles } from './fx';
import { PropField, pickIcons } from './props';
import { BigText, CodeBlock, Counter, Curve, Flash, Footage, ListScene, Outro, ProgressBar, TextWithAccent } from './scenes';
import { Tier, Timeline, Verdict, Versus } from './formats';
import { CursorLayer } from './cursor';
import { Ambient, sceneFx } from './ambient';
import { HEIGHT, MotionGraphicProps, MotionScene, OVERLAP, SceneFx, WIDTH, defaultTheme } from './types';

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
};

/** One scene wrapper: it enters with its own transition (varied per scene), drifts under a slow camera move, lands with an impact ring and thematic objects,
 *  and leaves with the matching exit while the next scene enters on top. */
const SceneShell: React.FC<{ scene: MotionScene; index: number; icons: string[]; fx: SceneFx | null; next?: MotionScene; last: boolean; children: React.ReactNode }> = ({ scene, index, icons, fx, next, last, children }) => {
  const frame = useCurrentFrame();
  const name = index === 0 ? 'zoomThrough' : pickTransition(index, scene.transition);
  const exitName = pickTransition(index + 1, next?.transition); // the exit always matches the NEXT scene's entrance
  const pin = interpolate(frame, [0, OVERLAP], [0, 1], clamp);
  const pout = interpolate(frame, [scene.durationInFrames, scene.durationInFrames + OVERLAP], [0, 1], clamp);
  const style: React.CSSProperties = !last && pout > 0 ? EXIT[exitName](pout, index + 1) : ENTER[name](pin, index);
  // slow push-in with a sideways drift that alternates direction, so a static scene never sits still
  const prog = frame / Math.max(1, scene.durationInFrames);
  const dir = index % 2 === 0 ? 1 : -1;
  const cam = `scale(${1 + 0.07 * prog}) translate(${dir * (prog - 0.5) * 36}px, ${(0.5 - prog) * 22}px) rotate(${dir * (prog - 0.5) * 0.8}deg)`;
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

export const MotionGraphic: React.FC<MotionGraphicProps> = ({ scenes, theme = defaultTheme, title }) => {
  if (!scenes?.length) throw new Error('MotionGraphic needs at least one scene');
  const frame = useCurrentFrame();
  const th = { ...defaultTheme, ...theme };
  // which scene is current (decides the light/dark variant of the shared background)
  let start = 0;
  let current = scenes.length - 1;
  const starts: number[] = [];
  scenes.forEach((s, i) => {
    starts.push(start);
    if (frame >= start && frame < start + s.durationInFrames) current = i;
    start += s.durationInFrames;
  });
  const sceneIcons: string[][] = [];
  scenes.forEach((sc, i) => sceneIcons.push(sc.cursor === 'toggle' ? [] : pickIcons(sc, sceneIcons[i - 1] ?? []))); // the Control Center panel takes the place of the icon tiles
  const fxs = sceneFx(scenes);
  const light = !!scenes[current].light;
  const flash = scenes[current].type === 'flash';
  return (
    <ThemeCtx.Provider value={{ theme: th, light }}>
      <AbsoluteFill style={{ width: WIDTH, height: HEIGHT }} data-cursor-root="1">
        <Background light={light} background={th.background} accent={th.accent} />
        {!flash && <Grid accent={th.accent} light={light} />}
        <Particles accent={th.accent} light={light} />
        {scenes.map((scene, i) => {
          const C = SCENES[scene.type] ?? BigText;
          const last = i === scenes.length - 1;
          return (
            <Sequence key={i} from={starts[i]} durationInFrames={scene.durationInFrames + (last ? 0 : OVERLAP)} layout="none">
              <ThemeCtx.Provider value={{ theme: th, light: !!scene.light }}>
                <SceneShell scene={scene} index={i} icons={sceneIcons[i]} fx={fxs[i]} next={scenes[i + 1]} last={last}>
                  <C scene={scene} />
                </SceneShell>
              </ThemeCtx.Provider>
            </Sequence>
          );
        })}
        {!flash && <CursorLayer scenes={scenes} starts={starts} current={current} accent={th.accent} title={title} />}
        {!flash && <Hud index={current} total={scenes.length} label={title} />}
      </AbsoluteFill>
    </ThemeCtx.Provider>
  );
};

export const totalFrames = (scenes: MotionScene[]) => scenes.reduce((a, s) => a + s.durationInFrames, 0);
