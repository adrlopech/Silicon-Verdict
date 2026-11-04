import React from 'react';
import { useCurrentFrame } from 'remotion';

export const VcselDepthProjector: React.FC = () => {
  const frame = useCurrentFrame();

  const scanBeamOffset = (frame * 4) % 180;
  const pulseOpacity = 0.5 + Math.sin(frame / 6) * 0.4;

  return (
    <div
      style={{
        width: '100%',
        height: '460px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '12px 10px',
        boxSizing: 'border-box',
        fontFamily: "'SF Pro Display', -apple-system, sans-serif",
      }}
    >
      {/* Top Header: Max 3 words, 28-34px */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          style={{
            fontSize: '32px',
            fontWeight: 900,
            letterSpacing: '1px',
            color: '#FFFFFF',
            textTransform: 'uppercase',
          }}
        >
          VCSEL DEPTH PROJECTION
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          940nm INFRARED
        </span>
      </div>

      {/* Giant 3D Dot Matrix Array Canvas */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        {/* Left: TrueDepth Emitter Housing */}
        <g transform="translate(140, 140)">
          <rect x="-80" y="-80" width="100" height="160" rx="16" fill="#141824" stroke="#007AFF" strokeWidth="2.5" />
          <circle cx="-30" cy="-25" r="24" fill="#0A0D14" stroke="#00F0FF" strokeWidth="2" />
          <text x="-30" y="35" fill="#00F0FF" fontSize="24" fontWeight="900" textAnchor="middle" fontFamily="monospace">
            VCSEL
          </text>
        </g>

        {/* 30,000 Dot Array Cone Visualization */}
        <g transform="translate(260, 140)">
          {[...Array(28)].map((_, i) => {
            const row = Math.floor(i / 7);
            const col = i % 7;
            const x = col * 70;
            const y = (row - 1.5) * 45;
            const dist = Math.sqrt(x * x + y * y);
            const isLit = (Math.sin(frame * 0.2 + dist * 0.05) + 1) > 1.2;
            return (
              <circle
                key={i}
                cx={x}
                cy={y}
                r={isLit ? 5.5 : 3.5}
                fill={isLit ? '#00F0FF' : '#5AC8FA'}
                opacity={isLit ? 0.95 : 0.45}
              />
            );
          })}
        </g>

        {/* Dynamic Sweeping Infrared Laser Plane */}
        <line
          x1={240 + scanBeamOffset * 2.8}
          y1="30"
          x2={240 + scanBeamOffset * 2.8}
          y2="250"
          stroke="#00F0FF"
          strokeWidth="3.5"
          opacity={pulseOpacity}
        />
      </svg>

      {/* Metrics Row */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '24px',
          borderTop: '2px solid rgba(255, 255, 255, 0.1)',
          paddingTop: '16px',
        }}
      >
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            INFRARED DOT MATRIX
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            30,000 DOTS
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            CARRIER WAVELENGTH
          </div>
          <div style={{ color: '#5AC8FA', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            940 nm
          </div>
        </div>
      </div>
    </div>
  );
};
