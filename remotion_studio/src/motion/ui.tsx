import React from 'react';
import { MotionScene } from './types';
import { Bios, Display, FrameTime, GameMenu, GpuPanel, Router, SpeedTest, TaskMgr, Terminal, WifiList } from './ui_presets';
import { Battery, DiskBar, Dimm, FileMgr, Keycaps, Leaderboard, PartPicker, Permissions, SpecLabel, TabMem } from './ui_presets2';
import { UiShell, Win } from './ui_kit';

/** The 20 drawn interfaces ("presets") of the `ui` scene. Each one animates a single change that the pointer performs (see ui_kit.tsx). */
export const UI_PRESETS: Record<string, React.FC<{ scene: MotionScene }>> = {
  display: Display,
  taskmgr: TaskMgr,
  bios: Bios,
  terminal: Terminal,
  gpupanel: GpuPanel,
  gamemenu: GameMenu,
  frametime: FrameTime,
  speedtest: SpeedTest,
  wifilist: WifiList,
  router: Router,
  keycaps: Keycaps,
  filemgr: FileMgr,
  diskbar: DiskBar,
  battery: Battery,
  tabmem: TabMem,
  speclabel: SpecLabel,
  leaderboard: Leaderboard,
  partpicker: PartPicker,
  dimm: Dimm,
  permissions: Permissions,
};

export const UiScene: React.FC<{ scene: MotionScene }> = ({ scene }) => {
  const C = UI_PRESETS[scene.preset ?? ''];
  if (C) return <C scene={scene} />;
  return (
    <UiShell scene={scene}>
      <Win title="Interface">{scene.items?.join(' · ')}</Win>
    </UiShell>
  );
};
