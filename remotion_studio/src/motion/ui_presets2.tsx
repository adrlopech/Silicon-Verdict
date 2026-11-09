import React from 'react';
import { MONO } from './fonts';
import { Kicker, SafeBox, useTheme } from './primitives';
import { MotionScene } from './types';
import { BAD, Chip, GOOD, Glyph, INK, MUTED, Row, Slider, Switch, UiShell, WARN, Win, ease, mix, num, parts, rows, useAct } from './ui_kit';

/** Presets 11-20: shortcuts, files, storage, battery, memory, specs, rankings, builds, slots and privacy. */
type P = { scene: MotionScene };
const idx = (value: number | undefined, len: number, fallback: number) => Math.max(0, Math.min(len - 1, Math.round(value ?? fallback) - 1));

/* 11 ─ keycaps: items = keys, accentText = what the shortcut does; the keys are pressed one after another. */
export const Keycaps: React.FC<P> = ({ scene }) => {
  const { frame, grab, done } = useAct(scene);
  const { theme } = useTheme();
  const keys = rows(scene).map((r) => r[0]);
  return (
    <UiShell scene={scene} gap={44}>
      <Win title="Keyboard">
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: 22, flexWrap: 'wrap', minHeight: 240 }}>
          {keys.map((k, i) => {
            const down = ease(frame, grab + i * 10, grab + i * 10 + 5) * (1 - ease(frame, done + 14, done + 22));
            return (
              <React.Fragment key={i}>
                {i > 0 && <span style={{ fontFamily: MONO, fontSize: 48, color: MUTED }}>+</span>}
                <div data-cursor={i === 0 ? 'target' : undefined} style={{ minWidth: 150, height: 150, padding: '0 34px', display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: 26, fontFamily: MONO, fontWeight: 800, fontSize: 52, color: down > 0.5 ? '#05070C' : INK, background: down > 0.5 ? theme.accent : 'rgba(255,255,255,0.1)', border: '2px solid rgba(255,255,255,0.2)', borderBottom: `${12 - down * 9}px solid rgba(255,255,255,0.28)`, transform: `translateY(${down * 9}px)`, boxShadow: down > 0.5 ? `0 0 40px ${theme.accent}` : '0 14px 24px rgba(0,0,0,0.35)' }}>{k}</div>
              </React.Fragment>
            );
          })}
        </div>
        <div style={{ marginTop: 26, textAlign: 'center', opacity: ease(frame, done - 2, done + 12), transform: `translateY(${(1 - ease(frame, done - 2, done + 12)) * 16}px)` }}>
          <Chip size={36}>{scene.accentText ?? ''}</Chip>
        </div>
      </Win>
    </UiShell>
  );
};

/* 12 ─ filemgr: items[0] = the file, items[1..] = folders "Name|note", value = the folder (1-based among the folders) the file is dropped on. */
export const FileMgr: React.FC<P> = ({ scene }) => {
  const { frame, grab, g } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const file = rs[0]?.[0] ?? 'file';
  const folders = rs.slice(1);
  const pick = idx(scene.value, folders.length, 1);
  const dy = 118 + pick * 96 + 12;
  return (
    <UiShell scene={scene}>
      <Win title="Files">
        <div style={{ height: 106, display: 'flex', alignItems: 'center' }}>
          <div data-cursor="target" style={{ display: 'inline-flex', alignItems: 'center', gap: 16, padding: '12px 26px', borderRadius: 18, background: '#16294d', border: `2px solid ${theme.accent}`, fontSize: 32, fontWeight: 700, boxShadow: g > 0 && g < 1 ? `0 22px 44px rgba(0,0,0,0.5), 0 0 28px ${theme.accent}66` : `0 0 18px ${theme.accent}33`, transform: `translate(${mix(0, 250, g)}px, ${mix(0, dy, g)}px) scale(${1 - 0.2 * g}) rotate(${Math.sin(g * Math.PI) * -3}deg)`, opacity: 1 - ease(frame, grab + 30, grab + 38), position: 'relative', zIndex: 5 }}>
            <Glyph name="file" color={theme.accent} size={38} />
            {file}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 10 }}>
          {folders.map((f, i) => (
            <Row key={i} height={84} active={i === pick ? ease(frame, grab + 8, grab + 26) : 0} label={<span style={{ display: 'flex', alignItems: 'center', gap: 16 }}><Glyph name="folder" color={theme.accent} size={38} />{f[0]}</span>}
              right={<>{f[1] && <span style={{ fontSize: 26 }}>{f[1]}</span>}{i === pick && g > 0.95 && <Glyph name="check" color={GOOD} size={34} />}</>} />
          ))}
        </div>
      </Win>
    </UiShell>
  );
};

