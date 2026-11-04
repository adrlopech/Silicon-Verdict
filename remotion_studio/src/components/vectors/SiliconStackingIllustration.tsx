import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';

export const SiliconStackingIllustration: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Smooth elastic descending and docking animation of the 3D Cache Die
  const dockSpring = spring({
    frame: frame % 180,
    fps,
    config: { damping: 14, stiffness: 90, mass: 0.9 },
  });

  // Cache die descends from y=24 down to y=68 (docked directly on copper micro-contacts at y=118)
  const cacheY = interpolate(dockSpring, [0, 1], [18, 68]);
  const isDocked = (frame % 180) > 45;
  const contactGlow = isDocked ? 0.6 + Math.sin(frame / 4) * 0.4 : 0.2;
  const sparkScale = isDocked ? 1.0 + Math.sin(frame / 3) * 0.25 : 0.0;

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
          3D SILICON HYBRID BONDING
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          TSMC SoIC 9μm
        </span>
      </div>

      {/* SVG Canvas for 3D Stacking Cross-Section */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id="cacheGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#007AFF" stopOpacity="0.9" />
            <stop offset="100%" stopColor="#0040A8" stopOpacity="0.95" />
          </linearGradient>
          <linearGradient id="baseCcdGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#141E33" />
            <stop offset="100%" stopColor="#0B101D" />
          </linearGradient>
          <linearGradient id="spacerGradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#1C2538" />
            <stop offset="100%" stopColor="#101726" />
          </linearGradient>
          <filter id="copperGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* 1. Silicon Interposer / Substrate Base */}
        <rect x="20" y="215" width="800" height="45" rx="10" fill="#0A0E17" stroke="#1E2A40" strokeWidth="2.5" />
        <text x="420" y="244" fill="#8E8E93" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          ORGANIC PACKAGE SUBSTRATE // TSV BUS
        </text>

        {/* 2. Base Silicon: Zen Compute Complex Die (CCD) */}
        <rect x="40" y="128" width="760" height="80" rx="14" fill="url(#baseCcdGradient)" stroke="#007AFF" strokeWidth="2.5" />
        <text x="420" y="174" fill="#FFFFFF" fontSize="28" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          ZEN COMPUTE COMPLEX (CCD) • BASE SILICON
        </text>

        {/* 3. Structural Silicon Spacers (flanking left and right to match height) */}
        <rect x="40" y="68" width="190" height="52" rx="8" fill="url(#spacerGradient)" stroke="#3A4A6B" strokeWidth="2" strokeDasharray="6 4" />
        <text x="135" y="100" fill="#8E8E93" fontSize="20" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          STRUCTURAL Si
        </text>

        <rect x="610" y="68" width="190" height="52" rx="8" fill="url(#spacerGradient)" stroke="#3A4A6B" strokeWidth="2" strokeDasharray="6 4" />
        <text x="705" y="100" fill="#8E8E93" fontSize="20" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          STRUCTURAL Si
        </text>

        {/* 4. TSMC Direct Copper-to-Copper Micro-Bonding Array (Micro-Bumps) */}
        {Array.from({ length: 18 }).map((_, idx) => {
          const cx = 250 + idx * 19.5;
          return (
            <g key={`copper-contact-${idx}`}>
              {/* Copper Contact Pad */}
              <rect
                x={cx - 5}
                y="118"
                width="10"
                height="10"
                rx="2"
                fill="#FF9F0A"
                stroke="#FFD60A"
                strokeWidth="1.5"
                filter="url(#copperGlow)"
              />
              {/* Active Hybrid Bonding Spark / Current Pulse */}
              {isDocked && (
                <circle
                  cx={cx}
                  cy="123"
                  r={3.5 * sparkScale}
                  fill="#00F0FF"
                  opacity={contactGlow}
                />
              )}
            </g>
          );
        })}

        {/* 5. 3D V-Cache SRAM Die (Descending and Docking Animation) */}
        <g transform={`translate(0, ${cacheY - 68})`}>
          <rect
            x="240"
            y="68"
            width="360"
            height="50"
            rx="12"
            fill="url(#cacheGradient)"
            stroke="#00F0FF"
            strokeWidth="3"
            filter="drop-shadow(0 0 16px rgba(0, 240, 255, 0.45))"
          />
          <text x="420" y="101" fill="#FFFFFF" fontSize="22" fontWeight="900" textAnchor="middle" fontFamily="monospace">
            64MB 3D V-CACHE SRAM DIE
          </text>
        </g>

        {/* Docking Indicator Arrows (visible while descending) */}
        {!isDocked && (
          <g opacity={1 - dockSpring}>
            <path d="M 320 20 L 320 50 M 310 40 L 320 50 L 330 40" stroke="#00F0FF" strokeWidth="3" fill="none" />
            <path d="M 520 20 L 520 50 M 510 40 L 520 50 L 530 40" stroke="#00F0FF" strokeWidth="3" fill="none" />
          </g>
        )}
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
            HYBRID BOND PITCH
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            9 μm
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            INTERCONNECT SPEED
          </div>
          <div style={{ color: '#5AC8FA', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            2.5 TB/s
          </div>
        </div>
      </div>
    </div>
  );
};
