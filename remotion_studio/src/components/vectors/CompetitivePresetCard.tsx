import React from 'react';
import { useCurrentFrame } from 'remotion';

export const CompetitivePresetCard: React.FC = () => {
  const frame = useCurrentFrame();

  const wavePoints = [...Array(24)].map((_, i) => {
    const x = 20 + i * 34;
    const y = 30 + Math.sin(frame * 0.15 + i * 0.5) * 14;
    return `${x},${y}`;
  }).join(' ');

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
          COMPETITIVE PRESET BENCHMARK
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          1440P DLSS
        </span>
      </div>

      {/* Dual Giant Comparison Boxes */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', margin: '14px 0' }}>
        {/* Preset A */}
        <div
          style={{
            padding: '24px',
            background: '#141824',
            borderRadius: '20px',
            border: '2px solid rgba(142, 142, 147, 0.4)',
          }}
        >
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#8E8E93', letterSpacing: '1px', marginBottom: '8px' }}>
            NATIVE 1440P
          </div>
          <div style={{ fontSize: '54px', fontWeight: 900, color: '#FFFFFF', fontFamily: 'monospace' }}>
            58 <span style={{ fontSize: '26px', color: '#8E8E93' }}>FPS</span>
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#FF453A', marginTop: '6px' }}>
            1% Low: 36 FPS
          </div>
        </div>

        {/* Preset B (Winner) */}
        <div
          style={{
            padding: '24px',
            background: '#101F3D',
            borderRadius: '20px',
            border: '2.5px solid #00F0FF',
            boxShadow: '0 0 24px rgba(0, 240, 255, 0.35)',
          }}
        >
          <div style={{ fontSize: '24px', fontWeight: 900, color: '#00F0FF', letterSpacing: '1px', marginBottom: '8px' }}>
            DLSS QUALITY
          </div>
          <div style={{ fontSize: '54px', fontWeight: 900, color: '#FFFFFF', fontFamily: 'monospace' }}>
            94 <span style={{ fontSize: '26px', color: '#00F0FF' }}>FPS</span>
          </div>
          <div style={{ fontSize: '24px', fontWeight: 800, color: '#00F0FF', marginTop: '6px' }}>
            1% Low: 74 FPS
          </div>
        </div>
      </div>

      {/* Frame Pacing Wave: Clean Visual Metaphor */}
      <div style={{ background: '#080C14', borderRadius: '16px', padding: '16px', border: '1.5px solid #1C202B' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '24px', fontWeight: 800, color: '#8E8E93', fontFamily: 'monospace' }}>
            FRAME PACING STABILITY
          </span>
          <span style={{ fontSize: '24px', fontWeight: 900, color: '#00F0FF', fontFamily: 'monospace' }}>
            6.9 ms
          </span>
        </div>
        <svg width="100%" height="50" viewBox="0 0 800 50">
          <polyline
            fill="none"
            stroke="#00F0FF"
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={wavePoints}
          />
        </svg>
      </div>
    </div>
  );
};
