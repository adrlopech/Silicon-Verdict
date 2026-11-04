import React from 'react';
import { useCurrentFrame } from 'remotion';

export const FrametimeTachometer: React.FC = () => {
  const frame = useCurrentFrame();

  // Micro-jitter of frametimes
  const needleJitter = Math.sin(frame * 0.75) * 5.0 + Math.cos(frame * 1.2) * 3.0;
  const needleAngle = -25 + needleJitter; // degrees

  const fpsVal = Math.round(144 + needleJitter * 2.0);
  const lowVal = (98.4 + needleJitter * 0.7).toFixed(1);

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
          FRAME PACING STABILITY
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          PRESENTMON 1% LOW
        </span>
      </div>

      {/* Giant SVG Tachometer Canvas */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        {/* Gauge Background Disc */}
        <circle
          cx="420"
          cy="150"
          r="125"
          fill="#0B0F19"
          stroke="#007AFF"
          strokeWidth="3.5"
        />

        {/* Dial Ticks */}
        {[...Array(21)].map((_, i) => {
          const angle = -130 + i * 13;
          const rad = (angle * Math.PI) / 180;
          const x1 = 420 + Math.cos(rad) * 105;
          const y1 = 150 + Math.sin(rad) * 105;
          const x2 = 420 + Math.cos(rad) * 120;
          const y2 = 150 + Math.sin(rad) * 120;
          const isHighlight = i % 4 === 0;
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke={isHighlight ? '#00F0FF' : 'rgba(255, 255, 255, 0.4)'}
              strokeWidth={isHighlight ? 3.5 : 2}
            />
          );
        })}

        {/* Active Arc */}
        <circle
          cx="420"
          cy="150"
          r="95"
          stroke="#00F0FF"
          strokeWidth="10"
          strokeDasharray="420"
          strokeDashoffset={180 - needleAngle * 1.2}
          strokeLinecap="round"
          fill="none"
        />

        {/* Rotating Needle */}
        <g transform={`rotate(${needleAngle}, 420, 150)`}>
          <line
            x1="420"
            y1="150"
            x2="420"
            y2="50"
            stroke="#00F0FF"
            strokeWidth="5"
            strokeLinecap="round"
          />
          <circle cx="420" cy="150" r="16" fill="#007AFF" stroke="#FFFFFF" strokeWidth="3" />
        </g>

        {/* Center Live FPS Readout */}
        <text x="420" y="195" fill="#FFFFFF" fontSize="38" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          {fpsVal} FPS
        </text>
      </svg>

      {/* Metrics Row: 48-60px figures */}
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
            AVERAGE FRAMES
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            {fpsVal} FPS
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            1% LOW STABILITY
          </div>
          <div style={{ color: '#5AC8FA', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            {lowVal} FPS
          </div>
        </div>
      </div>
    </div>
  );
};
