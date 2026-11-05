/** Data contract of the MotionGraphic composition. Everything shown on screen comes from these props (no text lives in the code). */
export type SceneType = 'bigText' | 'textWithAccent' | 'counter' | 'list' | 'codeBlock' | 'progressBar' | 'outro' | 'curve' | 'flash';

export interface MotionScene {
  type: SceneType;
  text: string; // main line (bigText: the word(s); counter/progressBar/curve: the caption; list: the heading; codeBlock: the headline under the code)
  accentText?: string; // the accent word shown in colour, italic serif
  kicker?: string; // small tracked-out label above the text
  value?: number; // counter: final number; progressBar: target percentage 0-100
  unit?: string; // counter / progressBar suffix, e.g. "%", "ms"
  items?: string[]; // list: 2-4 short items
  code?: string[]; // codeBlock: up to 8 short lines
  light?: boolean; // light background variant for this scene
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
