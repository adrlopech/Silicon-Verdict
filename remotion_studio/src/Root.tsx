import React from 'react';
import { Composition } from 'remotion';
import { MainScene, MainSceneProps } from './MainScene';
import defaultBundle from '../public/data/bundle.json';

export const Root: React.FC = () => {
  return (
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
  );
};
