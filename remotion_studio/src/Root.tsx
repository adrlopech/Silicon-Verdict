import React from 'react';
import { Composition } from 'remotion';
import { MainScene, MainSceneProps } from './MainScene';
import { StoryScene, StorySceneProps } from './story/StoryScene';
import defaultBundle from '../public/data/bundle.json';

export const Root: React.FC = () => {
  return (
    <>
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
