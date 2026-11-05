import React from 'react';
import { Composition } from 'remotion';
import { MainScene, MainSceneProps } from './MainScene';
import { StoryScene, StorySceneProps } from './story/StoryScene';
import defaultBundle from '../public/data/bundle.json';
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
    <Composition
      id="StoryScene"
      component={StoryScene as unknown as React.FC<Record<string, unknown>>}
      durationInFrames={1800}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={{ category: '', hook: '', audio_src: '', total_frames: 1800, subtitles: [], scenes: [] } as unknown as StorySceneProps}
      calculateMetadata={async ({ props }) => ({
        durationInFrames: (props as unknown as StorySceneProps).total_frames || 1800,
      })}
    />
    <Composition
      id="MainScene"
      component={MainScene as unknown as React.FC<Record<string, unknown>>}
      durationInFrames={(defaultBundle as any).total_frames || 1800}
      fps={30}
      width={1080}
      height={1920}
      defaultProps={defaultBundle as unknown as MainSceneProps}
      calculateMetadata={async ({ defaultProps, props }) => {
        const mergedProps = { ...defaultProps, ...props } as unknown as MainSceneProps & { total_frames?: number };
        let maxFrames = 1800;
        if (mergedProps.total_frames) {
          maxFrames = mergedProps.total_frames;
        } else if (mergedProps.subtitles && mergedProps.subtitles.length > 0) {
          const lastWord = mergedProps.subtitles[mergedProps.subtitles.length - 1];
          maxFrames = Math.ceil(lastWord.end * 30) + 45;
        }
        return {
          durationInFrames: maxFrames,
          props: mergedProps as unknown as Record<string, unknown>,
        };
      }}
    />
    </>
  );
};
