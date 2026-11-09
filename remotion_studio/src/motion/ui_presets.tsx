import React from 'react';
import { MONO, SANS } from './fonts';
import { useTheme } from './primitives';
import { MotionScene } from './types';
import { BAD, Bars, Chip, GOOD, Glyph, Graph, INK, MUTED, Row, Slider, Switch, UiShell, WARN, WIN_W, Win, ease, mix, num, rows, useAct } from './ui_kit';

/** Presets 1-10: system and gaming panels. Contract per preset (scene fields): see services/motion_generator.py UI_PRESETS. */
type P = { scene: MotionScene };
/** 1-based `value` -> 0-based index, clamped to the list. */
const idx = (value: number | undefined, len: number, fallback: number) => Math.max(0, Math.min(len - 1, Math.round(value ?? fallback) - 1));

/* 1 ─ display: refresh-rate dropdown. items = options ("60 Hz", ...), value = the option picked. */
export const Display: React.FC<P> = ({ scene }) => {
  const { frame, grab, g } = useAct(scene);
  const { theme } = useTheme();
  const opts = rows(scene).map((r) => r[0]);
  const pick = idx(scene.value, opts.length, opts.length);
  const hz0 = num(opts[0], 60);
  const hz1 = num(opts[pick], 144);
  const open = ease(frame, 8, 20) * (1 - ease(frame, grab + 6, grab + 14));
  const hz = Math.round(mix(hz0, hz1, g));
  const step = Math.max(1, Math.round(mix(8, 1, g))); // frames per drawn position: choppy at a low rate, smooth at a high one
  const t = Math.floor(frame / step) * step;
  const tri = Math.abs(((t * 11) % 1400) - 700) / 700;
  return (
    <UiShell scene={scene}>
      <Win title="Display">
        <Row label="Refresh rate" right={<span style={{ color: theme.accent, fontWeight: 800 }}>{frame < grab + 8 ? opts[0] : opts[pick]} ⌄</span>} active={ease(frame, grab - 8, grab)} />
        <div style={{ overflow: 'hidden', maxHeight: open * opts.length * 74, opacity: open, marginTop: 10, display: 'flex', flexDirection: 'column', gap: 8 }}>
          {opts.map((o, i) => (
            <div key={i} data-cursor={i === pick ? 'target' : undefined} style={{ height: 66, display: 'flex', alignItems: 'center', padding: '0 26px', borderRadius: 16, fontSize: 32, fontWeight: 600, background: i === pick && frame >= grab - 6 ? `${theme.accent}33` : 'rgba(255,255,255,0.05)', border: `2px solid ${i === pick && frame >= grab - 6 ? theme.accent : 'transparent'}` }}>
              {o}
            </div>
          ))}
        </div>
        <div style={{ position: 'relative', height: 190, marginTop: 22, borderRadius: 22, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: 18, right: 26, fontFamily: MONO, fontSize: 40, fontWeight: 700, color: theme.accent }}>{hz} Hz</div>
          <div style={{ position: 'absolute', left: 40 + tri * 780, top: 74, width: 52, height: 52, borderRadius: 26, background: '#fff', boxShadow: `0 0 28px ${theme.accent}`, opacity: 0.95 }} />
        </div>
      </Win>
    </UiShell>
  );
};

