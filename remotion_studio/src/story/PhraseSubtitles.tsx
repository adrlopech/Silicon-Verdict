import React, { useMemo } from 'react';
import { useCurrentFrame, useVideoConfig } from 'remotion';
import { CYAN, FONT } from './theme';

export interface Word { word: string; start: number; end: number }

const buildChunks = (words: Word[]): Word[][] => {
  const chunks: Word[][] = [];
  let cur: Word[] = [];
  let chars = 0;
  for (const w of words) {
    cur.push(w);
    chars += w.word.length + 1;
    const endsPhrase = /[.,!?;:]$/.test(w.word);
    if ((endsPhrase && cur.length >= 2) || cur.length >= 5 || chars > 28) {
      chunks.push(cur);
      cur = [];
      chars = 0;
    }
  }
  if (cur.length) chunks.push(cur);
  return chunks;
};

/** Phrase-style captions: white text, the word being spoken highlighted. */
export const PhraseSubtitles: React.FC<{ words: Word[]; top?: string }> = ({ words, top = '74%' }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const chunks = useMemo(() => buildChunks(words || []), [words]);
  if (!chunks.length) return null;

  let idx = chunks.findIndex((c) => t >= c[0].start - 0.05 && t <= c[c.length - 1].end + 0.25);
  if (idx === -1) {
    idx = chunks.reduce((acc, c, i) => (c[0].start <= t ? i : acc), -1);
    if (idx === -1) return null;
  }
  const chunk = chunks[idx];

  return (
    <div
      style={{
        position: 'absolute', top, left: 0, right: 0, padding: '0 70px', boxSizing: 'border-box',
        display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: '6px 18px', zIndex: 30,
        fontFamily: FONT, fontSize: 76, fontWeight: 900, lineHeight: 1.12, textAlign: 'center',
        textShadow: '0 4px 18px rgba(0,0,0,0.95)',
      }}
    >
      {chunk.map((w, i) => {
        const active = t >= w.start && t <= w.end + 0.05;
        const spoken = t > w.end;
        return (
          <span key={`${w.start}-${i}`} style={{ color: active ? CYAN : '#FFFFFF', opacity: active || spoken ? 1 : 0.55, textShadow: active ? `0 0 26px ${CYAN}aa, 0 4px 18px rgba(0,0,0,0.95)` : undefined, transform: active ? 'scale(1.06)' : 'none' }}>
            {w.word}
          </span>
        );
      })}
    </div>
  );
};
