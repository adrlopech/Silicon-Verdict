import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { MONO, SANS } from './fonts';
import { CAPTION_SPACE, NO_CAPTION, useLook } from './looks';
import { clamp, useTheme } from './primitives';
import { CaptionWord, MotionScene, HEIGHT, SAFE_BOTTOM } from './types';

/**
 * Word-by-word captions of the narration: the viewer who watches without sound still gets the story, and the highlighted word keeps the eye moving.
 * The words come from the voice timing (props.captions). Phrases of up to four words, cut at punctuation. Shown in a strip just above the platform's bottom UI,
 * except over scenes built to fill the frame (NO_CAPTION).
 */
type Chunk = { words: CaptionWord[]; s: number; e: number };

export const chunkCaptions = (words: CaptionWord[], maxWords = 4, maxChars = 24): Chunk[] => {
  const out: Chunk[] = [];
  let cur: CaptionWord[] = [];
  const flush = () => {
    if (cur.length) out.push({ words: cur, s: cur[0].s, e: cur[cur.length - 1].e });
    cur = [];
  };
  for (const w of words) {
    const len = cur.map((x) => x.w).join(' ').length + w.w.length + 1;
    if (cur.length >= maxWords || (cur.length && len > maxChars)) flush();
    cur.push(w);
    if (/[.!?;:]$/.test(w.w) || (/,$/.test(w.w) && cur.length >= 2)) flush();
  }
  flush();
  return out;
};

/** How much room the caption strip takes from the scene (0 when the scene fills the frame or there are no captions). */
export const captionSpaceFor = (scene: MotionScene, hasCaptions: boolean): number => (hasCaptions && !NO_CAPTION.has(scene.type) ? CAPTION_SPACE : 0);

export const Captions: React.FC<{ chunks: Chunk[]; scene: MotionScene | undefined }> = ({ chunks, scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { theme, light } = useTheme();
  const look = useLook();
  if (!scene || !chunks.length || NO_CAPTION.has(scene.type)) return null;
  // the phrase being said now, or the last one for a beat after it ends so there is no flicker between phrases
  let chunk: Chunk | undefined;
  for (const c of chunks) if (frame >= c.s - 2 && frame <= c.e + 10) chunk = c;
  if (!chunk) return null;
  const pop = spring({ frame: frame - chunk.s, fps, config: { damping: 14, stiffness: 220, mass: 0.6 } });
  const fade = interpolate(frame, [chunk.e + 4, chunk.e + 10], [1, 0], clamp);
  const style = look.captions;
  const size = style === 'mono' ? 46 : 56;
  const base = light ? '#0A1220' : '#FFFFFF';
  const hot = (w: CaptionWord) => frame >= w.s - 1 && frame <= w.e + 2;
  const accentWords = new Set(`${scene.accentText ?? ''} ${scene.text ?? ''}`.toLowerCase().split(/\s+/).map((x) => x.replace(/[^a-z0-9]/g, '')).filter((x) => x.length > 3));
  const key = (w: CaptionWord) => accentWords.has(w.w.toLowerCase().replace(/[^a-z0-9]/g, ''));
  const font = style === 'mono' ? MONO : SANS;
  const wordStyle = (w: CaptionWord): React.CSSProperties => {
    const on = hot(w);
    if (style === 'pill') return { color: on ? '#05070C' : base, background: on ? theme.accent : 'transparent', padding: '0 12px', borderRadius: 12 };
    if (style === 'underline') return { color: on || key(w) ? theme.accent : base, borderBottom: `5px solid ${on ? theme.accent : 'transparent'}` };
    if (style === 'mono') return { color: on ? theme.accent : base, textShadow: on ? `0 0 18px ${theme.accent}` : 'none' };
    return { color: on ? theme.accent : base, transform: on ? 'scale(1.08)' : 'none' };
  };
  const top = HEIGHT - SAFE_BOTTOM - CAPTION_SPACE + 22;
  return (
    <div style={{ position: 'absolute', left: 64, right: 64, top, height: CAPTION_SPACE - 52, display: 'flex', alignItems: 'center', justifyContent: look.align === 'left' && style !== 'pill' ? 'flex-start' : 'center', opacity: fade, transform: `translateY(${(1 - Math.min(1, pop)) * 18}px) scale(${0.94 + 0.06 * Math.min(1, pop)})`, pointerEvents: 'none' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px 14px', justifyContent: 'center', padding: style === 'pill' ? '14px 26px' : '0 4px', borderRadius: 26, background: style === 'pill' ? (light ? 'rgba(255,255,255,0.88)' : 'rgba(5,10,22,0.72)') : style === 'mono' ? 'rgba(0,0,0,0.5)' : 'transparent', border: style === 'pill' ? `1px solid ${theme.accent}44` : 'none', fontFamily: font, fontWeight: style === 'mono' ? 500 : 800, fontSize: size, lineHeight: 1.12, letterSpacing: style === 'mono' ? 0 : -1, textShadow: style === 'plain' ? '0 3px 14px rgba(0,0,0,0.85), 0 0 3px rgba(0,0,0,0.9)' : undefined }}>
        {style === 'mono' && <span style={{ color: theme.accent }}>&gt;</span>}
        {chunk.words.map((w, i) => (
          <span key={i} style={{ display: 'inline-block', ...wordStyle(w) }}>{w.w}</span>
        ))}
      </div>
    </div>
  );
};