/* 13 ─ diskbar: items = segments "Name|percent" (the last one is the free space), value = the free percent afterwards, leftValue / rightValue = speed before / after in MB/s. */
export const DiskBar: React.FC<P> = ({ scene }) => {
  const { frame, grab, g } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pcts = rs.map((r) => num(r[1]));
  const free0 = pcts[pcts.length - 1] ?? 10;
  const free1 = scene.value ?? free0 + 20;
  const free = mix(free0, free1, g);
  const used = pcts.slice(0, -1);
  used[used.length - 1] = Math.max(2, used[used.length - 1] - (free - free0)); // the freed space comes out of the last used segment
  const palette = [theme.accent, '#007AFF', '#8A8CFF', '#FFD166'];
  const W = 860;
  let x = 0;
  const speed = Math.round(mix(scene.leftValue ?? 300, scene.rightValue ?? 1800, g));
  return (
    <UiShell scene={scene}>
      <Win title="Storage">
        <div style={{ position: 'relative', width: W, height: 96, borderRadius: 24, overflow: 'visible', marginTop: 20 }}>
          <div style={{ display: 'flex', width: W, height: 96, borderRadius: 24, overflow: 'hidden', background: 'rgba(255,255,255,0.08)' }}>
            {used.map((p, i) => <div key={i} style={{ width: `${(p / 100) * W}px`, background: palette[i % palette.length], opacity: 0.9 }} />)}
            <div style={{ flex: 1, background: 'repeating-linear-gradient(135deg, rgba(255,255,255,0.14) 0 12px, rgba(255,255,255,0.05) 12px 24px)' }} />
          </div>
          {(() => { x = (used.reduce((a, b) => a + b, 0) / 100) * W; return null; })()}
          <div style={{ position: 'absolute', left: x - 3, top: -14, width: 6, height: 124, borderRadius: 3, background: '#fff', opacity: ease(frame, 10, 22) }} />
          <div data-cursor="target" style={{ position: 'absolute', left: x - 26, top: 24, width: 52, height: 52, borderRadius: 26, background: '#fff', border: `6px solid ${theme.accent}`, boxShadow: `0 0 24px ${theme.accent}, 0 6px 14px rgba(0,0,0,0.5)`, opacity: ease(frame, 10, 22), transform: `scale(${1 + 0.1 * (frame >= grab && g < 1 ? 1 : 0)})` }} />
        </div>
        <div style={{ display: 'flex', gap: 22, marginTop: 24, flexWrap: 'wrap' }}>
          {rs.map((r, i) => (
            <span key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 10, fontSize: 28, color: INK }}>
              <span style={{ width: 20, height: 20, borderRadius: 6, background: i === rs.length - 1 ? 'rgba(255,255,255,0.4)' : palette[i % palette.length] }} />
              {r[0]} <span style={{ fontFamily: MONO, color: MUTED }}>{Math.round(i === rs.length - 1 ? free : used[i])}%</span>
            </span>
          ))}
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginTop: 30 }}>
          <span style={{ fontSize: 30, color: MUTED }}>Write speed</span>
          <span style={{ fontFamily: MONO, fontSize: 70, fontWeight: 700, color: g > 0.5 ? GOOD : WARN }}>{speed.toLocaleString('en-US')}<span style={{ fontSize: 30, color: MUTED }}> MB/s</span></span>
        </div>
      </Win>
    </UiShell>
  );
};

