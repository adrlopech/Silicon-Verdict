#!/usr/bin/env node
// Runs the episode validator (choreography + camera + script checks) without rendering.
//   node scripts/validate_episodes.mjs
import { build } from '../remotion_studio/node_modules/esbuild/lib/main.js';
import { fileURLToPath, pathToFileURL } from 'node:url';
import path from 'node:path';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', 'remotion_studio');
const out = path.join(root, 'node_modules', '.cache', 'validate_episodes.mjs');
await build({
  entryPoints: [path.join(root, 'src/mc/cli.ts')],
  outfile: out, bundle: true, platform: 'node', format: 'esm', logLevel: 'error',
  loader: { '.ts': 'ts', '.tsx': 'tsx' }, jsx: 'automatic',
  banner: { js: "import { createRequire } from 'node:module'; const require = createRequire(import.meta.url);" },
});
await import(pathToFileURL(out).href);
