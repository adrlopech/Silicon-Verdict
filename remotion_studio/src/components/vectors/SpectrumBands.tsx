import React from 'react';
import { useCurrentFrame } from 'remotion';

export const SpectrumBands: React.FC = () => {
  const frame = useCurrentFrame();

  // Packet animation offsets
  const pulse24 = (frame * 5) % 100;
  const pulse50 = (frame * 8) % 100;

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
      }}
    >
      {/* Top Header: Max 3 words, 28-34px */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span
          style={{
            color: '#FFFFFF',
            fontSize: '32px',
            fontWeight: 900,
            letterSpacing: '1px',
            textTransform: 'uppercase',
            fontFamily: "'SF Pro Display', sans-serif",
          }}
        >
          SPECTRUM BAND ISOLATION
        </span>
        <span
          style={{
            color: '#00F0FF',
            fontSize: '26px',
            fontWeight: 800,
            fontFamily: 'monospace',
          }}
        >
          DUAL-BAND
        </span>
      </div>

      {/* SVG Frequency Canvas */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id="bandGrad24" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#FF453A" stopOpacity={0.8} />
            <stop offset="100%" stopColor="#FF9F0A" stopOpacity={0.8} />
          </linearGradient>
          <linearGradient id="bandGrad50" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#007AFF" stopOpacity={0.9} />
            <stop offset="100%" stopColor="#00F0FF" stopOpacity={0.9} />
          </linearGradient>
        </defs>

        {/* 2.4 GHz Congested Band Row */}
        <g transform="translate(20, 20)">
          {/* Label */}
          <text x="0" y="32" fill="#FF453A" fontSize="28" fontWeight="bold" fontFamily="monospace">
            2.4 GHz
          </text>
          <text x="140" y="32" fill="#8E8E93" fontSize="24" fontFamily="monospace">
            CROWDED (3 CHANNELS)
          </text>

          {/* Bar track */}
          <rect x="0" y="48" width="800" height="42" rx="12" fill="#1C202B" stroke="#FF453A" strokeWidth="2" />
          {/* Overlapping crowded interference lobes */}
          <rect x="4" y="52" width="260" height="34" rx="8" fill="url(#bandGrad24)" opacity="0.6" />
          <rect x="230" y="52" width="270" height="34" rx="8" fill="url(#bandGrad24)" opacity="0.8" />
          <rect x="460" y="52" width="280" height="34" rx="8" fill="url(#bandGrad24)" opacity="0.6" />
          {/* Noise spike indicator */}
          <circle cx={180 + ((pulse24 * 5) % 450)} cy="69" r="8" fill="#FFFFFF" />
        </g>

        {/* 5 GHz Clean Wideband Row */}
        <g transform="translate(20, 150)">
          {/* Label */}
          <text x="0" y="32" fill="#00F0FF" fontSize="28" fontWeight="bold" fontFamily="monospace">
            5.0 GHz
          </text>
          <text x="140" y="32" fill="#5AC8FA" fontSize="24" fontFamily="monospace">
            ZERO RF INTERFERENCE
          </text>

          {/* Bar track */}
          <rect x="0" y="48" width="800" height="42" rx="12" fill="#1C202B" stroke="#00F0FF" strokeWidth="2.5" />
          {/* Broad, non-overlapping 80 MHz channel */}
          <rect x="4" y="52" width="792" height="34" rx="8" fill="url(#bandGrad50)" />
          {/* Smooth streaming pulse */}
          <circle cx={40 + ((pulse50 * 7.5) % 720)} cy="69" r="10" fill="#FFFFFF" />
        </g>
      </svg>

      {/* Metrics Row: 48-60px figures with Neon Cyan illumination, labels >= 24px */}
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
            BANDWIDTH
          </div>
          <div style={{ color: '#00F0FF', fontSize: '52px', fontWeight: 900, fontFamily: 'monospace' }}>
            +240%
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            INTERFERENCE
          </div>
          <div style={{ color: '#5AC8FA', fontSize: '52px', fontWeight: 900, fontFamily: 'monospace' }}>
            -38 dB
          </div>
        </div>
      </div>
    </div>
  );
};
