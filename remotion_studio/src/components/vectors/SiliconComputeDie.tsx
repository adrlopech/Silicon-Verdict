import React from 'react';
import { useCurrentFrame } from 'remotion';

interface SiliconComputeDieProps {
  brand?: 'amd' | 'intel';
}

export const SiliconComputeDie: React.FC<SiliconComputeDieProps> = ({ brand = 'amd' }) => {
  const frame = useCurrentFrame();

  const dashOffset = (frame * 4) % 120;

  const isAmd = brand === 'amd';

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
          {isAmd ? 'ZEN COMPUTE COMPLEX' : 'COMPUTE DIE TOPOLOGY'}
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          {isAmd ? 'CCD ARCHITECTURE' : 'HYBRID TILES'}
        </span>
      </div>

      {/* Giant SVG Silicon Matrix Canvas */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        {/* Outer Package Die */}
        <rect
          x="10"
          y="10"
          width="820"
          height="260"
          rx="24"
          fill="#0B0F19"
          stroke="#007AFF"
          strokeWidth="3"
        />

        {/* Die Section 1: AMD Zen Cores vs Intel P-Cores */}
        <rect x="35" y="30" width="365" height="110" rx="16" fill="#141E33" stroke="#007AFF" strokeWidth="2" />
        <text x="217" y="78" fill="#FFFFFF" fontSize="28" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          {isAmd ? '8x ZEN CORES' : '8x P-CORES'}
        </text>
        <text x="217" y="115" fill="#5AC8FA" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          {isAmd ? '5.7 GHz BOOST' : '5.7 GHz TURBO'}
        </text>

        {/* Die Section 2: AMD I/O Die vs Intel E-Cores */}
        <rect x="440" y="30" width="365" height="110" rx="16" fill="#141E33" stroke="#007AFF" strokeWidth="2" />
        <text x="622" y="78" fill="#FFFFFF" fontSize="28" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          {isAmd ? 'I/O CONTROLLER DIE' : '16x E-CORES'}
        </text>
        <text x="622" y="115" fill="#5AC8FA" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          {isAmd ? 'INFINITY FABRIC' : 'DENSE CLUSTERS'}
        </text>

        {/* Central High-Speed Crossbar Bus with Pulsing Data Packets */}
        <line
          x1="35"
          y1="160"
          x2="805"
          y2="160"
          stroke="#00F0FF"
          strokeWidth="4"
          strokeDasharray="12 10"
          strokeDashoffset={-dashOffset}
        />
        <circle cx={60 + ((frame * 6) % 700)} cy="160" r="9" fill="#FFFFFF" />
        <circle cx={760 - ((frame * 5) % 700)} cy="160" r="8" fill="#00F0FF" />

        {/* Shared L3 Cache / 3D V-Cache Stack */}
        <rect x="35" y="180" width="770" height="74" rx="16" fill="#101827" stroke="#00F0FF" strokeWidth="2.5" />
        <text x="420" y="228" fill="#FFFFFF" fontSize="30" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          {isAmd ? '3D CACHE SRAM DIE • 96MB L3' : '36MB L3 SMART CACHE'}
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
            L3 CACHE DENSITY
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            {isAmd ? '96 MB' : '36 MB'}
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            CACHE ACCESS
          </div>
          <div style={{ color: '#5AC8FA', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            10.8 ns
          </div>
        </div>
      </div>
    </div>
  );
};