/* 2 ─ taskmgr: items = processes "Name|percent", value = the row the pointer ends. */
export const TaskMgr: React.FC<P> = ({ scene }) => {
  const { frame, grab, done, g } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pick = idx(scene.value, rs.length, 1);
  const collapse = ease(frame, grab + 6, done + 4);
  const total = rs.reduce((a, r, i) => a + num(r[1]) * (i === pick ? 1 - collapse : 1), 0);
  const level = Math.max(0.08, Math.min(0.95, total / 100));
  return (
    <UiShell scene={scene}>
      <Win title="Task Manager">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 8 }}>
          <span style={{ fontSize: 30, color: MUTED }}>CPU</span>
          <span style={{ fontFamily: MONO, fontSize: 56, fontWeight: 700, color: total > 80 ? WARN : GOOD }}>{Math.round(Math.min(100, total))}%</span>
        </div>
        <Graph seed={`cpu${scene.text}`} width={860} height={170} level={level} calm={collapse * 0.7} reveal={ease(frame, 4, 28)} />
        <div style={{ marginTop: 22, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {rs.map((r, i) => {
            const mine = i === pick;
            const h = mine ? 76 * (1 - collapse) : 76;
            return (
              <div key={i} style={{ height: h, opacity: mine ? 1 - collapse : 1, overflow: 'hidden' }}>
                <Row label={r[0]} height={70} active={mine ? ease(frame, grab - 8, grab) : 0} right={
                  <>
                    <span style={{ width: 150, height: 14, borderRadius: 7, background: 'rgba(255,255,255,0.14)', overflow: 'hidden', display: 'inline-block' }}>
                      <span style={{ display: 'block', width: `${num(r[1])}%`, height: '100%', background: num(r[1]) > 40 ? WARN : theme.accent }} />
                    </span>
                    <span style={{ fontFamily: MONO, width: 90, textAlign: 'right', color: INK }}>{num(r[1])}%</span>
                    {mine && <Chip target bg={BAD} color="#fff" size={26} style={{ opacity: ease(frame, grab - 14, grab - 6), transform: `scale(${1 - 0.1 * (frame >= grab && frame < grab + 6 ? 1 : 0)})` }}>End task</Chip>}
                  </>
                } />
              </div>
            );
          })}
        </div>
      </Win>
    </UiShell>
  );
};

/* 3 ─ bios: items = options "Option|Value", value = the row changed, accentText = its new value. */
export const Bios: React.FC<P> = ({ scene }) => {
  const { frame, grab } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pick = idx(scene.value, rs.length, 1);
  const swap = frame >= grab + 8;
  return (
    <UiShell scene={scene}>
      <Win title="Setup Utility" mono style={{ background: 'rgba(6,14,38,0.92)' }}>
        <div style={{ fontFamily: MONO, fontSize: 24, color: MUTED, letterSpacing: 3, marginBottom: 14, textTransform: 'uppercase' }}>Advanced</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {rs.map((r, i) => (
            <Row key={i} target={i === pick} height={76} label={<span style={{ fontFamily: MONO }}>{r[0]}</span>} active={i === pick ? ease(frame, grab - 8, grab) : 0}
              right={<span style={{ fontFamily: MONO, fontSize: 32, fontWeight: 700, color: i === pick && swap ? theme.accent : INK, textShadow: i === pick && swap ? `0 0 18px ${theme.accent}` : 'none' }}>[{i === pick && swap ? scene.accentText ?? r[1] : r[1]}]</span>} />
          ))}
        </div>
        <div style={{ fontFamily: MONO, fontSize: 22, color: MUTED, marginTop: 22 }}>↑↓ select   Enter change   Esc back</div>
        <div style={{ fontFamily: MONO, fontSize: 24, color: WARN, marginTop: 8, opacity: ease(frame, grab, grab + 12) }}>! Note the old value first</div>
      </Win>
    </UiShell>
  );
};

