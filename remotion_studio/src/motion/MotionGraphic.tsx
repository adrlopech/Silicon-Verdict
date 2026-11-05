import React from 'react';
import { AbsoluteFill, Sequence, interpolate, useCurrentFrame } from 'remotion';
import { Background, EASE_OUT, Hud, ThemeCtx, clamp } from './primitives';
import { BigText, CodeBlock, Counter, Curve, Flash, Footage, ListScene, Outro, ProgressBar, TextWithAccent } from './scenes';
import { HEIGHT, MotionGraphicProps, MotionScene, OVERLAP, WIDTH, defaultTheme } from './types';

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
};

/** One scene wrapper: soft rise-in, soft blur-out while the next scene fades in underneath (cross-fade, never a hard cut). */
const SceneShell: React.FC<{ scene: MotionScene; last: boolean; children: React.ReactNode }> = ({ scene, last, children }) => {
  const frame = useCurrentFrame();
  const fin = interpolate(frame, [0, 10], [0, 1], { ...clamp, easing: EASE_OUT });
  const fout = last ? 1 : interpolate(frame, [scene.durationInFrames, scene.durationInFrames + OVERLAP], [1, 0], { ...clamp, easing: EASE_OUT });
  return <AbsoluteFill style={{ opacity: Math.min(fin, fout), filter: `blur(${(1 - fout) * 10}px)` }}>{children}</AbsoluteFill>;
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
  const light = !!scenes[current].light;
  const flash = scenes[current].type === 'flash';
  return (
    <ThemeCtx.Provider value={{ theme: th, light }}>
      <AbsoluteFill style={{ width: WIDTH, height: HEIGHT }}>
        <Background light={light} background={th.background} accent={th.accent} />
        {scenes.map((scene, i) => {
          const C = SCENES[scene.type] ?? BigText;
          const last = i === scenes.length - 1;
          return (
            <Sequence key={i} from={starts[i]} durationInFrames={scene.durationInFrames + (last ? 0 : OVERLAP)} layout="none">
              <ThemeCtx.Provider value={{ theme: th, light: !!scene.light }}>
                <SceneShell scene={scene} last={last}>
                  <C scene={scene} />
                </SceneShell>
              </ThemeCtx.Provider>
            </Sequence>
          );
        })}
        {!flash && <Hud index={current} total={scenes.length} label={title} />}
      </AbsoluteFill>
    </ThemeCtx.Provider>
  );
};

export const totalFrames = (scenes: MotionScene[]) => scenes.reduce((a, s) => a + s.durationInFrames, 0);
