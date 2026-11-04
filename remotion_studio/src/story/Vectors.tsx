import React from 'react';
import { interpolate, spring, useCurrentFrame, useVideoConfig } from 'remotion';
import { FONT, VectorSpec } from './theme';
import { Icon } from './icons';

const W = 860;

const Label: React.FC<{ text?: string; ink: string; size?: number }> = ({ text, ink, size = 34 }) =>
  text ? (
    <div style={{ fontFamily: FONT, fontSize: size, fontWeight: 800, color: ink, textAlign: 'center', letterSpacing: '0.02em', textTransform: 'uppercase', lineHeight: 1.1 }}>
      {text}
    </div>
  ) : null;

const useEase = (delay = 0) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  return spring({ frame: frame - delay, fps, config: { damping: 14, stiffness: 120, mass: 0.8 } });
};

export const CounterVec: React.FC<{ s: VectorSpec; ink: string }> = ({ s, ink }) => {
  const e = useEase(2);
  const from = s.value_from ?? 0;
  const to = s.value_to ?? 100;
  const v = Math.round(from + (to - from) * Math.min(1, e));
  return (
    <div style={{ width: W, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 24 }}>
      <div style={{ border: `5px solid ${ink}`, borderRadius: 30, padding: '10px 56px', minWidth: 360, textAlign: 'center' }}>
        <span style={{ fontFamily: FONT, fontSize: 220, fontWeight: 900, color: ink, textShadow: `0 0 30px ${ink}55`, letterSpacing: '-0.02em' }}>{v}</span>
      </div>
      <Label text={s.label} ink={ink} />
    </div>
  );
};

export const BarsVec: React.FC<{ s: VectorSpec; ink: string }> = ({ s, ink }) => {
  const e = Math.min(1, useEase(2));
  const row = (label: string | undefined, val: number, dim: boolean, delay: number) => {
    const w = Math.max(0, Math.min(1, val)) * Math.min(1, useEase(delay));
    return (
      <div style={{ width: W, display: 'flex', flexDirection: 'column', gap: 10 }}>
        <div style={{ fontFamily: FONT, fontSize: 38, fontWeight: 800, color: ink, opacity: dim ? 0.7 : 1, textTransform: 'uppercase' }}>{label}</div>
        <div style={{ height: 40, borderRadius: 20, border: `4px solid ${ink}`, overflow: 'hidden' }}>
          <div style={{ width: `${w * 100}%`, height: '100%', background: ink, opacity: dim ? 0.55 : 1 }} />
        </div>
      </div>
    );
  };
  void e;
  return (
    <div style={{ width: W, display: 'flex', flexDirection: 'column', gap: 44 }}>
      {row(s.label, s.a ?? 0.5, true, 2)}
      {row(s.label2, s.b ?? 0.9, false, 14)}
    </div>
  );
};

