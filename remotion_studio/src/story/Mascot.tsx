import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { Pose } from './theme';

type Arm = [number, number, number, number]; // elbowX, elbowY, handX, handY
const POSES: Record<Pose, { L: Arm; R: Arm; eye: number }> = {
  idle: { L: [166, 318, 156, 368], R: [234, 318, 244, 368], eye: 1 },
  surprised: { L: [152, 238, 134, 176], R: [248, 238, 266, 176], eye: 1.5 },
  cheer: { L: [150, 232, 138, 170], R: [250, 232, 262, 170], eye: 1.1 },
  point: { L: [166, 318, 156, 368], R: [262, 258, 330, 222], eye: 1 },
  shrug: { L: [146, 304, 104, 284], R: [254, 304, 296, 284], eye: 1.1 },
  think: { L: [166, 318, 156, 368], R: [252, 296, 226, 236], eye: 0.9 },
  wave: { L: [166, 318, 156, 368], R: [262, 252, 286, 192], eye: 1 },
};

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerpArm = (a: Arm, b: Arm, t: number): Arm => [lerp(a[0], b[0], t), lerp(a[1], b[1], t), lerp(a[2], b[2], t), lerp(a[3], b[3], t)];

export interface MascotProps {
  pose: Pose;
  prevPose: Pose;
  poseStartFrame: number;
  words: { word: string; start: number; end: number }[];
  ink: string;
  scale?: number;
}

/** "Volt": a chip-headed stick figure. Poses blend with a spring; the mouth follows the narration timing. */
export const Mascot: React.FC<MascotProps> = ({ pose, prevPose, poseStartFrame, words, ink, scale = 1 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;

  const k = spring({ frame: frame - poseStartFrame, fps, config: { damping: 12, stiffness: 170, mass: 0.6 } });
  const a = POSES[prevPose] || POSES.idle;
  const b = POSES[pose] || POSES.idle;
  const L = lerpArm(a.L, b.L, k);
  let R = lerpArm(a.R, b.R, k);
  if (pose === 'wave') R = [R[0], R[1], R[2] + Math.sin(t * 9) * 14, R[3]];
  const eyeScale = lerp(a.eye, b.eye, k);

  const speaking = words.some((w) => t >= w.start - 0.02 && t <= w.end + 0.04);
  const mouthOpen = speaking ? 0.35 + 0.65 * Math.abs(Math.sin(t * 17)) : 0;

  // Blink for 4 frames about every 2.7s
  const blinkPhase = frame % Math.round(fps * 2.7);
  const blink = blinkPhase < 4 ? 0.1 : 1;

  const bob = Math.sin(t * 3.2) * 5;
  const tilt = Math.sin(t * 1.6) * 1.8;
  const hop = interpolate(k, [0, 0.35, 1], [0, -16, 0], { extrapolateRight: 'clamp' });

  const stroke = { stroke: ink, strokeWidth: 9, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' };

  return (
    <svg width={400 * scale} height={560 * scale} viewBox="0 0 400 560" style={{ overflow: 'visible' }}>
      <ellipse cx={200} cy={522} rx={90} ry={10} fill={ink} opacity={0.18} />
      <g transform={`translate(0 ${bob + hop})`}>
        {/* legs */}
        <path d="M200 360 L164 508 M200 360 L236 508" {...stroke} />
        {/* body */}
        <path d="M200 250 L200 360" {...stroke} />
        {/* arms */}
        <path d={`M200 272 L${L[0]} ${L[1]} L${L[2]} ${L[3]}`} {...stroke} />
        <path d={`M200 272 L${R[0]} ${R[1]} L${R[2]} ${R[3]}`} {...stroke} />
        {/* head (chip) */}
        <g transform={`rotate(${tilt} 200 190)`}>
          <path d="M150 156H132M150 176H132M150 196H132M150 216H132M250 156H268M250 176H268M250 196H268M250 216H268" {...stroke} strokeWidth={6} />
          <rect x={150} y={130} width={100} height={110} rx={24} {...stroke} />
          <ellipse cx={178} cy={172} rx={9} ry={9 * eyeScale * blink} fill={ink} />
          <ellipse cx={222} cy={172} rx={9} ry={9 * eyeScale * blink} fill={ink} />
          {speaking ? (
            <ellipse cx={200} cy={210} rx={15} ry={4 + mouthOpen * 14} fill={ink} />
          ) : (
            <path d="M184 206 Q200 222 216 206" {...stroke} strokeWidth={6} />
          )}
        </g>
      </g>
    </svg>
  );
};
