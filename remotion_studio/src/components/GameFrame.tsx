import React from 'react';
import { Img, Loop, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';

export interface GameFrameProps {
  image_src?: string; // path relative to public/, e.g. "games/doom_2016_00.jpg"
  video_src?: string; // game clip relative to public/ (muted, loops if shorter than the scene)
  video_seconds?: number;
  game_title?: string;
  annotation?: string;
  durationFrames?: number;
  seed?: number; // varies the zoom direction between consecutive frames
}

const W = 828;
const H = 466; // 16:9 inside the 900px glass card (36px padding)

/**
 * Real game screenshot integrated into the Silicon Verdict look:
 * desaturated + blue/cyan tint, technical grid and scanlines, corner brackets,
 * slow Ken Burns zoom, telemetry-style annotation bar and a small source credit.
 */
export const GameFrame: React.FC<GameFrameProps> = ({
  image_src,
  video_src,
  video_seconds,
  game_title,
  annotation,
  durationFrames = 90,
  seed = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const progress = Math.min(1, frame / Math.max(1, durationFrames));
  const dir = seed % 2 === 0 ? 1 : -1;
  const zoom = interpolate(progress, [0, 1], [1.04, 1.16]);
  const panX = interpolate(progress, [0, 1], [-14 * dir, 14 * dir]);
  const panY = interpolate(progress, [0, 1], [8, -8]);

  // Scan line sweeps once per ~2.4s
  const sweep = ((frame / fps) % 2.4) / 2.4;
  const pulse = 0.55 + 0.45 * Math.sin((frame / fps) * 6);

  const bracket = (pos: React.CSSProperties): React.ReactNode => (
    <div
      style={{
        position: 'absolute',
        width: 34,
        height: 34,
        borderColor: '#00F0FF',
        borderStyle: 'solid',
        borderWidth: 0,
        filter: 'drop-shadow(0 0 6px rgba(0,240,255,0.8))',
        ...pos,
      }}
    />
  );

  return (
    <div style={{ width: W, display: 'flex', flexDirection: 'column', gap: 14 }}>
      <div
        style={{
          position: 'relative',
          width: W,
          height: H,
          borderRadius: 20,
          overflow: 'hidden',
          background: '#05070C',
          boxShadow: 'inset 0 0 0 1px rgba(0,240,255,0.35)',
        }}
      >
        {video_src ? (
          <Loop durationInFrames={Math.max(1, Math.round((video_seconds ?? 3) * fps))}>
            <OffthreadVideo
              src={staticFile(video_src)}
              muted
              style={{
                position: 'absolute',
                inset: 0,
                width: '100%',
                height: '100%',
                objectFit: 'cover',
                filter: 'grayscale(0.65) contrast(1.12) brightness(0.88) saturate(1.1)',
              }}
            />
          </Loop>
        ) : image_src ? (
          <Img
            src={staticFile(image_src)}
            style={{
              position: 'absolute',
              inset: 0,
              width: '100%',
              height: '100%',
              objectFit: 'cover',
              transform: `scale(${zoom}) translate(${panX}px, ${panY}px)`,
              filter: 'grayscale(0.65) contrast(1.12) brightness(0.88) saturate(1.1)',
            }}
          />
        ) : null}

        {/* Brand tint: blue shadows, cyan highlights */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'linear-gradient(160deg, rgba(0,122,255,0.55) 0%, rgba(0,60,160,0.35) 55%, rgba(0,240,255,0.25) 100%)',
            mixBlendMode: 'color',
          }}
        />
        {/* Vignette */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 45%, rgba(4,8,16,0.78) 100%)',
          }}
        />
        {/* Technical grid */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: 0.16,
            backgroundImage:
              'linear-gradient(rgba(255,255,255,0.7) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.7) 1px, transparent 1px)',
            backgroundSize: '64px 64px',
          }}
        />
        {/* Scanlines */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            opacity: 0.18,
            backgroundImage: 'repeating-linear-gradient(0deg, rgba(0,0,0,0.9) 0px, rgba(0,0,0,0.9) 1px, transparent 1px, transparent 4px)',
          }}
        />
        {/* Sweep line */}
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            top: `${sweep * 100}%`,
            height: 3,
            background: 'linear-gradient(90deg, transparent, rgba(0,240,255,0.85), transparent)',
            opacity: 0.55,
          }}
        />

        {bracket({ top: 14, left: 14, borderTopWidth: 3, borderLeftWidth: 3 })}
        {bracket({ top: 14, right: 14, borderTopWidth: 3, borderRightWidth: 3 })}
        {bracket({ bottom: 14, left: 14, borderBottomWidth: 3, borderLeftWidth: 3 })}
        {bracket({ bottom: 14, right: 14, borderBottomWidth: 3, borderRightWidth: 3 })}

        {/* Game chip */}
        {game_title && (
          <div
            style={{
              position: 'absolute',
              top: 18,
              left: 58,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              background: 'rgba(5,9,16,0.78)',
              border: '1px solid rgba(0,240,255,0.5)',
              borderRadius: 10,
              padding: '5px 12px',
              fontFamily: 'monospace',
              fontSize: 18,
              fontWeight: 800,
              letterSpacing: '0.12em',
              color: '#00F0FF',
              textTransform: 'uppercase',
              maxWidth: W - 140,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
            }}
          >
            <span
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: '#00F0FF',
                boxShadow: '0 0 8px #00F0FF',
                opacity: pulse,
                flexShrink: 0,
              }}
            />
            {game_title}
          </div>
        )}
      </div>

      {/* Annotation bar */}
      {annotation && (
        <div
          style={{
            width: W,
            boxSizing: 'border-box',
            padding: '12px 20px',
            borderRadius: 14,
            background: 'rgba(0,122,255,0.14)',
            border: '1px solid rgba(0,122,255,0.55)',
            color: '#FFFFFF',
            fontFamily: "'SF Pro Display', -apple-system, sans-serif",
            fontSize: annotation.length > 34 ? 30 : 36,
            fontWeight: 900,
            letterSpacing: '0.04em',
            textTransform: 'uppercase',
            textAlign: 'center',
            textShadow: '0 0 18px rgba(0,240,255,0.45)',
          }}
        >
          {annotation}
        </div>
      )}
    </div>
  );
};
