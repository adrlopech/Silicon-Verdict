import { createContext, useContext } from 'react';
import { JAKARTA, LEXEND, MANROPE, OUTFIT, SANS, SORA, SPACE, SYNE, URBANIST } from './fonts';
import { MotionScene } from './types';
import { TransitionName } from './transitions';
import type { Reveal } from './anim';

/**
 * A LOOK is the visual identity of one video: palette, background, headline typeface, alignment, HUD, camera, transitions and caption style.
 * Every look is BLUE: the channel's colour in eight tonalities (cyan, ocean, indigo, cobalt, glass, paper, ice, blueprint), so the channel is recognisable
 * but two videos in a row never look alike. The pipeline picks one per video (services/looks.py) and passes its name in the props.
 */
export type BgStyle = 'glow' | 'aurora' | 'mesh' | 'orbs' | 'dots' | 'blueprint' | 'mono' | 'stripes' | 'bokeh' | 'circuit' | 'waves' | 'spotlight' | 'rain';
export type HudStyle = 'mono' | 'story' | 'brackets' | 'ticks';
export type CameraStyle = 'drift' | 'push' | 'orbit' | 'handheld' | 'still';
export type CaptionStyle = 'pill' | 'plain' | 'underline' | 'mono' | 'oneword' | 'twotone' | 'wordpill' | 'karaoke' | 'box' | 'bounce';
export type ParticleStyle = 'dots' | 'squares' | 'none';
export type DecorStyle = 'none' | 'number' | 'ring' | 'dimension' | 'bars' | 'arcs';

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
    transitions: ['zoomThrough', 'pushUp', 'fade', 'iris', 'zoomOut'], captions: 'wordpill', scale: 1.04, decor: 'none' },
  // periwinkle and indigo: the bluest end of violet, nothing purple
  indigo: { name: 'indigo', accent: '#8FA8FF', accent2: '#3B3FF0', background: '#060921', text: '#FFFFFF', light: false, bg: 'aurora', floorGrid: false, particles: 'squares', hud: 'ticks', align: 'left', upper: false, sans: SORA, camera: 'orbit',
    transitions: ['whip', 'flip', 'spin', 'diagonal', 'pushLeft'], captions: 'underline', scale: 1.1, decor: 'ring' },
  // modern and bold: a saturated cobalt gradient mesh with soft light blobs and film grain, big rounded type
  cobalt: { name: 'cobalt', accent: '#9BE8FF', accent2: '#4C8DFF', background: '#061552', text: '#FFFFFF', light: false, bg: 'mesh', floorGrid: false, particles: 'squares', hud: 'brackets', align: 'left', upper: false, sans: OUTFIT, camera: 'handheld',
    transitions: ['whip', 'diagonal', 'zoomThrough', 'pushLeft', 'blinds'], captions: 'oneword', scale: 1.2, decor: 'number' },
  // modern and calm: frosted glass spheres drifting over midnight blue
  glass: { name: 'glass', accent: '#7CC8FF', accent2: '#4A6BFF', background: '#040A1C', text: '#FFFFFF', light: false, bg: 'orbs', floorGrid: false, particles: 'dots', hud: 'story', align: 'center', upper: false, sans: JAKARTA, camera: 'drift',
    transitions: ['fade', 'zoomOut', 'iris', 'pushUp', 'zoomThrough'], captions: 'twotone', scale: 1.06, decor: 'none' },
  // a light look: blue ink on a pale blue sheet
  paper: { name: 'paper', accent: '#0A5CFF', accent2: '#00B3FF', background: '#EAF2FF', text: '#0A1220', light: true, bg: 'dots', floorGrid: false, particles: 'none', hud: 'story', align: 'left', upper: false, sans: MANROPE, camera: 'still',
    transitions: ['fade', 'pushLeft', 'wipe', 'zoomOut', 'pushUp'], captions: 'pill', scale: 1.12, decor: 'number' },
  // blue-tinted monochrome: icy white on deep blue-black
  ice: { name: 'ice', accent: '#E4F1FF', accent2: '#7FA6D6', background: '#050B16', text: '#F2F8FF', light: false, bg: 'mono', floorGrid: false, particles: 'none', hud: 'mono', align: 'center', upper: false, sans: SANS, camera: 'still',
    transitions: ['fade', 'wipe', 'pushLeft', 'iris'], captions: 'plain', scale: 1.0, decor: 'none' },
  // a technical drawing: white lines on blueprint blue
  blueprint: { name: 'blueprint', accent: '#A6DCFF', accent2: '#2F6BFF', background: '#0A2A66', text: '#FFFFFF', light: false, bg: 'blueprint', floorGrid: false, particles: 'none', hud: 'ticks', align: 'left', upper: true, sans: SPACE, camera: 'drift',
    transitions: ['wipe', 'blinds', 'pushLeft', 'diagonal', 'fade'], captions: 'mono', scale: 1.06, decor: 'dimension' },
  // NEW (Nov 2026): six more blues, each with its own background, typeface, caption style and decor
  // neon sign: diagonal light stripes sweeping over near-black blue, capitals
  neon: { name: 'neon', accent: '#5CF2FF', accent2: '#1E6BFF', background: '#04060F', text: '#FFFFFF', light: false, bg: 'stripes', floorGrid: false, particles: 'squares', hud: 'brackets', align: 'center', upper: true, sans: LEXEND, camera: 'handheld',
    transitions: ['whip', 'pushDown', 'shutter', 'glitch', 'diagonal', 'cornerIris'], captions: 'bounce', scale: 1.08, decor: 'bars' },
  // midnight bokeh: out-of-focus lights drifting, soft and cinematic
  midnight: { name: 'midnight', accent: '#9CC4FF', accent2: '#2B5BFF', background: '#030617', text: '#FFFFFF', light: false, bg: 'bokeh', floorGrid: false, particles: 'dots', hud: 'story', align: 'left', upper: false, sans: URBANIST, camera: 'push',
    transitions: ['fade', 'curtain', 'zoomOut', 'cornerIris', 'pushDown'], captions: 'karaoke', scale: 1.1, decor: 'arcs' },
  // steel circuit board: traces and travelling pulses on gunmetal blue
  steel: { name: 'steel', accent: '#6FB7FF', accent2: '#3A5F8F', background: '#07101C', text: '#F2F8FF', light: false, bg: 'circuit', floorGrid: false, particles: 'none', hud: 'ticks', align: 'left', upper: true, sans: SYNE, camera: 'drift',
    transitions: ['shutter', 'wipe', 'pushLeft', 'curtain', 'blinds'], captions: 'box', scale: 1.04, decor: 'bars' },
  // electric: rolling waves of saturated blue light
  electric: { name: 'electric', accent: '#2DA8FF', accent2: '#0B3BFF', background: '#02061E', text: '#FFFFFF', light: false, bg: 'waves', floorGrid: false, particles: 'dots', hud: 'mono', align: 'center', upper: false, sans: OUTFIT, camera: 'orbit',
    transitions: ['zoomThrough', 'curtain', 'spin', 'pushDown', 'iris', 'whip'], captions: 'wordpill', scale: 1.12, decor: 'arcs' },
  // frost: a cold spotlight cone from above on dark slate blue
  frost: { name: 'frost', accent: '#BFE3FF', accent2: '#5C8DE8', background: '#0A1426', text: '#F4F9FF', light: false, bg: 'spotlight', floorGrid: false, particles: 'none', hud: 'brackets', align: 'center', upper: false, sans: JAKARTA, camera: 'still',
    transitions: ['fade', 'curtain', 'iris', 'cornerIris', 'zoomOut'], captions: 'box', scale: 1.06, decor: 'none' },
  // deep sea: vertical streaks of cyan light falling through dark water
  deepsea: { name: 'deepsea', accent: '#35D0FF', accent2: '#0A5AA8', background: '#021426', text: '#FFFFFF', light: false, bg: 'rain', floorGrid: false, particles: 'dots', hud: 'mono', align: 'left', upper: false, sans: SPACE, camera: 'push',
    transitions: ['pushUp', 'shutter', 'zoomThrough', 'pushDown', 'glitch'], captions: 'karaoke', scale: 1.08, decor: 'bars' },
};

export const LOOK_NAMES = Object.keys(LOOKS);
export const lookFor = (name?: string): Look => LOOKS[name ?? ''] ?? LOOKS.obsidian;

export const LookCtx = createContext<Look>(LOOKS.obsidian);
export const useLook = () => useContext(LookCtx);

/** The scene being drawn (for the cues the pipeline sets on it) and how much room the caption strip takes from its bottom. */
export const SceneCtx = createContext<{ scene: MotionScene | null; captionSpace: number; reveal?: Reveal }>({ scene: null, captionSpace: 0 });
export const useSceneCtx = () => useContext(SceneCtx);

/** Scenes that are built to fill the frame: no caption strip over them. */
export const NO_CAPTION = new Set(['tier', 'ui', 'footage', 'flash']);
export const CAPTION_SPACE = 170;
/** The caption strip sits this many px lower than the bottom of the scene's content area, so a caption never touches a text or an object (the scene is also faded out above it). */
export const CAPTION_DROP = 56;
