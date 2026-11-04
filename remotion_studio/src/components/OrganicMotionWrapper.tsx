import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export interface OrganicMotionWrapperProps {
  children: React.ReactNode;
  triggerFrame?: number;
  startFrame?: number;
  durationFrames?: number;
  durationInFrames?: number;
  baseWidth?: number;
  baseHeight?: number;
  glowColor?: string;
  centerYPercent?: number;
  motionPreset?: 'hero' | 'metric' | 'diagram';
  style?: React.CSSProperties;
}

export const OrganicMotionWrapper: React.FC<OrganicMotionWrapperProps> = ({
  children,
  triggerFrame = 0,
  startFrame = 0,
  durationFrames,
  durationInFrames,
  baseWidth = 320,
  baseHeight = 320,
  glowColor = '#007AFF',
  centerYPercent = 45,
  motionPreset = 'hero',
  style = {},
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const effectiveStart = triggerFrame || startFrame || 0;
  const effectiveDuration = durationFrames || durationInFrames || 3600;

  // Active time window
  if (frame < effectiveStart || frame > effectiveStart + effectiveDuration + 16) {
    return null;
  }

  const localFrame = Math.max(0, frame - effectiveStart);

  // 1. Elastic Enter Spring with controlled overshoot
  const enterSpring = spring({
    frame: localFrame,
    fps,
    config: { damping: 11, stiffness: 140, mass: 0.8 },
  });

  // 2. Fast Exit Transition
  const isExiting = localFrame > effectiveDuration;
  const exitFrames = Math.max(5, Math.round(fps * 0.22));
  const exitProgress = isExiting
    ? interpolate(localFrame - effectiveDuration, [0, exitFrames], [1, 0], {
        extrapolateRight: 'clamp',
        extrapolateLeft: 'clamp',
      })
    : 1.0;

  // 3. BREATHING LAYER: Subtle perpetual sine scale oscillation (2.2s period, +/- 2.8%)
  const breathingScale =
    1.0 + Math.sin((localFrame * 2 * Math.PI) / (fps * 2.2)) * 0.028;

  // 4. FLOATING DRIFT LAYER: Uncoupled Lissajous idle drift (time-based)
  const driftX = Math.sin((localFrame / fps) * 2.3) * 6.0;
  const driftY = Math.cos((localFrame / fps) * 1.8) * 9.5;
  const microRotation = Math.sin((localFrame / fps) * 1.5) * 1.3; // +/- 1.3 degrees

  // 5. GLOW PULSE: Dynamic ambient drop-shadow oscillation (30% to 60%)
  const glowIntensity = interpolate(
    Math.sin((localFrame / fps) * 3.3),
    [-1, 1],
    [0.30, 0.60]
  );

  const combinedScale = enterSpring * breathingScale * exitProgress;
  const opacity =
    interpolate(enterSpring, [0, 0.25], [0, 1], {
      extrapolateRight: 'clamp',
      extrapolateLeft: 'clamp',
    }) * exitProgress;

  const alphaHex = Math.round(glowIntensity * 255)
    .toString(16)
    .padStart(2, '0');

  return (
    <div
      style={{
        position: 'absolute',
        top: `${centerYPercent}%`,
        left: '50%',
        transform: `translate(-50%, -50%) translate(${driftX}px, ${driftY}px) rotate(${microRotation}deg) scale(${combinedScale})`,
        opacity,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10,
        filter: `drop-shadow(0 0 32px ${glowColor}${alphaHex})`,
        willChange: 'transform, opacity, filter',
        ...style,
      }}
    >
      {children}
    </div>
  );
};
