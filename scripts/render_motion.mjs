#!/usr/bin/env node
// Renders the MotionGraphic composition from code with @remotion/bundler + @remotion/renderer (bundle -> selectComposition -> renderMedia).
// usage: node scripts/render_motion.mjs <props.json> <out.mp4>
// The props JSON is passed as inputProps. Output: H.264 MP4, 30 fps, ALWAYS 1080x1920 (anything else is an error).
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'remotion_studio');
const require = createRequire(join(root, 'package.json'));
const { bundle } = require('@remotion/bundler');
const { selectComposition, renderMedia } = require('@remotion/renderer');

const [propsPath, outPath] = process.argv.slice(2);
if (!propsPath || !outPath) {
  console.error('usage: node scripts/render_motion.mjs <props.json> <out.mp4>');
  process.exit(2);
}
const inputProps = JSON.parse(readFileSync(propsPath, 'utf8'));
if (!Array.isArray(inputProps.scenes) || !inputProps.scenes.length) throw new Error('props.scenes must be a non-empty array');

const publicDir = mkdtempSync(join(tmpdir(), 'motion-public-')); // empty: the bundle must not copy the 600 MB public/ of the other series
console.log('[motion] bundling...');
const serveUrl = await bundle({ entryPoint: join(root, 'src', 'index.ts'), publicDir, onProgress: (p) => p % 25 === 0 && console.log(`[motion] bundle ${p}%`) });

const composition = await selectComposition({ serveUrl, id: 'MotionGraphic', inputProps });
if (composition.width !== 1080 || composition.height !== 1920) throw new Error(`MotionGraphic must be 1080x1920 (9:16), got ${composition.width}x${composition.height}`);
if (composition.fps !== 30) throw new Error(`MotionGraphic must render at 30 fps, got ${composition.fps}`);
console.log(`[motion] ${composition.durationInFrames} frames (${(composition.durationInFrames / composition.fps).toFixed(1)} s), ${composition.width}x${composition.height}`);

let last = -1;
await renderMedia({
  composition, serveUrl, inputProps, codec: 'h264', pixelFormat: 'yuv420p', crf: 18, outputLocation: resolve(outPath),
  onProgress: ({ progress }) => {
    const pct = Math.floor(progress * 100);
    if (pct % 10 === 0 && pct !== last) { last = pct; console.log(`[motion] render ${pct}%`); }
  },
});
console.log(`[motion] done: ${resolve(outPath)}`);
