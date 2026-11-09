import { createContext, useContext } from 'react';
import { JAKARTA, MANROPE, OUTFIT, SANS, SORA, SPACE } from './fonts';
import { MotionScene } from './types';
import { TransitionName } from './transitions';

/**
 * A LOOK is the visual identity of one video: palette, background, headline typeface, alignment, HUD, camera, transitions and caption style.
 * Every look is BLUE: the channel's colour in eight tonalities (cyan, ocean, indigo, cobalt, glass, paper, ice, blueprint), so the channel is recognisable
 * but two videos in a row never look alike. The pipeline picks one per video (services/looks.py) and passes its name in the props.
 */
export type BgStyle = 'glow' | 'aurora' | 'mesh' | 'orbs' | 'dots' | 'blueprint' | 'mono';
export type HudStyle = 'mono' | 'story' | 'brackets' | 'ticks';
export type CameraStyle = 'drift' | 'push' | 'orbit' | 'handheld' | 'still';
export type CaptionStyle = 'pill' | 'plain' | 'underline' | 'mono';
export type ParticleStyle = 'dots' | 'squares' | 'none';
export type DecorStyle = 'none' | 'number' | 'ring' | 'dimension';

export interface Look {
  name: string;
  accent: string;
  accent2: string;
  background: string;
  text: string;
  light: boolean;
  bg: BgStyle;
  floorGrid: boolean; // the perspective grid scrolling at the bottom
  particles: ParticleStyle;
  hud: HudStyle;
  align: 'center' | 'left';
  upper: boolean; // headlines in capitals
  sans: string; // headline typeface
  camera: CameraStyle;
  transitions: TransitionName[];
  captions: CaptionStyle;
  scale: number; // headline size multiplier: bolder looks set the type bigger so the frame is filled
  decor: DecorStyle; // a design element that fills the empty lower part of text scenes
}

export const LOOKS: Record<string, Look> = {
  // deep black-blue with an electric cyan glow: the original channel look
  obsidian: { name: 'obsidian', accent: '#00F0FF', accent2: '#007AFF', background: '#05070C', text: '#FFFFFF', light: false, bg: 'glow', floorGrid: true, particles: 'dots', hud: 'mono', align: 'center', upper: false, sans: SANS, camera: 'drift',
    transitions: ['pushLeft', 'zoomThrough', 'iris', 'glitch', 'pushUp', 'blinds', 'whip', 'flip', 'wipe', 'zoomOut', 'diagonal', 'spin', 'fade'], captions: 'pill', scale: 1.0, decor: 'none' },
  // sky blue over a moving aurora of navy and royal blue
  ocean: { name: 'ocean', accent: '#4DC3FF', accent2: '#0A4DFF', background: '#030B1F', text: '#FFFFFF', light: false, bg: 'aurora', floorGrid: false, particles: 'dots', hud: 'story', align: 'center', upper: false, sans: SPACE, camera: 'push',
    transitions: ['zoomThrough', 'pushUp', 'fade', 'iris', 'zoomOut'], captions: 'plain', scale: 1.04, decor: 'none' },
  // periwinkle and indigo: the bluest end of violet, nothing purple
  indigo: { name: 'indigo', accent: '#8FA8FF', accent2: '#3B3FF0', background: '#060921', text: '#FFFFFF', light: false, bg: 'aurora', floorGrid: false, particles: 'squares', hud: 'ticks', align: 'left', upper: false, sans: SORA, camera: 'orbit',
    transitions: ['whip', 'flip', 'spin', 'diagonal', 'pushLeft'], captions: 'underline', scale: 1.1, decor: 'ring' },
  // modern and bold: a saturated cobalt gradient mesh with soft light blobs and film grain, big rounded type
  cobalt: { name: 'cobalt', accent: '#9BE8FF', accent2: '#4C8DFF', background: '#061552', text: '#FFFFFF', light: false, bg: 'mesh', floorGrid: false, particles: 'squares', hud: 'brackets', align: 'left', upper: false, sans: OUTFIT, camera: 'handheld',
    transitions: ['whip', 'diagonal', 'zoomThrough', 'pushLeft', 'blinds'], captions: 'pill', scale: 1.2, decor: 'number' },
  // modern and calm: frosted glass spheres drifting over midnight blue
  glass: { name: 'glass', accent: '#7CC8FF', accent2: '#4A6BFF', background: '#040A1C', text: '#FFFFFF', light: false, bg: 'orbs', floorGrid: false, particles: 'dots', hud: 'story', align: 'center', upper: false, sans: JAKARTA, camera: 'drift',
    transitions: ['fade', 'zoomOut', 'iris', 'pushUp', 'zoomThrough'], captions: 'plain', scale: 1.06, decor: 'none' },
  // a light look: blue ink on a pale blue sheet
  paper: { name: 'paper', accent: '#0A5CFF', accent2: '#00B3FF', background: '#EAF2FF', text: '#0A1220', light: true, bg: 'dots', floorGrid: false, particles: 'none', hud: 'story', align: 'left', upper: false, sans: MANROPE, camera: 'still',
    transitions: ['fade', 'pushLeft', 'wipe', 'zoomOut', 'pushUp'], captions: 'pill', scale: 1.12, decor: 'number' },
  // blue-tinted monochrome: icy white on deep blue-black
  ice: { name: 'ice', accent: '#E4F1FF', accent2: '#7FA6D6', background: '#050B16', text: '#F2F8FF', light: false, bg: 'mono', floorGrid: false, particles: 'none', hud: 'mono', align: 'center', upper: false, sans: SANS, camera: 'still',
    transitions: ['fade', 'wipe', 'pushLeft', 'iris'], captions: 'plain', scale: 1.0, decor: 'none' },
  // a technical drawing: white lines on blueprint blue
  blueprint: { name: 'blueprint', accent: '#A6DCFF', accent2: '#2F6BFF', background: '#0A2A66', text: '#FFFFFF', light: false, bg: 'blueprint', floorGrid: false, particles: 'none', hud: 'ticks', align: 'left', upper: true, sans: SPACE, camera: 'drift',
    transitions: ['wipe', 'blinds', 'pushLeft', 'diagonal', 'fade'], captions: 'mono', scale: 1.06, decor: 'dimension' },
};

export const LOOK_NAMES = Object.keys(LOOKS);
export const lookFor = (name?: string): Look => LOOKS[name ?? ''] ?? LOOKS.obsidian;

export const LookCtx = createContext<Look>(LOOKS.obsidian);
export const useLook = () => useContext(LookCtx);

/** The scene being drawn (for the cues the pipeline sets on it) and how much room the caption strip takes from its bottom. */
export const SceneCtx = createContext<{ scene: MotionScene | null; captionSpace: number }>({ scene: null, captionSpace: 0 });
export const useSceneCtx = () => useContext(SceneCtx);

/** Scenes that are built to fill the frame: no caption strip over them. */
export const NO_CAPTION = new Set(['tier', 'ui', 'footage', 'flash']);
export const CAPTION_SPACE = 170;
