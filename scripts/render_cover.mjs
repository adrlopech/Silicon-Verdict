#!/usr/bin/env node
// Renders the COVER of a Motion video: a still of the cold open (scene 1) once its claim is fully on screen, without subtitles. 1080x1920 PNG.
// usage: node scripts/render_cover.mjs <props.json> <out.png> [publicDir] [frame]
import { createRequire } from 'node:module';
import { fileURLToPath } from 'node:url';
import { dirname, join, resolve } from 'node:path';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'remotion_studio');
const require = createRequire(join(root, 'package.json'));
const { bundle } = require('@remotion/bundler');
const { selectComposition, renderStill } = require('@remotion/renderer');

const [propsPath, outPath, publicArg, frameArg] = process.argv.slice(2);
if (!propsPath || !outPath) {
  console.error('usage: node scripts/render_cover.mjs <props.json> <out.png> [publicDir] [frame]');
  process.exit(2);
}
const inputProps = { ...JSON.parse(readFileSync(propsPath, 'utf8')), captions: [] };
const first = inputProps.scenes[0].durationInFrames;
const frame = Math.max(0, Math.min(frameArg ? Number(frameArg) : 42, first - 2));
const publicDir = publicArg ? resolve(publicArg) : mkdtempSync(join(tmpdir(), 'cover-public-'));
const serveUrl = await bundle({ entryPoint: join(root, 'src', 'index.ts'), publicDir });
const composition = await selectComposition({ serveUrl, id: 'MotionGraphic', inputProps });
await renderStill({ composition, serveUrl, inputProps, frame, output: resolve(outPath), imageFormat: 'png' });
console.log(`[cover] done: ${resolve(outPath)} (frame ${frame})`);
