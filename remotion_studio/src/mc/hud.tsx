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

/** Wrapper must be absolutely positioned and full screen: a transformed ancestor becomes the containing block of absolute children. */
export const Subtitle: React.FC<{ text: string; hl?: string }> = ({ text, hl }) => (
  <div style={{ position: 'absolute', left: 50, right: 50, bottom: 270, display: 'flex', justifyContent: 'center' }}>
    <div style={{ background: 'rgba(0,0,0,0.72)', padding: '20px 28px', fontFamily: PIXEL, fontSize: 36, lineHeight: 1.5, textAlign: 'center', color: '#fff', textShadow: '4px 4px 0 #000' }}>
      {text.split(' ').map((w, i) => (
        <span key={i} style={{ color: hl && w.toLowerCase() === hl.toLowerCase() ? '#ffe14a' : '#fff' }}>{w} </span>
      ))}
    </div>
  </div>
);
