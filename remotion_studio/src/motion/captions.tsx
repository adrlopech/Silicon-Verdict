import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { MONO, SANS } from './fonts';
import { CAPTION_DROP, CAPTION_SPACE, NO_CAPTION, useLook } from './looks';
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
  for (const w0 of words) {
    const w = { ...w0, w: w0.w.replace(/\*/g, '') };
    if (!w.w) continue;
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
  const size = style === 'mono' ? 46 : style === 'twotone' ? 60 : 60;
  const base = light ? '#0A1220' : '#FFFFFF';
  const hot = (w: CaptionWord) => frame >= w.s - 1 && frame <= w.e + 2;
  const accentWords = new Set(`${scene.accentText ?? ''} ${scene.text ?? ''}`.toLowerCase().split(/\s+/).map((x) => x.replace(/[^a-z0-9]/g, '')).filter((x) => x.length > 3));
  const key = (w: CaptionWord) => accentWords.has(w.w.toLowerCase().replace(/[^a-z0-9]/g, ''));
  const font = style === 'mono' ? MONO : SANS;
  // a heavy outline keeps big captions legible over any background (the outline is the dark colour of the look; light looks use white)
  const edge = light ? '#FFFFFF' : '#05070C';
  const outline: React.CSSProperties = { WebkitTextStroke: `7px ${edge}`, paintOrder: 'stroke fill', textShadow: `0 6px 22px rgba(0,0,0,${light ? 0.25 : 0.7})` };
  const wordStyle = (w: CaptionWord): React.CSSProperties => {
    const on = hot(w);
    if (style === 'pill') return { color: on ? '#05070C' : base, background: on ? theme.accent : 'transparent', padding: '0 12px', borderRadius: 12 };
    if (style === 'wordpill') return { color: on ? '#05070C' : base, background: on ? theme.accent : 'transparent', padding: '0 14px', borderRadius: 18, boxShadow: on ? `0 0 28px ${theme.accent}77` : 'none', textShadow: on ? 'none' : `0 3px 14px rgba(0,0,0,${light ? 0.2 : 0.85})`, transform: on ? 'scale(1.06)' : 'none' };
    if (style === 'karaoke') {
      // a colour fill that sweeps through the word as it is spoken: spoken words stay in the accent colour
      const pr = Math.max(0, Math.min(1, (frame - w.s) / Math.max(1, w.e - w.s + 2)));
      if (frame > w.e + 2) return { color: theme.accent, padding: '0 6px' };
      return { padding: '0 6px', color: 'transparent', backgroundImage: `linear-gradient(90deg, ${theme.accent} ${pr * 100}%, ${base} ${pr * 100}%)`, WebkitBackgroundClip: 'text', backgroundClip: 'text', transform: on ? 'scale(1.05)' : 'none' };
    }
    if (style === 'box') return { color: on ? '#05070C' : base, background: on ? theme.accent : 'transparent', padding: '0 12px', borderRadius: 6, transform: on ? 'rotate(-2deg) scale(1.05)' : 'none', boxShadow: on ? `6px 6px 0 ${theme.accent2 ?? theme.accent}` : 'none' };
    if (style === 'bounce') return { padding: '0 10px', color: on ? theme.accent : base, transform: on ? `translateY(${-14 * Math.max(0, Math.sin(Math.min(1, (frame - w.s) / 6) * Math.PI))}px) scale(1.08)` : 'none', textShadow: on ? `0 0 22px ${theme.accent}99` : undefined };
    if (style === 'underline') return { color: on || key(w) ? theme.accent : base, borderBottom: `5px solid ${on ? theme.accent : 'transparent'}` };
    if (style === 'mono') return { color: on ? theme.accent : base, textShadow: on ? `0 0 18px ${theme.accent}` : 'none' };
    return { color: on ? theme.accent : base, transform: on ? 'scale(1.08)' : 'none' };
  };
  const top = HEIGHT - SAFE_BOTTOM - CAPTION_SPACE + 22 + CAPTION_DROP;
  if (style === 'oneword') {
    // one huge word at a time: the word being said (or the last one said), outlined, popping in on every word
    let cur = chunk.words[0];
    for (const w of chunk.words) if (frame >= w.s - 1) cur = w;
    const wp = spring({ frame: frame - cur.s, fps, config: { damping: 11, stiffness: 260, mass: 0.5 } });
    const big = cur.w.length > 9 ? 84 : cur.w.length > 6 ? 98 : 112;
    return (
      <div style={{ position: 'absolute', left: 40, right: 40, top, height: CAPTION_SPACE - 52, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: fade, pointerEvents: 'none' }}>
        <span style={{ display: 'inline-block', fontFamily: look.sans, fontWeight: 900, fontSize: big, lineHeight: 1, letterSpacing: -2, textTransform: look.upper ? 'uppercase' : 'none', color: key(cur) ? theme.accent : base, transform: `scale(${0.72 + 0.28 * Math.min(1.15, wp)})`, ...outline }}>{cur.w.replace(/[.,!?;:]+$/, '')}</span>
      </div>
    );
  }
  if (style === 'twotone') {
    // a two-line headline: the first half of the phrase in the accent colour, the second in white
    const cut = Math.ceil(chunk.words.length / 2);
    const line = (ws: CaptionWord[], color: string, k: number) => (
      <div key={k} style={{ display: 'flex', gap: Math.round(size * 0.34), justifyContent: 'center', color }}>
        {ws.map((w, i) => <span key={i} style={{ display: 'inline-block', transform: hot(w) ? 'scale(1.08)' : 'none', ...outline, WebkitTextStroke: `4px ${edge}` }}>{w.w}</span>)}
      </div>
    );
    return (
      <div style={{ position: 'absolute', left: 48, right: 48, top: top - 6, height: CAPTION_SPACE - 40, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: fade, transform: `translateY(${(1 - Math.min(1, pop)) * 16}px)`, pointerEvents: 'none' }}>
        <div style={{ fontFamily: look.sans, fontWeight: 900, fontSize: size, lineHeight: 1.04, letterSpacing: -1, textAlign: 'center', textTransform: look.upper ? 'uppercase' : 'none' }}>
          {line(chunk.words.slice(0, cut), theme.accent, 0)}
          {chunk.words.length > cut && line(chunk.words.slice(cut), base, 1)}
        </div>
      </div>
    );
  }
  return (
    <div style={{ position: 'absolute', left: 96, right: 96, top, height: CAPTION_SPACE - 52, display: 'flex', alignItems: 'center', justifyContent: look.align === 'left' && style !== 'pill' && style !== 'wordpill' ? 'flex-start' : 'center', opacity: fade, transform: `translateY(${(1 - Math.min(1, pop)) * 18}px) scale(${0.94 + 0.06 * Math.min(1, pop)})`, pointerEvents: 'none' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: `4px ${Math.round(size * 0.3)}px`, justifyContent: 'center', padding: style === 'pill' ? '14px 26px' : '0 4px', borderRadius: 26, background: style === 'pill' ? (light ? 'rgba(255,255,255,0.88)' : 'rgba(5,10,22,0.72)') : style === 'mono' ? 'rgba(0,0,0,0.5)' : 'transparent', border: style === 'pill' ? `1px solid ${theme.accent}44` : 'none', fontFamily: font, fontWeight: style === 'mono' ? 500 : 800, fontSize: size, lineHeight: 1.12, letterSpacing: style === 'mono' ? 0 : -1, textShadow: style === 'plain' ? '0 3px 14px rgba(0,0,0,0.85), 0 0 3px rgba(0,0,0,0.9)' : undefined }}>
        {style === 'mono' && <span style={{ color: theme.accent }}>&gt;</span>}
        {chunk.words.map((w, i) => (
          <span key={i} style={{ display: 'inline-block', ...wordStyle(w) }}>{w.w}</span>
        ))}
      </div>
    </div>
  );
};
