import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { SiliconComputeDie } from './vectors/SiliconComputeDie';
import { LatencyBarChart } from './vectors/LatencyBarChart';
import { FrametimeTachometer } from './vectors/FrametimeTachometer';
import { CompetitivePresetCard } from './vectors/CompetitivePresetCard';
import { VcselDepthProjector } from './vectors/VcselDepthProjector';
import { RfMicrowaveCollision } from './vectors/RfMicrowaveCollision';
import { SubseaFiberCable } from './vectors/SubseaFiberCable';
import { GpsRelativityOrbit } from './vectors/GpsRelativityOrbit';
import { NfcSecureToken } from './vectors/NfcSecureToken';
import { SpectrumBands } from './vectors/SpectrumBands';
import { SiliconStackingIllustration } from './vectors/SiliconStackingIllustration';
import { MemoryBusBottleneckIllustration } from './vectors/MemoryBusBottleneckIllustration';
import { ThermalDissipationIllustration } from './vectors/ThermalDissipationIllustration';
import { GameFrame } from './GameFrame';
import { StatCard } from './StatCard';

export interface AudioSyncedAssetProps {
  children?: React.ReactNode;
  asset_id?: string;
  triggerFrame?: number;
  startFrame?: number;
  durationFrames?: number;
  durationInFrames?: number;
  label?: string;
  isLastScene?: boolean;
  motionPreset?: 'hero' | 'metric' | 'diagram';
  image_src?: string;
  video_src?: string;
  video_seconds?: number;
  game_title?: string;
  annotation?: string;
  seed?: number;
}

export const AudioSyncedAsset: React.FC<AudioSyncedAssetProps> = ({
  children,
  asset_id,
  triggerFrame,
  startFrame,
  durationFrames,
  durationInFrames,
  label,
  isLastScene = false,
  image_src,
  video_src,
  video_seconds,
  game_title,
  annotation,
  seed = 0,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames: totalDuration } = useVideoConfig();

  const effectiveTrigger = triggerFrame ?? startFrame ?? 0;
  const initialDuration = durationFrames ?? durationInFrames ?? 180;

  const effectiveDuration = isLastScene
    ? Math.max(initialDuration, totalDuration - effectiveTrigger)
    : initialDuration;

  if (frame < effectiveTrigger || frame > effectiveTrigger + effectiveDuration) {
    return null;
  }

  const localFrame = frame - effectiveTrigger;

  // Entrada elástica
  const enterSpring = spring({
    frame: localFrame,
    fps,
    config: { damping: 11, stiffness: 150, mass: 0.75 },
  });

  // Salida rápida calibrada a la base temporal (solo si no es el outro)
  const exitFrames = Math.max(4, Math.round(fps * 0.16));
  const isExiting = !isLastScene && localFrame > effectiveDuration - exitFrames;
  const exitProgress = isExiting
    ? interpolate(localFrame - (effectiveDuration - exitFrames), [0, exitFrames], [1, 0], {
        extrapolateRight: 'clamp',
      })
    : 1.0;

  // Movimiento vivo constante (Respiración + Flotación temporal independiente de FPS)
  const breathe = 1.0 + Math.sin((localFrame * 2 * Math.PI) / (fps * 2.2)) * 0.025;
  const driftY = Math.sin((localFrame / fps) * 2.5) * 7;
  const driftX = Math.cos((localFrame / fps) * 1.8) * 5;

  const renderContent = () => {
    if (children) return children;
    switch ((asset_id || '').toLowerCase()) {
      case 'stat_card':
        return <StatCard label={label} caption={annotation} />;
      case 'game_frame':
        return (
          <GameFrame
            image_src={image_src}
            video_src={video_src}
            video_seconds={video_seconds}
            game_title={game_title}
            annotation={annotation}
            durationFrames={effectiveDuration}
            seed={seed}
          />
        );
      case 'silicon_die':
      case 'cpu_die':
      case 'semiconductor': {
        const isIntel = (label || '').toLowerCase().includes('intel') || (label || '').toLowerCase().includes('core ultra');
        return <SiliconComputeDie brand={isIntel ? 'intel' : 'amd'} />;
      }
      case 'silicon_stacking':
      case 'vcache_stacking':
      case '3d_stacking':
      case 'hybrid_bonding':
        return <SiliconStackingIllustration />;
      case 'memory_bottleneck':
      case 'bus_bottleneck':
      case 'cache_vs_ram':
        return <MemoryBusBottleneckIllustration />;
      case 'thermal_dissipation':
      case 'thermal_density':
      case 'chip_thermals':
        return <ThermalDissipationIllustration />;
      case 'latency_bars':
      case 'cache_latency':
      case 'interconnect_latency':
        return <LatencyBarChart />;
      case 'frametime_gauge':
      case 'tachometer':
      case 'fps_meter':
        return <FrametimeTachometer />;
      case 'preset_card':
      case 'dlss_card':
      case 'optimization_card':
        return <CompetitivePresetCard />;
      case 'vcsel_projector':
      case 'face_id':
      case 'lidar':
        return <VcselDepthProjector />;
      case 'rf_collision':
      case 'wifi_microwave':
        return <RfMicrowaveCollision />;
      case 'spectrum_bands':
      case 'frequency_bands':
      case 'spectrum_analyzer':
        return <SpectrumBands />;
      case 'subsea_cable':
      case 'fiber_optic':
        return <SubseaFiberCable />;
      case 'gps_relativity':
      case 'einstein_orbit':
        return <GpsRelativityOrbit />;
      case 'nfc_token':
      case 'secure_enclave':
        return <NfcSecureToken />;
      default:
        return <SiliconComputeDie />;
    }
  };

  return (
    <div
      style={{
        position: 'absolute',
        top: '42%',
        left: '50%',
        transform: `translate(-50%, -50%) translate(${driftX}px, ${driftY}px) scale(${enterSpring * breathe * exitProgress})`,
        opacity: interpolate(enterSpring, [0, 0.2], [0, 1]) * exitProgress,
        width: '900px', // 83% de ancho de lienzo
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        zIndex: 10,
      }}
    >
      <div
        style={{
          width: '100%',
          minHeight: '520px',
          padding: '36px',
          borderRadius: '32px',
          background: 'rgba(8, 12, 20, 0.90)',
          border: '2px solid rgba(0, 122, 255, 0.45)',
          backdropFilter: 'blur(25px)',
          boxShadow: '0 30px 80px rgba(0, 0, 0, 0.75), 0 0 45px rgba(0, 122, 255, 0.25)',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative',
        }}
      >
        {label && !['game_frame', 'stat_card'].includes((asset_id || '').toLowerCase()) && (
          <div
            style={{
              position: 'absolute',
              top: '-22px',
              background: '#007AFF',
              color: '#FFFFFF',
              fontFamily: "'SF Pro Display', sans-serif",
              fontSize: '26px',
              fontWeight: 900,
              letterSpacing: '2px',
              padding: '6px 24px',
              borderRadius: '12px',
              textTransform: 'uppercase',
              boxShadow: '0 0 20px rgba(0, 122, 255, 0.5)',
            }}
          >
            {label}
          </div>
        )}
        <div style={{ width: '100%', display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
          {renderContent()}
        </div>
      </div>
    </div>
  );
};
