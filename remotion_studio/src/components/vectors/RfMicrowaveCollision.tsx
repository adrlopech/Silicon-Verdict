import React from 'react';
import { useCurrentFrame } from 'remotion';

export const RfMicrowaveCollision: React.FC = () => {
  const frame = useCurrentFrame();

  const wifiPhase = frame * 0.18;
  const microwavePhase = frame * 0.28;
  const collisionIntensity = Math.abs(Math.sin(frame * 0.12));

  // Generate sine wave path for Wi-Fi (2.4 GHz) across 820px canvas
  const wifiWavePoints: string[] = [];
  for (let x = 90; x <= 400; x += 12) {
    const y = 140 + Math.sin((x * 0.045) - wifiPhase) * 36 * (1 - (x - 90) / 480);
    wifiWavePoints.push(`${x},${y.toFixed(1)}`);
  }
  const wifiPath = `M ${wifiWavePoints.join(' L ')}`;

  // Generate chaotic wave for Microwave (2.45 GHz)
  const microWavePoints: string[] = [];
  for (let x = 740; x >= 420; x -= 12) {
    const chaos = Math.sin(frame * 0.3 + x * 0.02) * 10;
    const y = 140 + Math.sin((x * 0.06) + microwavePhase) * (50 + chaos) * (1 - (740 - x) / 500);
    microWavePoints.push(`${x},${y.toFixed(1)}`);
  }
  const microPath = `M ${microWavePoints.join(' L ')}`;

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
      {/* Top Header: Max 3 words, 28-34px Bold uppercase */}
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
          2.45 GHz COLLISION
        </span>
        <span
          style={{
            color: '#FF453A',
            fontSize: '26px',
            fontWeight: 800,
            fontFamily: 'monospace',
          }}
        >
          ISM OVERLAP
        </span>
      </div>

      {/* Giant SVG Waveform & Interference Visual Canvas */}
      <svg width="100%" height="260" viewBox="0 0 840 260" style={{ overflow: 'visible' }}>
        <defs>
          <radialGradient id="collisionGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#FF453A" stopOpacity={0.5 + collisionIntensity * 0.4} />
            <stop offset="70%" stopColor="#FF9F0A" stopOpacity={0.2} />
            <stop offset="100%" stopColor="transparent" stopOpacity="0" />
          </radialGradient>
          <filter id="glowWifi" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Central Collision Aura */}
        <circle cx="410" cy="140" r={80 + collisionIntensity * 40} fill="url(#collisionGlow)" />

        {/* Left Emitter: Wi-Fi Router */}
        <g transform="translate(30, 80)">
          <rect width="70" height="110" rx="12" fill="#1C202B" stroke="#00F0FF" strokeWidth="3" />
          {/* Dual Antennas */}
          <line x1="18" y1="0" x2="18" y2="-40" stroke="#00F0FF" strokeWidth="4" />
          <line x1="52" y1="0" x2="52" y2="-40" stroke="#00F0FF" strokeWidth="4" />
          <circle cx="18" cy="-42" r="5" fill="#00F0FF" />
          <circle cx="52" cy="-42" r="5" fill="#00F0FF" />
          <text x="35" y="65" fill="#00F0FF" fontSize="24" fontWeight="900" textAnchor="middle" fontFamily="monospace">
            WI-FI
          </text>
        </g>

        {/* Right Emitter: 1000W Magnetron */}
        <g transform="translate(730, 70)">
          <rect width="80" height="120" rx="12" fill="#1C202B" stroke="#FF453A" strokeWidth="3" />
          <circle cx="40" cy="50" r="22" fill="#0A0D14" stroke="#FF9F0A" strokeWidth="2.5" strokeDasharray="6 4" />
          <text x="40" y="100" fill="#FF453A" fontSize="24" fontWeight="900" textAnchor="middle" fontFamily="monospace">
            1000W
          </text>
        </g>

        {/* Clean Wi-Fi Carrier Wave */}
        <path d={wifiPath} fill="none" stroke="#00F0FF" strokeWidth="4.5" filter="url(#glowWifi)" />

        {/* Chaotic Magnetron Wave */}
        <path d={microPath} fill="none" stroke="#FF453A" strokeWidth="5" />

        {/* Dynamic Collision Sparks */}
        {[...Array(8)].map((_, i) => {
          const angle = (frame * 6 + i * 45) * (Math.PI / 180);
          const dist = 40 + (Math.sin(frame * 0.2 + i) + 1) * 28;
          const sx = 410 + Math.cos(angle) * dist;
          const sy = 140 + Math.sin(angle) * dist;
          return (
            <circle
              key={i}
              cx={sx}
              cy={sy}
              r={3.5}
              fill={i % 2 === 0 ? '#00F0FF' : '#FF9F0A'}
              opacity={0.9}
            />
          );
        })}

        {/* Center Badge: Minimum 24px text */}
        <g transform="translate(410, 140)">
          <rect x="-110" y="-24" width="220" height="48" rx="24" fill="rgba(10, 13, 20, 0.95)" stroke="#FF453A" strokeWidth="2" />
          <text y="8" fill="#FFFFFF" fontSize="24" fontWeight="900" textAnchor="middle" fontFamily="monospace">
            RF INTERFERENCE
          </text>
        </g>
      </svg>

      {/* Metrics Row: 48-60px figures with Neon Cyan / Red illumination, labels >= 24px */}
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
            PACKET LOSS
          </div>
          <div style={{ color: '#FF453A', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            {(72.4 + Math.sin(frame * 0.1) * 8).toFixed(1)}%
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            SIGNAL NOISE
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            -{(14.2 + Math.cos(frame * 0.15) * 3).toFixed(1)} dB
          </div>
        </div>
      </div>
    </div>
  );
};
