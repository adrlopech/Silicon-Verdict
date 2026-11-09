/** Data contract of the MotionGraphic composition. Everything shown on screen comes from these props (no text lives in the code). */
export type SceneType = 'bigText' | 'textWithAccent' | 'counter' | 'list' | 'codeBlock' | 'progressBar' | 'outro' | 'curve' | 'flash' | 'footage' | 'tier' | 'versus' | 'verdict' | 'timeline' | 'ui';

export type SceneFx = 'plane' | 'rocket' | 'satellite' | 'waves' | 'bolts' | 'embers' | 'snow' | 'drops' | 'packets' | 'coins' | 'equalizer' | 'signalbars' | 'notifications' | 'batteryfill' | 'clock' | 'padlock' | 'magnify' | 'bits';
export type ToggleKey = 'airplane' | 'wifi' | 'bluetooth' | 'airdrop';
export type CursorAction = 'click' | 'select' | 'drag' | 'toggle';

export interface MotionScene {
  type: SceneType;
  text: string; // main line (bigText: the word(s); counter/progressBar/curve: the caption; list: the heading; codeBlock: the headline under the code)
  accentText?: string; // the accent word shown in colour, italic serif
  kicker?: string; // small tracked-out label above the text
  value?: number; // counter: final number; progressBar: target percentage 0-100
  unit?: string; // counter / progressBar suffix, e.g. "%", "ms"
  items?: string[]; // list: 2-4 short items; tier: up to 10 "S|label" entries (S A B C D F); timeline: up to 5 "year|label" entries
  left?: string; // versus: name of the left contender
  right?: string; // versus: name of the right contender
  leftValue?: number; // versus: the left contender's figure for this scene's metric
  rightValue?: number; // versus: the right contender's figure
  winner?: 'left' | 'right' | 'none'; // versus: who wins (default: the bigger value; set it for lower-is-better metrics)
  verdict?: 'myth' | 'fact' | 'partly'; // verdict: the stamp
  code?: string[]; // codeBlock: up to 8 short lines
  light?: boolean; // light background variant for this scene
  mediaSrc?: string; // footage: path inside the render's public dir, e.g. games/skyrim_00.jpg or games/clip.mp4
  mediaKind?: 'image' | 'video'; // footage: how to play mediaSrc
  mediaSeconds?: number; // footage: clip length (video loops if the scene lasts longer)
  credit?: string; // footage: game name shown as a tag
  icons?: string[]; // 1-4 thematic objects floating around the text (names from props.tsx ICONS); picked from the scene's words when empty
  fx?: SceneFx; // an animated element related to what the scene says (a plane flying across, signal waves, lightning...); picked from the scene's words when empty
  toggle?: ToggleKey; // with cursor 'toggle': which switch of the Control Center panel the cursor flips (airplane mode switches the radios off)
  cursor?: CursorAction; // the pointer acts in this scene only when the action means something: select (highlights the key phrase as it is spoken), drag (pulls a progress bar, drops the new tier chip), click (presses a step or a setting: code and list scenes), toggle (flips a Control Center switch)
  preset?: string; // ui scenes: which drawn interface (display, taskmgr, bios, terminal, gpupanel, gamemenu, frametime, speedtest, wifilist, router, keycaps, filemgr, diskbar, battery, tabmem, speclabel, leaderboard, partpicker, dimm, permissions); its data lives in text / items / value / accentText / leftValue / rightValue / code
  accentCue?: number; // seconds after the scene starts at which the narrator says the accent phrase: it pulses then (set by the pipeline from the voice timing)
  cursorCue?: number; // seconds after the scene starts at which the narrator says the phrase the pointer acts on (set by the pipeline from the voice timing; the pointer arrives then)
  transition?: string; // how this scene enters (see transitions.ts); varied automatically when empty
  narration?: string; // spoken line (used by the pipeline for the voice; not drawn)
  durationInFrames: number;
}

export interface MotionTheme {
  accent: string;
  accent2?: string; // the second colour of the look (glows, gradients, secondary bars); the channel blue when empty
  background: string;
  text: string;
}

export interface CaptionWord {
  w: string; // the spoken word
  s: number; // first frame of the word in the whole video
  e: number; // last frame
}

export interface MotionGraphicProps {
  title: string;
  look?: string; // the visual look of the whole video (see looks.ts); obsidian when empty
  captions?: CaptionWord[]; // word timing of the narration for the caption strip (set by the pipeline)
  scenes: MotionScene[];
  theme: MotionTheme;
}

export const FPS = 30;
/** Frames of a tier scene at which the pointer grabs the new chip and drops it in its row (shared by the scene, which moves the chip, and the pointer, which holds it). */
export const TIER_GRAB = 14;
export const TIER_DROP = 46;
export const WIDTH = 1080;
export const HEIGHT = 1920;
/** Shorts / TikTok overlay the app UI on the top ~12% and the bottom ~20%: nothing important may live there. */
export const SAFE_TOP = Math.round(HEIGHT * 0.12);
export const SAFE_BOTTOM = Math.round(HEIGHT * 0.2);
export const SAFE_HEIGHT = HEIGHT - SAFE_TOP - SAFE_BOTTOM;
export const OVERLAP = 12; // frames a scene stays under the next one while they cross-fade

/** Silicon Verdict palette: electric cyan on obsidian, with the channel blue for depth. */
export const BRAND_CYAN = '#00F0FF';
export const BRAND_BLUE = '#007AFF';
export const defaultTheme: MotionTheme = { accent: BRAND_CYAN, background: '#05070C', text: '#FFFFFF' };

/** Timing of the one thing a `ui` scene does (the pointer grabs / presses at `grab`, the change is complete at `done`). Shared by the preset, which animates the change,
 *  and by the pointer, which reaches its target by `grab` (when the narrator says it, if the voice timing is known). */
export const uiAct = (scene: MotionScene): { grab: number; done: number } => {
  const dur = scene.durationInFrames;
  const cue = scene.cursorCue != null ? Math.round(scene.cursorCue * FPS) : null;
  const grab = cue != null ? Math.max(28, Math.min(dur - 70, cue - 2)) : Math.max(28, Math.min(46, Math.round(dur * 0.3)));
  return { grab, done: grab + 32 };
};
