import React from 'react';
import { useCurrentFrame } from 'remotion';

export const DynamicBackground: React.FC = () => {
  const frame = useCurrentFrame();

  // Subtle continuous drift of technical grid
  const gridOffsetY = (frame * 0.75) % 64;
  const gridOffsetX = (frame * 0.35) % 64;

  // Slow non-harmonic oscillation of ambient glowing orbs
  const orb1X = 250 + Math.sin(frame / 40) * 70;
  const orb1Y = 480 + Math.cos(frame / 55) * 110;

  const orb2X = 820 + Math.cos(frame / 45) * 85;
  const orb2Y = 1350 + Math.sin(frame / 35) * 95;

  const orb3X = 540 + Math.sin(frame / 50) * 60;
  const orb3Y = 960 + Math.cos(frame / 60) * 80;

  return (
    <div
      style={{
        position: 'absolute',
        inset: 0,
        backgroundColor: '#07090E',
        overflow: 'hidden',
        width: 1080,
        height: 1920,
      }}
    >
      {/* Orb 1: Electric Blue Bloom */}
      <div
        style={{
          position: 'absolute',
          left: orb1X - 260,
          top: orb1Y - 260,
          width: 520,
          height: 520,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(0, 122, 255, 0.16) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* Orb 2: Cyan Ambient Highlight */}
      <div
        style={{
          position: 'absolute',
          left: orb2X - 290,
          top: orb2Y - 290,
          width: 580,
          height: 580,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(0, 240, 255, 0.11) 0%, transparent 70%)',
          pointerEvents: 'none',
        }}
      />

      {/* Orb 3: Subtle Deep Sapphire Core */}
      <div
        style={{
          position: 'absolute',
          left: orb3X - 200,
          top: orb3Y - 200,
          width: 400,
          height: 400,
          borderRadius: '50%',
          background:
            'radial-gradient(circle, rgba(0, 122, 255, 0.08) 0%, transparent 65%)',
          pointerEvents: 'none',
        }}
      />

      {/* Technical Dot-Grid Matrix with procedural continuous drift */}
      <svg
        width="100%"
        height="100%"
        style={{
          position: 'absolute',
          inset: 0,
          opacity: 0.12,
          pointerEvents: 'none',
        }}
      >
        <defs>
          <pattern
            id="tech-grid"
            width="64"
            height="64"
            patternUnits="userSpaceOnUse"
            patternTransform={`translate(${gridOffsetX}, ${gridOffsetY})`}
          >
            <path
              d="M 64 0 L 0 0 0 64"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="0.75"
            />
            <circle cx="0" cy="0" r="1.5" fill="#00F0FF" />
          </pattern>
        </defs>
        <rect width="100%" height="100%" fill="url(#tech-grid)" />
      </svg>

      {/* Top and Bottom Technical Precision Crosshairs & Boundary Markers */}
      <div
        style={{
          position: 'absolute',
          top: 70,
          left: 56,
          right: 56,
          display: 'flex',
          justifyContent: 'space-between',
          fontFamily: "'SF Pro Display', -apple-system, sans-serif",
          fontSize: '13px',
          fontWeight: 700,
          letterSpacing: '1.5px',
          color: 'rgba(142, 142, 147, 0.55)',
          textTransform: 'uppercase',
          pointerEvents: 'none',
        }}
      >
        <span>SV-SYS // 30 FPS VECTOR ENGINE</span>
        <span>RES: 1080x1920 • RECT 9:16</span>
      </div>

      <div
        style={{
          position: 'absolute',
          bottom: 70,
          left: 56,
          right: 56,
          display: 'flex',
          justifyContent: 'space-between',
          fontFamily: "'SF Pro Display', -apple-system, sans-serif",
          fontSize: '12px',
          fontWeight: 700,
          letterSpacing: '1.4px',
          color: 'rgba(142, 142, 147, 0.45)',
          textTransform: 'uppercase',
          pointerEvents: 'none',
        }}
      >
        <span>TELEMETRY PRECISION: ±0.001ms</span>
        <span style={{ color: '#007AFF' }}>@SILICONVERDICT</span>
      </div>
    </div>
  );
};
