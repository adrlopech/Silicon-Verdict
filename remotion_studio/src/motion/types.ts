/** Data contract of the MotionGraphic composition. Everything shown on screen comes from these props (no text lives in the code). */
export type SceneType = 'bigText' | 'textWithAccent' | 'counter' | 'list' | 'codeBlock' | 'progressBar' | 'outro' | 'curve' | 'flash' | 'footage' | 'tier' | 'versus' | 'verdict' | 'timeline';

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
  narration?: string; // spoken line (used by the pipeline for the voice; not drawn)
  durationInFrames: number;
}

export interface MotionTheme {
  accent: string;
  background: string;
  text: string;
}

export interface MotionGraphicProps {
  title: string;
  scenes: MotionScene[];
  theme: MotionTheme;
}

export const FPS = 30;
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
