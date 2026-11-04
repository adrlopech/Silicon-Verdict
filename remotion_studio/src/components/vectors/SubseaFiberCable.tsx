import React from 'react';
import { useCurrentFrame } from 'remotion';

export const SubseaFiberCable: React.FC = () => {
  const frame = useCurrentFrame();

  const pulseOffset = (frame * 6) % 120;
  const coreGlow = 0.6 + Math.sin(frame * 0.15) * 0.35;

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
          SUBSEA OPTICAL INFRASTRUCTURE
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          DWDM TRUNK
        </span>
      </div>

      {/* Giant Cross-Section + Pulse Canvas */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        <defs>
          <radialGradient id="cableCoreGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#00F0FF" stopOpacity={coreGlow} />
            <stop offset="70%" stopColor="#007AFF" stopOpacity="0.3" />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Cable Cross-Section Layers (Center: 240, 140) */}
        <g transform="translate(240, 140)">
          <circle r="120" fill="#0E121A" stroke="#1C202B" strokeWidth="6" />
          <circle r="105" fill="#131822" stroke="rgba(255,255,255,0.2)" strokeWidth="2" strokeDasharray="6 4" />

          {/* High-tensile steel armor wires */}
          {[...Array(16)].map((_, i) => {
            const angle = (i * 22.5 * Math.PI) / 180;
            const cx = Math.cos(angle) * 88;
            const cy = Math.sin(angle) * 88;
            return <circle key={i} cx={cx} cy={cy} r="6" fill="#2A3142" stroke="#8E8E93" strokeWidth="1" />;
          })}

          {/* Copper power tube */}
          <circle r="68" fill="#1A2436" stroke="#5AC8FA" strokeWidth="3" opacity="0.8" />
          {/* Central core */}
          <circle r="46" fill="#0A0D14" stroke="#007AFF" strokeWidth="2" />
          <circle r="32" fill="url(#cableCoreGlow)" />

          {/* Fiber Strands */}
          {[...Array(8)].map((_, i) => {
            const angle = (i * 45 * Math.PI) / 180 + (frame * 0.02);
            const fx = Math.cos(angle) * 20;
            const fy = Math.sin(angle) * 20;
            return <circle key={i} cx={fx} cy={fy} r="3.5" fill="#00F0FF" />;
          })}
          <circle r="4" fill="#FFFFFF" />
        </g>

        {/* Longitudinal Waveguide Stream (Right side) */}
        <g transform="translate(520, 100)">
          <text x="140" y="-12" fill="#00F0FF" fontSize="26" fontWeight="900" textAnchor="middle" fontFamily="monospace">
            PHOTON SPEED
          </text>
          <rect x="0" y="0" width="280" height="50" rx="12" fill="#0E121A" stroke="#007AFF" strokeWidth="2" />
          <line x1="15" y1="25" x2="265" y2="25" stroke="#007AFF" strokeWidth="5" opacity="0.4" />
          {/* Travelling photon bursts */}
          <circle cx={15 + ((pulseOffset * 2.2) % 250)} cy="25" r="7" fill="#00F0FF" />
          <circle cx={15 + (((pulseOffset * 2.2) + 100) % 250)} cy="25" r="6" fill="#FFFFFF" />
          <text x="140" y="85" fill="#8E8E93" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
            204,190 km/s
          </text>
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
            ABYSSAL DEPTH
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            8,420 m
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            TRUNK CAPACITY
          </div>
          <div style={{ color: '#5AC8FA', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            340 Tbps
          </div>
        </div>
      </div>
    </div>
  );
};
