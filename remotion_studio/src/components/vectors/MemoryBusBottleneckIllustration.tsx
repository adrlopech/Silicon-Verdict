import React from 'react';
import { useCurrentFrame } from 'remotion';

export const MemoryBusBottleneckIllustration: React.FC = () => {
  const frame = useCurrentFrame();

  // Slow packet animation on the long memory bus (simulating high-latency 60ns travel across Infinity Fabric to RAM)
  const slowPacketX = 210 + ((frame * 2.8) % 430);

  // Fast packet stream on the local 3D cache hierarchy (simulating sub-11ns local hits)
  const fastPacketOffset = (frame * 12) % 40;

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
          CACHE HIERARCHY LATENCY
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          60ns VS 11ns
        </span>
      </div>

      {/* SVG Canvas for Memory Bus Latency Comparison */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        <defs>
          <linearGradient id="coreGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#192847" />
            <stop offset="100%" stopColor="#0E1626" />
          </linearGradient>
          <linearGradient id="ramGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#2A1E24" />
            <stop offset="100%" stopColor="#171114" />
          </linearGradient>
          <linearGradient id="cacheGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#007AFF" />
            <stop offset="100%" stopColor="#004FB8" />
          </linearGradient>
        </defs>

        {/* ========================================================
            LANE 1 (TOP): CORE TO SYSTEM RAM (HIGH LATENCY STALL)
           ======================================================== */}
        {/* Core Block */}
        <rect x="25" y="25" width="170" height="90" rx="14" fill="url(#coreGrad)" stroke="#007AFF" strokeWidth="2.5" />
        <text x="110" y="65" fill="#FFFFFF" fontSize="26" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          ZEN CORE
        </text>
        <text x="110" y="95" fill="#5AC8FA" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          EXECUTION
        </text>

        {/* System RAM Block */}
        <rect x="645" y="25" width="170" height="90" rx="14" fill="url(#ramGrad)" stroke="#FF453A" strokeWidth="2.5" />
        <text x="730" y="65" fill="#FFFFFF" fontSize="26" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          SYSTEM RAM
        </text>
        <text x="730" y="95" fill="#FF453A" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          DDR5-6000
        </text>

        {/* Long Interconnect Line with Stalled Data Packet */}
        <line x1="195" y1="70" x2="645" y2="70" stroke="#FF453A" strokeWidth="3.5" strokeDasharray="10 8" />
        <circle cx={slowPacketX} cy="70" r="10" fill="#FF3B30" filter="drop-shadow(0 0 10px rgba(255, 69, 58, 0.9))" />
        <text x="420" y="55" fill="#FF453A" fontSize="24" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          MEMORY STALL // 65.4 ns DELAY
        </text>

        {/* ========================================================
            LANE 2 (BOTTOM): CORE + DIRECT 3D V-CACHE (ZERO STALL)
           ======================================================== */}
        {/* Core Block */}
        <rect x="25" y="155" width="170" height="90" rx="14" fill="url(#coreGrad)" stroke="#007AFF" strokeWidth="2.5" />
        <text x="110" y="195" fill="#FFFFFF" fontSize="26" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          ZEN CORE
        </text>
        <text x="110" y="225" fill="#00F0FF" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
          ZERO STALL
        </text>

        {/* Direct 3D V-Cache SRAM Block (Stacked immediately adjacent) */}
        <rect x="220" y="155" width="310" height="90" rx="14" fill="url(#cacheGrad)" stroke="#00F0FF" strokeWidth="3" />
        <text x="375" y="195" fill="#FFFFFF" fontSize="26" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          3D V-CACHE SRAM DIE
        </text>
        <text x="375" y="225" fill="#00F0FF" fontSize="24" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          LOCAL HIERARCHY HIT
        </text>

        {/* Ultra-Fast Direct Connection Stream */}
        <line x1="195" y1="200" x2="220" y2="200" stroke="#00F0FF" strokeWidth="6" strokeDasharray="6 4" />
        <circle cx={198 + (fastPacketOffset % 20)} cy="200" r="6" fill="#FFFFFF" />

        {/* Bypass Indicator Badge */}
        <rect x="560" y="170" width="255" height="60" rx="10" fill="#0F1B2E" stroke="#00F0FF" strokeWidth="2" />
        <text x="687" y="207" fill="#00F0FF" fontSize="21" fontWeight="900" textAnchor="middle" fontFamily="monospace">
          LOCAL HIT // 10.8ns
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
            RAM ACCESS PENALTY
          </div>
          <div style={{ color: '#FF453A', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            65.4 ns
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            3D CACHE LATENCY
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            10.8 ns
          </div>
        </div>
      </div>
    </div>
  );
};
