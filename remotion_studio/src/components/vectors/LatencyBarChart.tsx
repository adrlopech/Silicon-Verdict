import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const LatencyBarChart: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Enter animation for bars
  const fillProgress = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 90 },
  });

  // Micro jitter for live telemetry authenticity
  const jitterA = Math.sin(frame * 0.8) * 0.4;
  const jitterB = Math.cos(frame * 0.9) * 0.6;

  const width1 = interpolate(fillProgress, [0, 1], [0, 480]);
  const width2 = interpolate(fillProgress, [0, 1], [0, 760]);

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
          INTERCONNECT LATENCY
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          NANOSECOND TELEMETRY
        </span>
      </div>

      {/* Main Bar Comparisons */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '28px', margin: '20px 0' }}>
        {/* Bar 1: Baseline Architecture */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ color: '#8E8E93', fontSize: '26px', fontWeight: 800, fontFamily: 'monospace' }}>
              STANDARD BUS
            </span>
            <span style={{ color: '#8E8E93', fontSize: '32px', fontWeight: 900, fontFamily: 'monospace' }}>
              {(64.2 + jitterA).toFixed(1)} ns
            </span>
          </div>
          <div style={{ width: '100%', height: '38px', background: '#161B26', borderRadius: '18px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${width1}px`,
                height: '100%',
                background: 'linear-gradient(90deg, #334155 0%, #007AFF 100%)',
                borderRadius: '18px',
                boxShadow: '0 0 16px rgba(0, 122, 255, 0.4)',
              }}
            />
          </div>
        </div>

        {/* Bar 2: Ultra-Wide Optimized Bus */}
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ color: '#FFFFFF', fontSize: '26px', fontWeight: 900, fontFamily: 'monospace' }}>
              3D V-CACHE BUS
            </span>
            <span style={{ color: '#00F0FF', fontSize: '32px', fontWeight: 900, fontFamily: 'monospace' }}>
              {(11.4 + jitterB).toFixed(1)} ns
            </span>
          </div>
          <div style={{ width: '100%', height: '42px', background: '#161B26', borderRadius: '20px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${width2}px`,
                height: '100%',
                background: 'linear-gradient(90deg, #007AFF 0%, #00F0FF 100%)',
                borderRadius: '20px',
                boxShadow: '0 0 24px rgba(0, 240, 255, 0.7)',
              }}
            />
          </div>
        </div>
      </div>

      {/* Metrics Row: 48-60px figures with Neon Cyan / Ice Blue */}
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
            LATENCY DELTA
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            -82.2%
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            MEMORY ACCESS
          </div>
          <div style={{ color: '#5AC8FA', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            5.8x FASTER
          </div>
        </div>
      </div>
    </div>
  );
};