/* 4 ─ terminal: code = lines ("$ " lines are commands, the rest is output), value = the line the pointer selects. */
export const Terminal: React.FC<P> = ({ scene }) => {
  const { frame, grab } = useAct(scene);
  const { theme } = useTheme();
  const lines = (scene.code ?? []).slice(0, 8);
  const pick = idx(scene.value, lines.length, lines.length);
  const total = lines.join('\n').length || 1;
  let left = Math.floor(ease(frame, 6, grab - 6) * total);
  return (
    <UiShell scene={scene}>
      <Win title="Terminal" mono style={{ background: 'rgba(4,10,24,0.94)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minHeight: 360 }}>
          {lines.map((line, i) => {
            const shown = Math.max(0, Math.min(line.length, left));
            left -= line.length + 1;
            const cmd = line.startsWith('$');
            const sel = i === pick ? ease(frame, grab, grab + 14) : 0;
            return (
              <div key={i} style={{ fontFamily: MONO, fontSize: 34, color: cmd ? INK : MUTED, whiteSpace: 'pre', minHeight: 50 }}>
                <span data-cursor={i === pick ? 'target' : undefined} style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 8, background: sel > 0 ? `${theme.accent}${Math.round(sel * 70).toString(16).padStart(2, '0')}` : 'transparent', color: sel > 0.5 ? '#fff' : undefined }}>
                  {line.slice(0, shown)}
                </span>
                {shown > 0 && shown < line.length && <span style={{ background: theme.accent, color: 'transparent' }}>▌</span>}
              </div>
            );
          })}
        </div>
      </Win>
    </UiShell>
  );
};

/* 5 ─ gpupanel: items = switches "Name|on/off", value = the one the pointer flips; the frame-time graph calms down. */
export const GpuPanel: React.FC<P> = ({ scene }) => {
  const { frame, grab, done } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pick = idx(scene.value, rs.length, 1);
  const calm = ease(frame, grab + 6, done + 14);
  return (
    <UiShell scene={scene}>
      <Win title="Graphics Control Panel">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {rs.map((r, i) => {
            const on0 = /^(on|yes|true|1)/i.test(r[1] ?? '') ? 1 : 0;
            const on = i === pick ? mix(on0, 1 - on0, ease(frame, grab, grab + 8)) : on0;
            return <Row key={i} label={r[0]} active={i === pick ? ease(frame, grab - 8, grab) : 0} right={<><span style={{ fontFamily: MONO, fontSize: 28, width: 70, textAlign: 'right', color: on > 0.5 ? theme.accent : MUTED }}>{on > 0.5 ? 'ON' : 'OFF'}</span><Switch on={on} target={i === pick} /></>} />;
          })}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 26, fontSize: 28, color: MUTED }}>
          <span>Frame time</span>
          <span style={{ color: calm > 0.6 ? GOOD : WARN, fontWeight: 700 }}>{calm > 0.6 ? 'steady' : 'uneven'}</span>
        </div>
        <Graph seed={`gpu${scene.text}`} width={860} height={190} level={0.5} calm={calm} reveal={ease(frame, 4, 30)} />
      </Win>
    </UiShell>
  );
};

/* 6 ─ gamemenu: items = sliders "Name|from>to", value = the slider dragged, leftValue / rightValue = FPS before / after. */
export const GameMenu: React.FC<P> = ({ scene }) => {
  const { frame, grab, done, g } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pick = idx(scene.value, rs.length, 1);
  const fps0 = scene.leftValue ?? 60;
  const fps1 = scene.rightValue ?? 90;
  const fps = Math.round(mix(fps0, fps1, g));
  return (
    <UiShell scene={scene}>
      <Win title="Graphics">
        <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 18 }}>
          <span style={{ fontSize: 30, color: MUTED }}>Frame rate</span>
          <span style={{ fontFamily: MONO, fontSize: 92, fontWeight: 700, color: fps1 >= fps0 ? theme.accent : WARN, textShadow: `0 0 26px ${theme.accent}66` }}>{fps}<span style={{ fontSize: 36, color: MUTED }}> FPS</span></span>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {rs.map((r, i) => {
            const [a, b] = (r[1] ?? '50>50').split('>').map((x) => num(x, 50));
            const v = (i === pick ? mix(a, b ?? a, g) : a) / 100;
            return <Row key={i} label={r[0]} height={92} active={i === pick ? ease(frame, grab - 8, grab) * (1 - ease(frame, done, done + 8)) : 0} right={<><Slider v={v} width={440} target={i === pick} /><span style={{ fontFamily: MONO, width: 78, textAlign: 'right', color: INK }}>{Math.round(v * 100)}</span></>} />;
          })}
        </div>
      </Win>
    </UiShell>
  );
};

