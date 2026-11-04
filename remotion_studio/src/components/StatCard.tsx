import React from 'react';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

export interface StatCardProps {
  label?: string; // the key term or number, shown huge
  caption?: string; // optional small line under it
}

/**
 * Honest, data-free beat: shows only the term or figure taken from the script.
 * Used where a generic chart would imply measurements we do not have.
 */
export const StatCard: React.FC<StatCardProps> = ({ label = '', caption }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const glow = 0.5 + 0.5 * Math.sin(t * 3);
  const lineW = interpolate(frame, [0, 14], [0, 100], { extrapolateRight: 'clamp' });
  const size = label.length > 22 ? 78 : label.length > 14 ? 96 : 120;

  return (
    <div
      style={{
        width: 828,
        minHeight: 466,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 28,
        textAlign: 'center',
      }}
    >
      <div
        style={{
          height: 4,
          width: `${lineW}%`,
          background: 'linear-gradient(90deg, transparent, #00F0FF, transparent)',
          opacity: 0.4 + 0.5 * glow,
        }}
      />
      <div
        style={{
          fontFamily: "'SF Pro Display', -apple-system, 'Helvetica Neue', Arial, sans-serif",
          fontSize: size,
          fontWeight: 900,
          lineHeight: 1.05,
          letterSpacing: '-0.01em',
          color: '#FFFFFF',
          textTransform: 'uppercase',
          textShadow: `0 0 ${24 + 20 * glow}px rgba(0,240,255,0.55)`,
          wordBreak: 'keep-all',
        }}
      >
        {label}
      </div>
      {caption && (
        <div
          style={{
            fontFamily: 'monospace',
            fontSize: 26,
            fontWeight: 800,
            letterSpacing: '0.14em',
            color: '#00F0FF',
            textTransform: 'uppercase',
          }}
        >
          {caption}
        </div>
      )}
      <div
        style={{
          height: 4,
          width: `${lineW}%`,
          background: 'linear-gradient(90deg, transparent, #007AFF, transparent)',
          opacity: 0.4 + 0.5 * (1 - glow),
        }}
      />
    </div>
  );
};