/* 14 ─ battery: items[0] = "Charge limit|100>80" (the slider the pointer drags), value = the battery health in percent. */
export const Battery: React.FC<P> = ({ scene }) => {
  const { frame, grab, done, g } = useAct(scene);
  const { theme } = useTheme();
  const [a, b] = (rows(scene)[0]?.[1] ?? '100>80').split('>').map((x) => num(x, 100));
  const limit = mix(a, b ?? a, g);
  return (
    <UiShell scene={scene}>
      <Win title="Battery">
        <div style={{ display: 'flex', justifyContent: 'center', margin: '8px 0 26px' }}>
          <div style={{ position: 'relative', width: 420, height: 190, borderRadius: 40, border: '8px solid rgba(255,255,255,0.5)' }}>
            <div style={{ position: 'absolute', right: -30, top: 56, width: 18, height: 66, borderRadius: 9, background: 'rgba(255,255,255,0.5)' }} />
            <div style={{ position: 'absolute', left: 10, top: 10, bottom: 10, width: `${(limit / 100) * 380}px`, borderRadius: 26, background: `linear-gradient(90deg, #007AFF, ${limit > 85 ? WARN : theme.accent})`, boxShadow: `0 0 30px ${theme.accent}66` }} />
            <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: MONO, fontWeight: 700, fontSize: 70, color: '#fff', textShadow: '0 2px 10px rgba(0,0,0,0.6)' }}>{Math.round(limit)}%</div>
          </div>
        </div>
        <Row label={rows(scene)[0]?.[0] ?? 'Charge limit'} height={92} active={ease(frame, grab - 8, grab) * (1 - ease(frame, done, done + 8))} right={<><Slider v={limit / 100} width={400} target /><span style={{ fontFamily: MONO, width: 84, textAlign: 'right', color: INK }}>{Math.round(limit)}%</span></>} />
        <div style={{ marginTop: 12 }}>
          <Row label="Battery health" height={84} right={<span style={{ fontFamily: MONO, fontSize: 34, color: GOOD, fontWeight: 700 }}>{scene.value ?? 90}%</span>} />
        </div>
      </Win>
    </UiShell>
  );
};

/* 15 ─ tabmem: items = tabs "Name|MB", value = the heavy tab the pointer closes. */
export const TabMem: React.FC<P> = ({ scene }) => {
  const { frame, grab, done } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pick = idx(scene.value, rs.length, 1);
  const collapse = ease(frame, grab + 6, done + 4);
  const mb = rs.map((r) => num(r[1]));
  const total0 = mb.reduce((a, b) => a + b, 0);
  const total = total0 - mb[pick] * collapse;
  const fmt = (m: number) => (m >= 1000 ? `${(m / 1000).toFixed(1)} GB` : `${Math.round(m)} MB`);
  return (
    <UiShell scene={scene}>
      <Win title="Browser tasks">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
          <span style={{ fontSize: 30, color: MUTED }}>Memory in use</span>
          <span style={{ fontFamily: MONO, fontSize: 62, fontWeight: 700, color: total > total0 * 0.8 ? WARN : GOOD }}>{fmt(total)}</span>
        </div>
        <div style={{ height: 18, borderRadius: 9, background: 'rgba(255,255,255,0.12)', overflow: 'hidden', margin: '14px 0 24px' }}>
          <div style={{ width: `${Math.min(100, (total / (total0 * 1.15)) * 100)}%`, height: '100%', background: `linear-gradient(90deg, #007AFF, ${theme.accent})` }} />
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {rs.map((r, i) => {
            const mine = i === pick;
            return (
              <div key={i} style={{ height: mine ? 84 * (1 - collapse) : 84, opacity: mine ? 1 - collapse : 1, overflow: 'hidden' }}>
                <Row label={r[0]} height={76} active={mine ? ease(frame, grab - 8, grab) : 0} right={<><span style={{ fontFamily: MONO, fontSize: 30, color: INK }}>{fmt(num(r[1]))}</span><span data-cursor={mine ? 'target' : undefined} style={{ width: 52, height: 52, borderRadius: 14, background: mine ? BAD : 'rgba(255,255,255,0.1)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', transform: `scale(${mine && frame >= grab && frame < grab + 6 ? 0.88 : 1})` }}><Glyph name="cross" color="#fff" size={26} /></span></>} />
              </div>
            );
          })}
        </div>
      </Win>
    </UiShell>
  );
};

