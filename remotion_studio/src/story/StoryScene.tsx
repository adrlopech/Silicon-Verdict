import React from 'react';
import { AbsoluteFill, Audio, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from 'remotion';
import { BG, BLUE, CYAN, DARK_INK, FONT, SceneSpec } from './theme';
import { Mascot } from './Mascot';
import { Vector } from './Vectors';
import { PhraseSubtitles, Word } from './PhraseSubtitles';

export interface StorySceneProps {
  category: string;
  hook: string;
  audio_src: string;
  total_frames: number;
  subtitles: Word[];
  scenes: SceneSpec[];
}

const Particles: React.FC<{ ink: string }> = ({ ink }) => {
  const frame = useCurrentFrame();
  const dots = Array.from({ length: 36 }, (_, i) => {
    const seed = (i * 9301 + 49297) % 233280;
    const x = (seed / 233280) * 1080;
    const speed = 0.25 + ((i * 37) % 10) / 22;
    const y = (((seed * 7) % 1920) - frame * speed + 1920 * 10) % 1920;
    const r = 1.5 + (i % 4) * 0.8;
    const tw = 0.25 + 0.45 * Math.abs(Math.sin((frame + i * 11) / 28));
    return <circle key={i} cx={x} cy={y} r={r} fill={ink} opacity={tw} />;
  });
  return <svg width={1080} height={1920} style={{ position: 'absolute', inset: 0 }}>{dots}</svg>;
};

const StageScene: React.FC<{ scene: SceneSpec }> = ({ scene }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  if (!scene.vector) return null;
  const ink = scene.flash ? DARK_INK : CYAN;
  const enter = spring({ frame, fps, config: { damping: 13, stiffness: 150, mass: 0.7 } });
  const exitF = 6;
  const out = interpolate(frame, [scene.duration_frames - exitF, scene.duration_frames], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  return (
    <div style={{ position: 'absolute', top: scene.start_frame === 0 ? 330 : 250, left: 0, width: 1080, height: 640, display: 'flex', alignItems: 'center', justifyContent: 'center', opacity: Math.min(1, enter * 1.4) * out, transform: `scale(${(0.82 + 0.18 * enter) * 1.12})` }}>
      <Vector spec={scene.vector} ink={ink} />
    </div>
  );
};

export const StoryScene: React.FC<StorySceneProps> = ({ category = '', hook = '', audio_src, total_frames = 1800, subtitles = [], scenes = [] }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const idx = scenes.reduce((acc, s, i) => (frame >= s.start_frame ? i : acc), 0);
  const cur = scenes[idx];
  const prev = scenes[Math.max(0, idx - 1)];
  const flashNow = !!cur?.flash && frame >= cur.start_frame && frame < cur.start_frame + cur.duration_frames - 3;
  const flashK = flashNow ? Math.min(1, (frame - cur.start_frame) / 4) : 0;
  const ink = flashNow ? DARK_INK : CYAN;

  const hookOpacity = interpolate(frame, [0, 6, fps * 3, fps * 3.4], [0, 1, 1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const progress = Math.min(1, frame / Math.max(1, total_frames));

  return (
    <AbsoluteFill style={{ backgroundColor: BG, overflow: 'hidden' }}>
      {/* soft brand glow */}
      <div style={{ position: 'absolute', inset: 0, background: `radial-gradient(ellipse 700px 600px at 50% 36%, ${BLUE}33 0%, transparent 70%)` }} />
      <Particles ink={CYAN} />
      {/* flash punch */}
      <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(160deg, ${CYAN} 0%, #00A9FF 55%, ${BLUE} 100%)`, opacity: flashK }} />

      {audio_src && <Audio src={staticFile(audio_src)} />}

      {/* progress bar */}
      <div style={{ position: 'absolute', top: 0, left: 0, height: 8, width: `${progress * 100}%`, background: flashNow ? DARK_INK : CYAN, boxShadow: `0 0 14px ${CYAN}` }} />

      {/* hook */}
      <div style={{ position: 'absolute', top: 150, left: 40, right: 40, textAlign: 'center', opacity: hookOpacity, fontFamily: FONT, fontSize: hook.length > 24 ? 92 : 110, fontWeight: 900, lineHeight: 1.04, color: '#FFFFFF', textTransform: 'uppercase', textShadow: `0 0 36px ${CYAN}88, 0 6px 22px rgba(0,0,0,0.9)`, zIndex: 40 }}>
        {hook}
      </div>

      {/* category tag */}
      <div style={{ position: 'absolute', top: 40, left: 0, right: 0, textAlign: 'center', fontFamily: 'monospace', fontSize: 22, fontWeight: 800, letterSpacing: '0.16em', color: ink, opacity: 0.8 }}>
        SILICON VERDICT // {category.toUpperCase()}
      </div>

      {/* vectors, one Sequence per scene so animations restart locally */}
      {scenes.map((s, i) => (
        <Sequence key={i} from={s.start_frame} durationInFrames={s.duration_frames}>
          <StageScene scene={s} />
        </Sequence>
      ))}

      {/* mascot */}
      <div style={{ position: 'absolute', top: 860, left: 0, right: 0, display: 'flex', justifyContent: 'center', transform: `translateX(${idx % 2 === 0 ? -170 : 170}px)`, zIndex: 20 }}>
        {cur && (
          <Mascot pose={cur.pose} prevPose={prev?.pose || 'idle'} poseStartFrame={cur.start_frame} words={subtitles} ink={ink} scale={0.92} />
        )}
      </div>

      <PhraseSubtitles words={subtitles} top="74%" />

      {/* handle */}
      <div style={{ position: 'absolute', bottom: 60, right: 56, fontFamily: FONT, fontSize: 24, fontWeight: 800, color: BLUE, letterSpacing: '0.1em' }}>@SILICONVERDICT</div>
    </AbsoluteFill>
  );
};
