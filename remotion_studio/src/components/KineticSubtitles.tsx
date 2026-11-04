import React from 'react';
import { interpolate, useCurrentFrame, useVideoConfig } from 'remotion';

export interface WordToken {
  word: string;
  start: number; // in seconds
  end: number;   // in seconds
}

export type WordSubtitle = WordToken;

interface KineticSubtitlesProps {
  words: WordToken[];
}

export const KineticSubtitles: React.FC<KineticSubtitlesProps> = ({ words }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const currentTime = frame / fps;

  if (!words || words.length === 0) return null;

  const activeIndex = words.findIndex(
    (w) => currentTime >= w.start && currentTime <= w.end
  );

  // If no exact match (e.g. small silence between words), find the nearest past word
  let targetIndex = activeIndex;
  if (targetIndex === -1) {
    for (let i = words.length - 1; i >= 0; i--) {
      if (currentTime >= words[i].end && (i === words.length - 1 || currentTime < words[i + 1].start)) {
        targetIndex = i;
        break;
      }
    }
  }

  if (targetIndex === -1) return null;

  // Window of 2-3 words centered around active word
  const startIndex = Math.max(0, targetIndex - 1);
  const visibleWords = words.slice(startIndex, startIndex + 3);

  // Dynamic font sizing based on character volume to prevent clipping
  const totalChars = visibleWords.reduce((acc, item) => acc + item.word.length, 0);
  const fontSize = totalChars > 22 ? 52 : (totalChars > 16 ? 60 : 68);
  const wordGap = totalChars > 22 ? 14 : 20;

  return (
    <div
      style={{
        position: 'absolute',
        top: '74%',
        width: '100%',
        display: 'flex',
        flexDirection: 'row',
        flexWrap: 'nowrap',
        justifyContent: 'center',
        alignItems: 'center',
        gap: `${wordGap}px`,
        padding: '0 40px',
        fontFamily: "'SF Pro Display', -apple-system, sans-serif",
        fontSize: `${fontSize}px`,
        fontWeight: 900,
        letterSpacing: '1.5px',
        textTransform: 'uppercase',
        zIndex: 20,
        pointerEvents: 'none',
        boxSizing: 'border-box',
      }}
    >
      {visibleWords.map((item, idx) => {
        const isCurrent = currentTime >= item.start && currentTime <= item.end;
        const scale = isCurrent
          ? interpolate(currentTime, [item.start, item.start + 0.08], [1.0, 1.12], {
              extrapolateRight: 'clamp',
              extrapolateLeft: 'clamp',
            })
          : 1.0;

        // Clean formatting to prevent joined words
        const displayWord = item.word.trim();

        return (
          <span
            key={`${item.word}-${item.start}-${idx}`}
            style={{
              color: isCurrent ? '#00F0FF' : '#FFFFFF',
              transform: `scale(${scale})`,
              textShadow: isCurrent
                ? '0 0 28px rgba(0, 240, 255, 0.85), 0 2px 14px rgba(0, 0, 0, 0.95)'
                : '0 2px 12px rgba(0, 0, 0, 0.90)',
              transition: 'transform 0.05s ease-out, color 0.05s ease-out',
              display: 'inline-flex',
              alignItems: 'center',
              whiteSpace: 'nowrap',
              marginLeft: idx > 0 ? '8px' : '0px',
              marginRight: idx < visibleWords.length - 1 ? '8px' : '0px',
            }}
          >
            {displayWord}
          </span>
        );
      })}
    </div>
  );
};