/* 16 ─ speclabel: text = the label, items = its parts "token|what it means", value = the part the pointer selects; the meanings appear one by one. */
export const SpecLabel: React.FC<P> = ({ scene }) => {
  const { frame, grab } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pick = idx(scene.value, rs.length, 1);
  return (
    <SafeBox gap={40}>
      <Kicker text={scene.kicker ?? 'decoded'} />
      <div style={{ display: 'flex', flexWrap: 'wrap', justifyContent: 'center', gap: 14, maxWidth: 940 }}>
        {rs.map((r, i) => {
          const on = ease(frame, grab - 4, grab + 8);
          const lit = i === pick ? on : 0;
          const pop = ease(frame, 6 + i * 6, 16 + i * 6);
          return (
            <div key={i} data-cursor={i === pick ? 'target' : undefined} style={{ padding: '14px 26px', borderRadius: 20, fontFamily: MONO, fontWeight: 800, fontSize: 70, color: lit > 0.5 ? '#05070C' : INK, background: lit > 0.5 ? theme.accent : 'rgba(255,255,255,0.1)', border: `2px solid ${lit > 0.5 ? theme.accent : 'rgba(255,255,255,0.22)'}`, opacity: pop, transform: `translateY(${(1 - pop) * 30}px) scale(${1 + lit * 0.06})`, boxShadow: lit > 0.5 ? `0 0 40px ${theme.accent}99` : 'none' }}>{r[0]}</div>
          );
        })}
      </div>
      <div style={{ width: 900, display: 'flex', flexDirection: 'column', gap: 12 }}>
        {rs.map((r, i) => {
          const a = ease(frame, 22 + i * 14, 34 + i * 14);
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 22, padding: '14px 26px', borderRadius: 18, background: i === pick && frame >= grab ? `${theme.accent}26` : 'rgba(255,255,255,0.06)', opacity: a, transform: `translateX(${(1 - a) * -40}px)`, textAlign: 'left' }}>
              <span style={{ fontFamily: MONO, fontWeight: 800, fontSize: 38, color: theme.accent, minWidth: 150 }}>{r[0]}</span>
              <span style={{ fontSize: 34, fontWeight: 600, color: INK }}>{r[1]}</span>
            </div>
          );
        })}
      </div>
    </SafeBox>
  );
};

/* 17 ─ leaderboard: items = rows "Name|score" in their true order, value = the row that starts misplaced at the bottom and is dragged up to its place. */
export const Leaderboard: React.FC<P> = ({ scene }) => {
  const { frame, grab, g } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const n = rs.length;
  const pick = idx(scene.value, n, n);
  const best = Math.max(1, ...rs.map((r) => num(r[1])));
  const rowH = 100;
  return (
    <UiShell scene={scene}>
      <Win title="Benchmark results">
        <div style={{ position: 'relative', height: n * rowH }}>
          {rs.map((r, j) => {
            const start = j === pick ? n - 1 : j > pick ? j - 1 : j;
            const slot = mix(start, j, g);
            const mine = j === pick;
            const lift = mine ? Math.sin(g * Math.PI) : 0;
            return (
              <div key={j} data-cursor={mine ? 'target' : undefined} style={{ position: 'absolute', left: 0, right: 0, top: slot * rowH, height: rowH - 12, zIndex: mine ? 5 : 1, transform: `scale(${1 + 0.03 * lift})` }}>
                <Row label={<span style={{ display: 'flex', alignItems: 'center', gap: 22 }}><span style={{ fontFamily: MONO, width: 46, color: MUTED }}>{Math.round(slot) + 1}</span>{r[0]}</span>} height={rowH - 12} active={mine ? ease(frame, grab - 8, grab) : 0}
                  right={<><span style={{ width: 200, height: 14, borderRadius: 7, background: 'rgba(255,255,255,0.14)', overflow: 'hidden', display: 'inline-block' }}><span style={{ display: 'block', width: `${(num(r[1]) / best) * 100}%`, height: '100%', background: mine ? theme.accent : '#007AFF' }} /></span><span style={{ fontFamily: MONO, width: 110, textAlign: 'right', color: INK }}>{num(r[1])}</span></>} style={{ boxShadow: mine && lift > 0.05 ? `0 24px 50px rgba(0,0,0,0.5), 0 0 30px ${theme.accent}55` : undefined }} />
              </div>
            );
          })}
        </div>
      </Win>
    </UiShell>
  );
};

