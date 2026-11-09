import { loadFont as loadInter } from '@remotion/google-fonts/Inter';
import { loadFont as loadSerif } from '@remotion/google-fonts/InstrumentSerif';
import { loadFont as loadMono } from '@remotion/google-fonts/JetBrainsMono';

// Google Fonts only (no external assets). Loaded once; Remotion waits for them before rendering a frame.
export const SANS = loadInter('normal', { weights: ['500', '800', '900'], subsets: ['latin'] }).fontFamily;
export const SERIF = loadSerif('italic', { weights: ['400'], subsets: ['latin'] }).fontFamily;
export const MONO = loadMono('normal', { weights: ['400', '500'], subsets: ['latin'] }).fontFamily;

// Display faces that give each look its own voice (still Google Fonts only).
import { loadFont as loadSpace } from '@remotion/google-fonts/SpaceGrotesk';
import { loadFont as loadSora } from '@remotion/google-fonts/Sora';
import { loadFont as loadOutfit } from '@remotion/google-fonts/Outfit';
import { loadFont as loadJakarta } from '@remotion/google-fonts/PlusJakartaSans';
import { loadFont as loadManrope } from '@remotion/google-fonts/Manrope';

export const SPACE = loadSpace('normal', { weights: ['500', '700'], subsets: ['latin'] }).fontFamily;
export const SORA = loadSora('normal', { weights: ['600', '800'], subsets: ['latin'] }).fontFamily;
export const OUTFIT = loadOutfit('normal', { weights: ['600', '800'], subsets: ['latin'] }).fontFamily;
export const JAKARTA = loadJakarta('normal', { weights: ['600', '800'], subsets: ['latin'] }).fontFamily;
export const MANROPE = loadManrope('normal', { weights: ['500', '800'], subsets: ['latin'] }).fontFamily;
