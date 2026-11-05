import React from 'react';
import { AbsoluteFill, Audio, staticFile } from 'remotion';
import { DynamicBackground } from './components/DynamicBackground';
import { HeaderBanner } from './components/HeaderBanner';
import { KineticSubtitles, WordSubtitle } from './components/KineticSubtitles';
import { AudioSyncedAsset } from './components/AudioSyncedAsset';

export interface VisualTrigger {
  id?: string;
  asset_id: string;
  label?: string;
  start_frame: number;
  duration_frames: number;
  motion_preset?: 'hero' | 'metric' | 'diagram';
}

export interface MainSceneProps {
  category: string;
  header_banner: string;
  audio_src: string;
  subtitles: WordSubtitle[];
  visual_triggers: VisualTrigger[];
}

export const MainScene: React.FC<MainSceneProps> = ({
  category = 'TECH CURIOSITIES',
  header_banner = 'WHY MICROWAVES DESTROY 2.4 GHz WI-FI',
  audio_src = 'audio/narration.wav',
  subtitles = [],
  visual_triggers = [],
}) => {
  return (
    <AbsoluteFill style={{ backgroundColor: '#07090E', overflow: 'hidden' }}>
      {/* 1. Procedural Living High-Tech Background */}
      <DynamicBackground />

      {/* 2. Audio Track */}
      {audio_src && (
        <Audio src={staticFile(audio_src)} />
      )}

      {/* 3. Header Banner (Safe Zone Compliant at Top) */}
      <HeaderBanner category={category} title={header_banner} />

      {/* 4. Giant Visual Asset Stage (900px width / 83% of screen) */}
      {visual_triggers.map((trigger, idx) => (
        <AudioSyncedAsset
          key={`${trigger.asset_id}-${trigger.start_frame}-${idx}`}
          asset_id={trigger.asset_id}
          label={trigger.label}
          triggerFrame={trigger.start_frame}
          durationFrames={trigger.duration_frames}
          isLastScene={idx === visual_triggers.length - 1}
          motionPreset={trigger.motion_preset || 'hero'}
          seed={idx}
        />
      ))}

      {/* 5. Word-by-Word Kinetic Subtitles (Anchored at 74% Safe Zone) */}
      <KineticSubtitles words={subtitles} />
    </AbsoluteFill>
  );
};
