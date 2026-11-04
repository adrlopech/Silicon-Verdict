import React from 'react';
import { useCurrentFrame } from 'remotion';

export const ThermalDissipationIllustration: React.FC = () => {
  const frame = useCurrentFrame();

  // Pulsing thermal hotspot intensity and expanding heat waves
  const heatPulse = 0.8 + Math.sin(frame / 6) * 0.2;
  const wave1R = 25 + ((frame * 2.2) % 65);
  const wave2R = 25 + (((frame * 2.2) + 32) % 65);
  const wave1Opacity = Math.max(0, 1 - wave1R / 65);
  const wave2Opacity = Math.max(0, 1 - wave2R / 65);

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
          CONCENTRATED THERMAL LOAD
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#FF9F0A', fontFamily: 'monospace' }}>
          HOTSPOT BARRIER
        </span>
      </div>

      {/* SVG Canvas for Thermal Dissipation Cross-Section */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id="ihsGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#2E3A4E" />
            <stop offset="100%" stopColor="#1E2738" />
          </linearGradient>
          <radialGradient id="hotspotGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FF3B30" stopOpacity="0.95" />
            <stop offset="45%" stopColor="#FF9500" stopOpacity="0.75" />
            <stop offset="100%" stopColor="#FFCC00" stopOpacity="0.0" />
          </radialGradient>
        </defs>

        {/* 1. Integrated Heat Spreader (IHS) & Cooler Baseplate */}
        <rect x="25" y="15" width="790" height="48" rx="8" fill="url(#ihsGrad)" stroke="#5AC8FA" strokeWidth="2" />
        <text x="420" y="46" fill="#FFFFFF" fontSize="26" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          NICKEL-PLATED COPPER IHS // COOLER INTERFACE
        </text>

        {/* Thermal Resistance Barrier Line (extra silicon layer on top of compute die) */}
        <line x1="40" y1="72" x2="800" y2="72" stroke="#FF9F0A" strokeWidth="3" strokeDasharray="8 6" />

        {/* 2. Top 3D V-Cache Silicon Die (Stacking Barrier) */}
        <rect x="200" y="80" width="440" height="48" rx="8" fill="#141E33" stroke="#FF9F0A" strokeWidth="2.5" />
        <text x="420" y="112" fill="#FF9F0A" fontSize="24" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          3D V-CACHE SRAM // THERMAL BLANKET
        </text>

        {/* 3. Base Silicon Zen Compute Complex Die (CCD) */}
        <rect x="50" y="140" width="740" height="110" rx="14" fill="#0B111D" stroke="#007AFF" strokeWidth="2.5" />
        <text x="145" y="175" fill="#8E8E93" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          ZEN CORES
        </text>
        <text x="695" y="175" fill="#8E8E93" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          ZEN CORES
        </text>

        {/* 4. Concentrated Hotspot Core (Underneath the 3D Cache Stack) */}
        <ellipse cx="420" cy="195" rx="150" ry="48" fill="url(#hotspotGrad)" opacity={heatPulse} />
        <circle cx="295" cy="195" r="12" fill="#FF453A" stroke="#FFFFFF" strokeWidth="2" filter="drop-shadow(0 0 10px #FF3B30)" />
        <text x="430" y="203" fill="#FFFFFF" fontSize="22" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          HOTSPOT: 185 W/cm²
        </text>

        {/* Expanding Thermal Shockwaves */}
        <ellipse cx="420" cy="195" rx={wave1R * 2.2} ry={wave1R * 0.75} fill="none" stroke="#FF453A" strokeWidth="2.5" opacity={wave1Opacity} />
        <ellipse cx="420" cy="195" rx={wave2R * 2.2} ry={wave2R * 0.75} fill="none" stroke="#FF9F0A" strokeWidth="2" opacity={wave2Opacity} />

        {/* Rising Heat Flux Arrows trying to escape toward IHS */}
        <g stroke="#FF9F0A" strokeWidth="3" fill="none">
          <path d="M 330 140 L 330 110 M 322 120 L 330 110 L 338 120" />
          <path d="M 420 140 L 420 110 M 412 120 L 420 110 L 428 120" />
          <path d="M 510 140 L 510 110 M 502 120 L 510 110 L 518 120" />
        </g>
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
            THERMAL DENSITY
          </div>
          <div style={{ color: '#FF9F0A', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            185 W/cm²
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            HOTSPOT DELTA
          </div>
          <div style={{ color: '#FF453A', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            +14.2 °C
          </div>
        </div>
      </div>
    </div>
  );
};
