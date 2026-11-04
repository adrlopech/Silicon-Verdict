import React from 'react';
import { useCurrentFrame } from 'remotion';

export const GpsRelativityOrbit: React.FC = () => {
  const frame = useCurrentFrame();

  const orbitAngle = (frame * 0.4) % 360;
  const rad = (orbitAngle * Math.PI) / 180;

  const earthX = 420;
  const earthY = 140;

  const sat1X = earthX + Math.cos(rad) * 320;
  const sat1Y = earthY + Math.sin(rad) * 90;

  const sat2X = earthX + Math.cos(rad + (Math.PI * 2 / 3)) * 320;
  const sat2Y = earthY + Math.sin(rad + (Math.PI * 2 / 3)) * 90;

  const sat3X = earthX + Math.cos(rad + (Math.PI * 4 / 3)) * 320;
  const sat3Y = earthY + Math.sin(rad + (Math.PI * 4 / 3)) * 90;

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
          EINSTEIN RELATIVISTIC DRIFT
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          MEO ORBIT
        </span>
      </div>

      {/* Giant Orbital Canvas */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        {/* Orbital Ellipse */}
        <ellipse
          cx={earthX}
          cy={earthY}
          rx="320"
          ry="90"
          fill="none"
          stroke="rgba(0, 122, 255, 0.4)"
          strokeWidth="2.5"
          strokeDasharray="6 6"
        />

        {/* Earth Geoid */}
        <circle cx={earthX} cy={earthY} r="65" fill="#0A0D14" stroke="#007AFF" strokeWidth="3.5" />
        <text
          x={earthX}
          y={earthY + 8}
          fill="#FFFFFF"
          fontSize="24"
          fontWeight="900"
          textAnchor="middle"
          fontFamily="monospace"
        >
          EARTH
        </text>

        {/* Satellite 1 Beam & Body */}
        <line x1={sat1X} y1={sat1Y} x2={earthX} y2={earthY} stroke="#00F0FF" strokeWidth="2" strokeDasharray="4 4" opacity="0.7" />
        <g transform={`translate(${sat1X}, ${sat1Y})`}>
          <rect x="-16" y="-12" width="32" height="24" rx="6" fill="#1C202B" stroke="#00F0FF" strokeWidth="2.5" />
          <line x1="-34" y1="0" x2="-16" y2="0" stroke="#00F0FF" strokeWidth="4" />
          <line x1="16" y1="0" x2="34" y2="0" stroke="#00F0FF" strokeWidth="4" />
          <circle cx="0" cy="0" r="4" fill="#FFFFFF" />
        </g>

        {/* Satellite 2 */}
        <g transform={`translate(${sat2X}, ${sat2Y})`}>
          <rect x="-14" y="-10" width="28" height="20" rx="5" fill="#1C202B" stroke="#5AC8FA" strokeWidth="2" />
          <line x1="-28" y1="0" x2="-14" y2="0" stroke="#5AC8FA" strokeWidth="3" />
          <line x1="14" y1="0" x2="28" y2="0" stroke="#5AC8FA" strokeWidth="3" />
        </g>

        {/* Satellite 3 */}
        <g transform={`translate(${sat3X}, ${sat3Y})`}>
          <rect x="-14" y="-10" width="28" height="20" rx="5" fill="#1C202B" stroke="#5AC8FA" strokeWidth="2" />
          <line x1="-28" y1="0" x2="-14" y2="0" stroke="#5AC8FA" strokeWidth="3" />
          <line x1="14" y1="0" x2="28" y2="0" stroke="#5AC8FA" strokeWidth="3" />
        </g>
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
            DAILY TIME DILATION
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            +38.6 μs/day
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            UNMASKED DRIFT
          </div>
          <div style={{ color: '#5AC8FA', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            11.4 km/day
          </div>
        </div>
      </div>
    </div>
  );
};