/* 7 ─ frametime: value = the spike in ms, leftValue = the baseline in ms; the pointer selects the spike. */
export const FrameTime: React.FC<P> = ({ scene }) => {
  const { frame, grab } = useAct(scene);
  const { theme } = useTheme();
  const spike = scene.value ?? 40;
  const base = scene.leftValue ?? 7;
  const top = Math.max(spike * 1.25, base * 3, 20);
  const W = 860;
  const H = 360;
  const at = 38;
  const sel = ease(frame, grab, grab + 14);
  return (
    <UiShell scene={scene}>
      <Win title="Frame time (ms)">
        <div style={{ position: 'relative', width: W, height: H + 10 }}>
          <Graph seed={`ft${scene.text}`} width={W} height={H} level={base / top} calm={0.55} points={60} reveal={ease(frame, 4, grab - 2)} spikeAt={at} spike={(spike - base) / top} />
          <div data-cursor="target" style={{ position: 'absolute', left: (at / 59) * W - 48, top: 0, width: 96, height: H, borderRadius: 18, border: `3px solid ${theme.accent}`, background: `${theme.accent}22`, opacity: sel }} />
          <div style={{ position: 'absolute', left: (at / 59) * W + 60, top: Math.max(0, H - (spike / top) * H - 6), fontFamily: MONO, fontSize: 40, fontWeight: 700, color: BAD, opacity: sel }}>{spike} ms</div>
          <div style={{ position: 'absolute', left: 0, bottom: -4, fontFamily: MONO, fontSize: 24, color: MUTED }}>usual {base} ms</div>
        </div>
      </Win>
    </UiShell>
  );
};

/* 8 ─ speedtest: value = the result, unit = its unit, items = extra readings "Ping|12 ms"; the pointer drags the needle up to the result. */
export const SpeedTest: React.FC<P> = ({ scene }) => {
  const { g } = useAct(scene);
  const { theme } = useTheme();
  const value = scene.value ?? 100;
  const step = value > 400 ? 200 : value > 100 ? 100 : value > 40 ? 50 : 20;
  const max = Math.ceil((value * 1.2) / step) * step;
  const cx = 380;
  const cy = 330;
  const R = 300;
  const v = value * g;
  const ang = Math.PI * (1 - Math.min(1, v / max));
  const tip = { x: cx + R * Math.cos(ang), y: cy - R * Math.sin(ang) };
  const arc = (a: number) => `M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R * Math.cos(Math.PI - a)} ${cy - R * Math.sin(Math.PI - a)}`;
  return (
    <UiShell scene={scene}>
      <Win title="Speed test">
        <svg width={760} height={380} viewBox="0 0 760 380" style={{ display: 'block', margin: '0 auto', overflow: 'visible' }}>
          <path d={`M ${cx - R} ${cy} A ${R} ${R} 0 0 1 ${cx + R} ${cy}`} fill="none" stroke="rgba(255,255,255,0.14)" strokeWidth={26} strokeLinecap="round" />
          <path d={arc(Math.PI * Math.min(1, v / max))} fill="none" stroke={theme.accent} strokeWidth={26} strokeLinecap="round" style={{ filter: `drop-shadow(0 0 12px ${theme.accent}99)` }} />
          <line x1={cx} y1={cy} x2={tip.x} y2={tip.y} stroke="#fff" strokeWidth={8} strokeLinecap="round" />
          <circle cx={cx} cy={cy} r={20} fill="#fff" />
          <circle data-cursor="target" cx={tip.x} cy={tip.y} r={22} fill="#fff" stroke={theme.accent} strokeWidth={7} />
          <text x={cx - R} y={cy + 52} fill={MUTED} fontFamily={MONO} fontSize={26} textAnchor="middle">0</text>
          <text x={cx + R} y={cy + 52} fill={MUTED} fontFamily={MONO} fontSize={26} textAnchor="middle">{max}</text>
        </svg>
        <div style={{ textAlign: 'center', fontFamily: MONO, fontWeight: 700, fontSize: 104, color: INK, marginTop: -6 }}>
          {Math.round(v)}<span style={{ fontSize: 40, color: theme.accent }}> {scene.unit ?? 'Mbps'}</span>
        </div>
        <div style={{ display: 'flex', justifyContent: 'center', gap: 22, marginTop: 16 }}>
          {rows(scene).map((r, i) => <Chip key={i} bg="rgba(255,255,255,0.1)" color={INK} size={28}><span style={{ color: MUTED, marginRight: 12 }}>{r[0]}</span>{r[1]}</Chip>)}
        </div>
      </Win>
    </UiShell>
  );
};

