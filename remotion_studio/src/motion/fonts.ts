import { loadFont as loadInter } from '@remotion/google-fonts/Inter';
import { loadFont as loadSerif } from '@remotion/google-fonts/InstrumentSerif';
import { loadFont as loadMono } from '@remotion/google-fonts/JetBrainsMono';

// Google Fonts only (no external assets). Loaded once; Remotion waits for them before rendering a frame.
export const SANS = loadInter('normal', { weights: ['500', '800', '900'], subsets: ['latin'] }).fontFamily;
export const SERIF = loadSerif('italic', { weights: ['400'], subsets: ['latin'] }).fontFamily;
export const MONO = loadMono('normal', { weights: ['400', '500'], subsets: ['latin'] }).fontFamily;
