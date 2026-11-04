import React from 'react';
import { useCurrentFrame } from 'remotion';

export const NfcSecureToken: React.FC = () => {
  const frame = useCurrentFrame();

  const couplingPhase = (frame * 0.25) % (Math.PI * 2);
  const tokenHex = ['A9', 'F4', '0E', '7C', 'B2', '31', '8D', '55'];
  const activeByteIndex = Math.floor(frame / 6) % tokenHex.length;

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
          NEAR-FIELD INDUCTION
        </span>
        <span style={{ fontSize: '26px', fontWeight: 800, color: '#00F0FF', fontFamily: 'monospace' }}>
          SECURE ENCLAVE
        </span>
      </div>

      {/* Giant Induction Coils & Cryptogram Canvas */}
      <svg width="100%" height="280" viewBox="0 0 840 280" style={{ overflow: 'visible' }}>
        {/* Left: POS Terminal Inductive Loops */}
        <g transform="translate(160, 140)">
          <rect x="-80" y="-95" width="100" height="190" rx="16" fill="#0E121A" stroke="#1C202B" strokeWidth="2.5" />
          <rect x="-65" y="-80" width="70" height="160" rx="12" fill="none" stroke="#007AFF" strokeWidth="3" />
          <text x="-30" y="125" fill="#8E8E93" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
            POS EMITTER
          </text>
        </g>

        {/* Dynamic Magnetic Flux Arcs */}
        {[...Array(5)].map((_, i) => {
          const spread = (i - 2) * 32;
          const arcPhase = couplingPhase + i * 0.4;
          const cpY = 140 + spread + Math.sin(arcPhase) * 14;
          return (
            <path
              key={i}
              d={`M 200 140 Q 420 ${cpY} 640 140`}
              fill="none"
              stroke="#00F0FF"
              strokeWidth="2.5"
              opacity={0.4 + (i % 2 === 0 ? 0.4 : 0.2)}
              strokeDasharray="10 8"
            />
          );
        })}

        {/* Right: Smartphone Enclave */}
        <g transform="translate(680, 140)">
          <rect x="-20" y="-95" width="100" height="190" rx="16" fill="#0E121A" stroke="#1C202B" strokeWidth="2.5" />
          <rect x="-5" y="-80" width="70" height="160" rx="12" fill="none" stroke="#00F0FF" strokeWidth="3" />
          <text x="30" y="125" fill="#8E8E93" fontSize="24" fontWeight="800" textAnchor="middle" fontFamily="monospace">
            eSE RECEIVER
          </text>
        </g>

        {/* Ephemeral Cryptogram Badge */}
        <g transform="translate(420, 80)">
          <rect x="-170" y="-28" width="340" height="56" rx="14" fill="rgba(10, 13, 20, 0.95)" stroke="#00F0FF" strokeWidth="2" />
          <g transform="translate(-140, 10)">
            {tokenHex.map((byte, idx) => (
              <text
                key={idx}
                x={idx * 38}
                y="0"
                fill={idx === activeByteIndex ? '#00F0FF' : '#FFFFFF'}
                fontSize="26"
                fontWeight={idx === activeByteIndex ? '900' : 'normal'}
                fontFamily="monospace"
              >
                {byte}
              </text>
            ))}
          </g>
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
            CARRIER FREQUENCY
          </div>
          <div style={{ color: '#00F0FF', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            13.56 MHz
          </div>
        </div>
        <div>
          <div style={{ color: '#8E8E93', fontSize: '24px', fontWeight: 700, fontFamily: 'monospace' }}>
            TOKEN HANDSHAKE
          </div>
          <div style={{ color: '#5AC8FA', fontSize: '54px', fontWeight: 900, fontFamily: 'monospace' }}>
            18.2 ms
          </div>
        </div>
      </div>
    </div>
  );
};
