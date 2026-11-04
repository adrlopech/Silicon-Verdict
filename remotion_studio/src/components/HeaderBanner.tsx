import React from 'react';
import { useCurrentFrame } from 'remotion';

export interface HeaderBannerProps {
  category: string;
  title: string;
}

export const HeaderBanner: React.FC<HeaderBannerProps> = ({ category, title }) => {
  const frame = useCurrentFrame();

  // Subtle breathing scale for the banner
  const breath = 1.0 + Math.sin((frame * 2 * Math.PI) / (60 * 2.5)) * 0.012;

  // Use non-breaking hyphen (\u2011) so words like "Wi‑Fi" or "2.4‑GHz" are never broken across lines
  const formattedTitle = title.replace(/-/g, '\u2011');
  const fontSize = formattedTitle.length > 40 ? 38 : (formattedTitle.length > 30 ? 42 : 46);

  return (
    <div
      style={{
        position: 'absolute',
        top: 140, // 140px ensures TikTok / Shorts top HUD clearance
        left: 40,
        right: 40,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        textAlign: 'center',
        transform: `scale(${breath})`,
        zIndex: 50,
      }}
    >
      {/* Category Pill */}
      <div
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 8,
          background: 'rgba(0, 122, 255, 0.12)',
          border: '1px solid rgba(0, 122, 255, 0.4)',
          borderRadius: 16,
          padding: '6px 16px',
          marginBottom: 12,
        }}
      >
        <div
          style={{
            width: 7,
            height: 7,
            borderRadius: '50%',
            background: '#00F0FF',
            boxShadow: '0 0 8px #00F0FF',
          }}
        />
        <span
          style={{
            color: '#00F0FF',
            fontSize: 13,
            fontWeight: 800,
            letterSpacing: '0.14em',
            fontFamily: 'monospace',
          }}
        >
          SILICON VERDICT // {category.toUpperCase()}
        </span>
      </div>

      {/* Main Punchy Title */}
      <h1
        style={{
          margin: 0,
          fontFamily: "'SF Pro Display', -apple-system, 'Helvetica Neue', Arial, sans-serif",
          color: '#FFFFFF',
          fontSize: `${fontSize}px`,
          fontWeight: 900,
          lineHeight: 1.18,
          letterSpacing: '-0.02em',
          textTransform: 'uppercase',
          maxWidth: 960,
          hyphens: 'none',
          wordBreak: 'keep-all',
          textShadow: '0 4px 20px rgba(0, 0, 0, 0.8), 0 0 30px rgba(0, 122, 255, 0.25)',
        }}
      >
        {formattedTitle}
      </h1>
    </div>
  );
};
