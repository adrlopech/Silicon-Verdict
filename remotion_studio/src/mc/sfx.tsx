/**
 * Minecraft video kit — sounds. Events use the game's own names ("block.chest.open", "entity.pig.ambient"...), resolved to real files
 * through public/mc/sound_events.json (generated from the game's sounds.json). Footsteps use normalised copies (public/mc/sfx/):
 * vanilla step sounds are far quieter than hits and breaks (grass peaks around 0.02).
 */
import React, { useContext } from 'react';
import { Audio, Sequence, staticFile } from 'remotion';
import { SoundMap, SoundMapCtx, rnd } from './core';

export interface SoundEvent {
  f: number;
  event?: string; // game event, e.g. 'block.stone.break'
  file?: string; // or a direct file under mc_sounds/minecraft/sounds (without .ogg), e.g. 'random/pop'
  vol?: number;
  rate?: number; // playback rate = pitch
}

const STEP = /^(block\.[a-z_]+|entity\.(pig|cow|chicken|zombie|skeleton|player|sheep|spider))\.step$/;
const DEFAULT_VOL: [RegExp, number][] = [
  [STEP, 0.85],
  [/\.hit$/, 0.5],
  [/\.break$/, 0.85],
  [/item\.pickup/, 0.55],
  [/chest/, 0.9],
  [/attack/, 0.8],
  [/ambient|say|hurt|death/, 0.7],
  [/.*/, 0.8],
];

export const resolveSound = (e: SoundEvent, i: number, map: SoundMap): { src: string; vol: number; rate: number } | null => {
  const vol = e.vol ?? (e.event ? DEFAULT_VOL.find(([re]) => re.test(e.event!))![1] : 0.8);
  const rate = e.rate ?? 0.94 + rnd(i * 3.7 + e.f) * 0.12;
  if (e.file) return { src: staticFile(`mc_sounds/minecraft/sounds/${e.file}.ogg`), vol, rate };
  const files = e.event ? map[e.event] : undefined;
  if (!files?.length) return null;
  const k = Math.floor(rnd(i * 7.3 + e.f * 1.7) * files.length);
  if (e.event && STEP.test(e.event)) return { src: staticFile(`mc/sfx/${e.event.replace(/\./g, '_')}_${k + 1}.wav`), vol, rate };
  return { src: staticFile(`mc_sounds/minecraft/sounds/${files[k]}.ogg`), vol, rate };
};

export const Sounds: React.FC<{ events: SoundEvent[] }> = ({ events }) => {
  const map = useContext(SoundMapCtx);
  return (
    <>
      {events.map((e, i) => {
        const r = resolveSound(e, i, map);
        if (!r) return null;
        return (
          <Sequence key={i} from={Math.max(0, e.f)} durationInFrames={120} layout="none">
            <Audio src={r.src} volume={r.vol} playbackRate={r.rate} />
          </Sequence>
        );
      })}
    </>
  );
};
