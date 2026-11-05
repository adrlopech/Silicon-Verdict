/** Minecraft video kit — HUD: vanilla hotbar (widgets.png), subtitles and title card. Survival bars are intentionally not drawn. */
import React, { useContext } from 'react';
import { AssetsCtx, PIXEL } from './core';

export const PX = 4; // GUI scale

export const Hotbar: React.FC<{ items: string[]; bottom: number; start: number; selected?: number }> = ({ items, bottom, start, selected }) => {
  const A = useContext(AssetsCtx);
  const W = 182 * PX;
  const widgets = A.widgets.src;
  return (
    <div style={{ position: 'absolute', left: (1080 - W) / 2, bottom, width: W, height: 22 * PX, backgroundImage: `url(${widgets})`, backgroundSize: `${256 * PX}px ${256 * PX}px`, backgroundPosition: '0 0', imageRendering: 'pixelated' }}>
      {Array.from({ length: 9 }).map((_, i) => {
        const it = items[start + i];
        return it ? <img key={i} src={A[it].src} width={16 * PX} height={16 * PX} style={{ position: 'absolute', left: (3 + i * 20) * PX, top: 3 * PX, imageRendering: 'pixelated' }} /> : null;
      })}
      {selected != null && (
        <div style={{ position: 'absolute', left: (selected * 20 - 1) * PX, top: -1 * PX, width: 24 * PX, height: 24 * PX, backgroundImage: `url(${widgets})`, backgroundSize: `${256 * PX}px ${256 * PX}px`, backgroundPosition: `0 ${-22 * PX}px`, imageRendering: 'pixelated' }} />
      )}
    </div>
  );
};

const clean = (w: string) => w.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');

/** Splits a line into short on-screen chunks (2-3 words, ~18 characters), like the reference Shorts show them. */
export const chunkText = (text: string, maxWords = 3, maxChars = 18): string[] => {
  const chunks: string[] = [];
  let cur: string[] = [];
  text.trim().split(/\s+/).forEach((w) => {
    const next = [...cur, w].join(' ');
    if (cur.length && (cur.length >= maxWords || next.length > maxChars)) {
      chunks.push(cur.join(' '));
      cur = [];
    }
    cur.push(w);
    if (/[.!?,;:]$/.test(w) && cur.length >= 2) { chunks.push(cur.join(' ')); cur = []; }
  });
  if (cur.length) chunks.push(cur.join(' '));
  if (chunks.length > 1 && chunks[chunks.length - 1].split(' ').length === 1) chunks.splice(-2, 2, chunks.slice(-2).join(' ')); // never leave a lone last word
  return chunks;
};

/** The chunk to show at `progress` (0..1 of the spoken part of the beat), weighted by characters so it follows the speech rhythm. */
export const chunkAt = (text: string, progress: number): string => {
  const chunks = chunkText(text);
  const w = chunks.map((c) => c.length + 3);
  const total = w.reduce((a, b) => a + b, 0);
  let acc = 0;
  for (let i = 0; i < chunks.length; i++) {
    acc += w[i];
    if (progress * total < acc) return chunks[i];
  }
  return chunks[chunks.length - 1];
};

/** Wrapper must be absolutely positioned and full screen: a transformed ancestor becomes the containing block of absolute children.
 *  Shows one short chunk at a time; the highlighted term (and any figure) is yellow. */
export const chunkAtWords = (text: string, words: { s: number; e: number }[], t: number): string => {
  const chunks = chunkText(text);
  let first = 0, cur = chunks[0];
  for (const c of chunks) {
    const w = words[first];
    if (w && t >= w.s - 2) cur = c; // a chunk appears just before its first word is spoken
    first += c.split(' ').length;
  }
  return cur;
};

export const Subtitle: React.FC<{ text: string; hl?: string; progress?: number; words?: { s: number; e: number }[]; t?: number }> = ({ text, hl, progress = 0, words, t = 0 }) => {
  const shown = words?.length ? chunkAtWords(text, words, t) : chunkAt(text, progress);
  const hot = new Set((hl ?? '').split(/\s+/).map(clean).filter(Boolean));
  return (
    <div style={{ position: 'absolute', left: 40, right: 40, bottom: 330, display: 'flex', justifyContent: 'center' }}>
      <div style={{ background: 'rgba(0,0,0,0.62)', padding: '16px 30px', fontFamily: PIXEL, fontSize: 62, lineHeight: 1.35, textAlign: 'center', color: '#fff', textShadow: '5px 5px 0 #000' }}>
        {shown.split(' ').map((w, i) => (
          <span key={i} style={{ color: hot.has(clean(w)) || /\d/.test(w) ? '#ffe14a' : '#fff' }}>{w} </span>
        ))}
      </div>
    </div>
  );
};

/** Giant pixel-font concept title in the middle of the frame (green with a dark outline), popping in with a small overshoot. */
export const BigTitle: React.FC<{ text: string; f: number; frames: number }> = ({ text, f, frames }) => {
  const words = text.trim().split(/\s+/);
  let lines = [text.trim()];
  if (text.length > 10 && words.length > 1) {
    let best = 1, diff = 1e9;
    for (let k = 1; k < words.length; k++) {
      const d = Math.abs(words.slice(0, k).join(' ').length - words.slice(k).join(' ').length);
      if (d < diff) { diff = d; best = k; }
    }
    lines = [words.slice(0, best).join(' '), words.slice(best).join(' ')];
  }
  const longest = Math.max(...lines.map((l) => l.length));
  const size = Math.min(150, 900 / (longest * 1.05));
  const t = Math.min(1, Math.max(0, f / 10));
  const pop = t < 1 ? 1.25 - 0.25 * t + Math.sin(t * Math.PI) * 0.08 : 1;
  const op = Math.min(1, f / 6) * Math.min(1, Math.max(0, (frames - f) / 12));
  if (op <= 0) return null;
  const stroke = Math.max(4, size / 14);
  const outline = [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, 2], [2, 2]].map(([x, y]) => `${x * stroke}px ${y * stroke}px 0 #123b12`).join(',');
  return (
    <div style={{ position: 'absolute', left: 0, right: 0, top: 560, textAlign: 'center', opacity: op, transform: `scale(${pop})` }}>
      {lines.map((l, i) => (
        <div key={i} style={{ fontFamily: PIXEL, fontSize: size, lineHeight: 1.12, color: '#55ff55', textShadow: outline }}>{l}</div>
      ))}
    </div>
  );
};