/* 18 ─ partpicker: items = slots "Slot|Part" ("Slot|empty" for the one being filled), value = the empty slot, accentText = the part, leftValue = 1 if it fits and 0 if not, unit = the reason it does not. */
export const PartPicker: React.FC<P> = ({ scene }) => {
  const { frame, grab, done, g } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const n = rs.length;
  const pick = idx(scene.value, n, n);
  const fits = (scene.leftValue ?? 1) > 0;
  const dy = -((n - pick) * 96 + 33);
  const verdict = ease(frame, done, done + 8);
  const shake = !fits && verdict > 0 && frame < done + 22 ? Math.sin(frame * 1.7) * 8 * (1 - ease(frame, done, done + 22)) : 0;
  return (
    <UiShell scene={scene}>
      <Win title="Your build">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {rs.map((r, i) => {
            const empty = i === pick;
            return (
              <Row key={i} height={84} label={r[0]} active={empty ? ease(frame, grab + 8, grab + 24) : 0}
                right={empty ? <span style={{ minWidth: 470, height: 56, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', borderRadius: 14, border: `3px dashed ${verdict > 0 ? (fits ? GOOD : BAD) : 'rgba(255,255,255,0.3)'}`, fontSize: 26, color: MUTED }}>{g < 0.9 ? 'empty slot' : ''}{verdict > 0 && <span style={{ marginLeft: 12, display: 'inline-flex' }}><Glyph name={fits ? 'check' : 'cross'} color={fits ? GOOD : BAD} size={36} /></span>}</span> : <span style={{ color: INK }}>{r[1]}</span>} />
            );
          })}
        </div>
        <div style={{ height: 96, marginTop: 30, display: 'flex', alignItems: 'center' }}>
          <div data-cursor="target" style={{ display: 'inline-flex', alignItems: 'center', padding: '14px 28px', borderRadius: 18, fontSize: 30, fontWeight: 800, color: verdict > 0 && !fits ? '#fff' : '#05070C', background: verdict > 0 ? (fits ? GOOD : BAD) : theme.accent, whiteSpace: 'nowrap', boxShadow: g > 0 && g < 1 ? `0 22px 44px rgba(0,0,0,0.5), 0 0 28px ${theme.accent}77` : `0 0 22px ${theme.accent}55`, transform: `translate(${mix(0, 360, g) + shake}px, ${mix(0, dy, g)}px) rotate(${Math.sin(g * Math.PI) * -3}deg)`, position: 'relative', zIndex: 5 }}>
            {scene.accentText}
          </div>
        </div>
        {!fits && scene.unit && <div style={{ marginTop: 14, fontSize: 28, color: BAD, fontWeight: 700, opacity: verdict }}>{scene.unit}</div>}
      </Win>
    </UiShell>
  );
};

/* 19 ─ dimm: items = the four slot names, leftValue / rightValue = the two slots (1-4) the sticks go into, accentText = the badge that lights up. */
export const Dimm: React.FC<P> = ({ scene }) => {
  const { frame, grab, done } = useAct(scene);
  const { theme } = useTheme();
  const names = rows(scene).map((r) => r[0]);
  const slots = names.length >= 4 ? names.slice(0, 4) : ['A1', 'A2', 'B1', 'B2'];
  const first = Math.max(1, Math.min(4, Math.round(scene.leftValue ?? 2))) - 1;
  const second = Math.max(1, Math.min(4, Math.round(scene.rightValue ?? 4))) - 1;
  const ins = (i: number) => (i === first ? ease(frame, grab, grab + 14) : i === second ? ease(frame, grab + 14, grab + 28) : 0);
  const both = ease(frame, done - 2, done + 12);
  return (
    <UiShell scene={scene}>
      <Win title="Motherboard">
        <div style={{ display: 'flex', justifyContent: 'center', gap: 34, height: 440, position: 'relative' }}>
          {slots.map((s, i) => {
            const k = ins(i);
            const used = i === first || i === second;
            return (
              <div key={i} style={{ width: 130, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
                <div data-cursor={i === first ? 'target' : undefined} style={{ position: 'relative', width: 120, height: 360, borderRadius: 18, background: 'rgba(255,255,255,0.07)', border: `3px solid ${used && k > 0.9 ? theme.accent : 'rgba(255,255,255,0.22)'}`, overflow: 'hidden', boxShadow: used && k > 0.9 && both > 0.5 ? `0 0 34px ${theme.accent}88` : 'none' }}>
                  <div style={{ position: 'absolute', left: 14, right: 14, top: 14, bottom: 14, borderRadius: 8, background: 'repeating-linear-gradient(0deg, rgba(255,255,255,0.12) 0 6px, transparent 6px 14px)' }} />
                  {used && (
                    <div style={{ position: 'absolute', left: 8, right: 8, top: 10, height: 338, borderRadius: 12, background: '#0f2a52', border: `3px solid ${theme.accent}`, transform: `translateY(${(1 - k) * -380}px)`, display: 'flex', flexDirection: 'column', justifyContent: 'space-evenly', alignItems: 'center' }}>
                      {[0, 1, 2, 3].map((c) => <div key={c} style={{ width: 70, height: 34, borderRadius: 6, background: '#05070C', border: `2px solid ${theme.accent}88` }} />)}
                    </div>
                  )}
                </div>
                <span style={{ fontFamily: MONO, fontSize: 36, fontWeight: 700, color: used ? theme.accent : MUTED }}>{s}</span>
              </div>
            );
          })}
        </div>
        <div style={{ textAlign: 'center', marginTop: 12, opacity: both, transform: `translateY(${(1 - both) * 14}px)` }}>
          <Chip size={36}>{scene.accentText ?? 'Dual channel'}</Chip>
        </div>
      </Win>
    </UiShell>
  );
};

/* 20 ─ permissions: items = switches "Name|on", value = the one the pointer turns off; its icon leaves the status bar. */
export const Permissions: React.FC<P> = ({ scene }) => {
  const { frame, grab } = useAct(scene);
  const { theme } = useTheme();
  const rs = rows(scene);
  const pick = idx(scene.value, rs.length, 1);
  const glyph = (name: string): 'mic' | 'camera' | 'pin' => (/mic/i.test(name) ? 'mic' : /cam/i.test(name) ? 'camera' : 'pin');
  return (
    <UiShell scene={scene}>
      <Win title="Privacy">
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 22, minHeight: 56, marginBottom: 14 }}>
          {rs.map((r, i) => {
            const on0 = /^(on|yes|true|1)/i.test(parts(r.join('|'))[1] ?? 'on') ? 1 : 0;
            const on = i === pick ? on0 * (1 - ease(frame, grab + 6, grab + 16)) : on0;
            return <span key={i} style={{ opacity: on, transform: `scale(${0.6 + 0.4 * on})`, display: 'inline-flex' }}><Glyph name={glyph(r[0])} color={WARN} size={44} /></span>;
          })}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {rs.map((r, i) => {
            const on0 = /^(on|yes|true|1)/i.test(r[1] ?? 'on') ? 1 : 0;
            const on = i === pick ? on0 * (1 - ease(frame, grab, grab + 8)) : on0;
            return <Row key={i} height={92} active={i === pick ? ease(frame, grab - 8, grab) : 0} label={<span style={{ display: 'flex', alignItems: 'center', gap: 20 }}><Glyph name={glyph(r[0])} color={theme.accent} size={42} />{r[0]}</span>} right={<Switch on={on} target={i === pick} />} />;
          })}
        </div>
      </Win>
    </UiShell>
  );
};