export const GaugeVec: React.FC<{ s: VectorSpec; ink: string }> = ({ s, ink }) => {
  const e = useEase(2);
  const frame = useCurrentFrame();
  const target = Math.max(0, Math.min(1, s.a ?? 0.7));
  const val = target * Math.min(1, e) + Math.sin(frame / 3) * 0.012;
  const ang = -180 + val * 180; // -180..0 degrees
  const r = 250;
  const cx = 300;
  const cy = 300;
  const nx = cx + Math.cos((ang * Math.PI) / 180) * (r - 40);
  const ny = cy + Math.sin((ang * Math.PI) / 180) * (r - 40);
  const ticks = Array.from({ length: 11 }, (_, i) => {
    const a = (-180 + i * 18) * (Math.PI / 180);
    return <line key={i} x1={cx + Math.cos(a) * (r - 22)} y1={cy + Math.sin(a) * (r - 22)} x2={cx + Math.cos(a) * r} y2={cy + Math.sin(a) * r} stroke={ink} strokeWidth={5} strokeLinecap="round" />;
  });
  return (
    <div style={{ width: W, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
      <svg width={600} height={340} viewBox="0 0 600 340">
        <path d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`} fill="none" stroke={ink} strokeWidth={6} strokeLinecap="round" />
        {ticks}
        <line x1={cx} y1={cy} x2={nx} y2={ny} stroke={ink} strokeWidth={9} strokeLinecap="round" />
        <circle cx={cx} cy={cy} r={16} fill={ink} />
      </svg>
      <Label text={s.label} ink={ink} />
    </div>
  );
};

export const TrioVec: React.FC<{ s: VectorSpec; ink: string }> = ({ s, ink }) => {
  const items = [
    { icon: s.icon, label: s.label },
    { icon: s.icon2, label: s.label2 },
    { icon: s.icon3, label: s.label3 },
  ];
  return (
    <div style={{ width: W + 80, display: 'flex', justifyContent: 'space-around', alignItems: 'flex-start', gap: 10 }}>
      {items.map((it, i) => {
        const e = Math.min(1, useEase(2 + i * 9));
        return (
          <div key={i} style={{ width: 290, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16, opacity: e, transform: `translateY(${(1 - e) * 40}px) scale(${0.8 + 0.2 * e})` }}>
            <Icon name={it.icon} size={220} ink={ink} />
            <Label text={it.label} ink={ink} size={30} />
          </div>
        );
      })}
    </div>
  );
};

export const FlowVec: React.FC<{ s: VectorSpec; ink: string }> = ({ s, ink }) => {
  const e = Math.min(1, useEase(2));
  const frame = useCurrentFrame();
  const dash = (frame * 3) % 40;
  return (
    <div style={{ width: W, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 20 }}>
        <Icon name={s.icon} size={230} ink={ink} />
        <svg width={180} height={40} viewBox="0 0 180 40" style={{ opacity: e }}>
          <line x1={0} y1={20} x2={150} y2={20} stroke={ink} strokeWidth={6} strokeDasharray="14 12" strokeDashoffset={-dash} strokeLinecap="round" />
          <path d="M140 6l28 14-28 14" fill="none" stroke={ink} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" />
        </svg>
        <Icon name={s.icon2 || s.icon} size={230} ink={ink} />
      </div>
      <Label text={s.label} ink={ink} />
    </div>
  );
};

export const IconVec: React.FC<{ s: VectorSpec; ink: string }> = ({ s, ink }) => {
  const frame = useCurrentFrame();
  const float = Math.sin(frame / 12) * 8;
  return (
    <div style={{ width: W, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20, transform: `translateY(${float}px)` }}>
      <Icon name={s.icon} size={380} ink={ink} />
      <Label text={s.label} ink={ink} size={44} />
    </div>
  );
};

export const BigTextVec: React.FC<{ s: VectorSpec; ink: string }> = ({ s, ink }) => {
  const e = Math.min(1, useEase(1));
  const t = s.text || s.label || '';
  const size = t.length > 26 ? 84 : t.length > 14 ? 110 : 150;
  return (
    <div style={{ width: W, textAlign: 'center', transform: `scale(${0.85 + 0.15 * e})`, opacity: interpolate(e, [0, 0.3], [0, 1]) }}>
      <div style={{ fontFamily: FONT, fontSize: size, fontWeight: 900, lineHeight: 1.02, color: ink, textTransform: 'uppercase', textShadow: `0 0 30px ${ink}55`, wordBreak: 'keep-all' }}>{t}</div>
    </div>
  );
};

export const Vector: React.FC<{ spec: VectorSpec; ink: string }> = ({ spec, ink }) => {
  switch (spec.type) {
    case 'counter': return <CounterVec s={spec} ink={ink} />;
    case 'bars': return <BarsVec s={spec} ink={ink} />;
    case 'gauge': return <GaugeVec s={spec} ink={ink} />;
    case 'trio': return <TrioVec s={spec} ink={ink} />;
    case 'flow': return <FlowVec s={spec} ink={ink} />;
    case 'big_text': return <BigTextVec s={spec} ink={ink} />;
    case 'icon':
    default: return <IconVec s={spec} ink={ink} />;
  }
};