/* 9 ─ wifilist: items = networks "Name|band|bars", value = the network the pointer presses. */
export const WifiList: React.FC<P> = ({ scene }) => {
  const { frame, grab, g } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pick = idx(scene.value, rs.length, rs.length);
  return (
    <UiShell scene={scene}>
      <Win title="Wi-Fi">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {rs.map((r, i) => {
            const mine = i === pick;
            const level = mine ? mix(num(r[2], 2), 4, g) : num(r[2], 2);
            return (
              <Row key={i} target={mine} height={104} active={mine ? ease(frame, grab - 8, grab) : 0}
                label={<span style={{ display: 'flex', flexDirection: 'column', lineHeight: 1.15 }}><span>{r[0]}</span><span style={{ fontSize: 24, color: mine && g > 0.6 ? GOOD : MUTED, fontWeight: 500 }}>{mine && g > 0.6 ? 'Connected' : 'Secured'}</span></span>}
                right={<><Chip bg="rgba(255,255,255,0.12)" color={mine && g > 0.6 ? theme.accent : INK} size={26}>{r[1]}</Chip>{mine && g > 0.6 && <Glyph name="check" color={GOOD} size={40} />}<Bars level={level} /></>} />
            );
          })}
        </div>
      </Win>
    </UiShell>
  );
};

/* 10 ─ router: items = fields "Name|value", value = the field edited, accentText = its new value. */
export const Router: React.FC<P> = ({ scene }) => {
  const { frame, grab, done } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pick = idx(scene.value, rs.length, 1);
  const next = scene.accentText ?? '';
  return (
    <UiShell scene={scene}>
      <Win title="Router admin" style={{ fontFamily: SANS }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {rs.map((r, i) => {
            const mine = i === pick;
            const old = r[1] ?? '';
            const erased = old.slice(0, Math.round(old.length * (1 - ease(frame, grab, grab + 10))));
            const typed = next.slice(0, Math.round(next.length * ease(frame, grab + 10, done)));
            const text = mine ? erased + typed : old;
            const focus = mine ? ease(frame, grab - 6, grab) : 0;
            return (
              <Row key={i} label={r[0]} height={96} right={
                <span data-cursor={mine ? 'target' : undefined} style={{ minWidth: 330, height: 60, display: 'inline-flex', alignItems: 'center', padding: '0 20px', borderRadius: 14, fontFamily: MONO, fontSize: 32, color: INK, background: 'rgba(0,0,0,0.35)', border: `3px solid ${focus > 0.5 ? theme.accent : 'rgba(255,255,255,0.18)'}`, boxShadow: focus > 0.5 ? `0 0 22px ${theme.accent}66` : 'none' }}>
                  {text}
                  {mine && focus > 0.5 && frame % 20 < 12 && <span style={{ width: 3, height: 34, background: theme.accent, marginLeft: 3 }} />}
                </span>
              } />
            );
          })}
        </div>
        <div style={{ marginTop: 24, display: 'flex', justifyContent: 'flex-end' }}>
          <Chip bg={frame > done ? GOOD : 'rgba(255,255,255,0.14)'} color={frame > done ? '#05070C' : MUTED}>{frame > done ? 'Saved' : 'Apply'}</Chip>
        </div>
      </Win>
    </UiShell>
  );
};

export { WIN_W };
