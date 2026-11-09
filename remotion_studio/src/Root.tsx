import React from 'react';
import { Composition } from 'remotion';
import { MotionGraphic, totalFrames } from './motion/MotionGraphic';
import { MotionGraphicProps } from './motion/types';
import motionSample from './motion/sample.json';

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
    </>
  );
};
