import React from 'react';
import { Composition } from 'remotion';
import { McEpisode } from './mc/episode';
import { mobsDemo, mobsLine } from './mc/episodes/mobsDemo';
import { actionsDemo } from './mc/episodes/actionsDemo';
import { McStory, compileMcScript } from './mc/story';
import { MotionGraphic, totalFrames } from './motion/MotionGraphic';
import { MotionGraphicProps } from './motion/types';
import motionSample from './motion/sample.json';
import studioPreview from '../mc_scripts/studio_preview.json'; // placeholder for Remotion Studio only: the pipeline always passes a new Gemini script

export const Root: React.FC = () => {
  return (
    <>
    <Composition
      id="MotionGraphic"
      component={MotionGraphic as unknown as React.FC<Record<string, unknown>>}
      durationInFrames={totalFrames((motionSample as unknown as MotionGraphicProps).scenes)}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={motionSample as unknown as Record<string, unknown>}
      calculateMetadata={async ({ props }) => ({ durationInFrames: totalFrames((props as unknown as MotionGraphicProps).scenes) })}
    />
    <Composition
      id="McMobsDemo"
      component={McEpisode as unknown as React.FC<Record<string, unknown>>}
      durationInFrames={mobsDemo.frames}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ spec: mobsDemo } as unknown as Record<string, unknown>}
    />
    <Composition
      id="McActionsDemo"
      component={McEpisode as unknown as React.FC<Record<string, unknown>>}
      durationInFrames={actionsDemo.frames}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ spec: actionsDemo } as unknown as Record<string, unknown>}
    />
    <Composition
      id="McStory"
      component={McStory as unknown as React.FC<Record<string, unknown>>}
      durationInFrames={600}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ script: studioPreview } as unknown as Record<string, unknown>}
      calculateMetadata={async ({ props }) => ({ durationInFrames: compileMcScript((props as { script: never }).script).frames || 600 })}
    />
    <Composition
      id="McMobsLine"
      component={McEpisode as unknown as React.FC<Record<string, unknown>>}
      durationInFrames={mobsLine.frames}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ spec: mobsLine } as unknown as Record<string, unknown>}
    />
    </>
  );
};
