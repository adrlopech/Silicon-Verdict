#!/usr/bin/env node
// Compiles a Minecraft video script (JSON) with the kit's director and prints a JSON report.
// usage: node scripts/mc_compile.mjs path/to/script.json
import { build } from '../remotion_studio/node_modules/esbuild/lib/main.js';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';
import { tmpdir } from 'node:os';
import { mkdtempSync } from 'node:fs';
import { spawnSync } from 'node:child_process';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', 'remotion_studio');
const out = join(mkdtempSync(join(tmpdir(), 'mc-compile-')), 'cli.cjs');
await build({ entryPoints: [join(root, 'src/mc/cli_director.ts')], bundle: true, platform: 'node', format: 'cjs', outfile: out, logLevel: 'error', jsx: 'automatic' });
const r = spawnSync('node', [out, process.argv[2]], { encoding: 'utf8' });
process.stdout.write(r.stdout);
process.stderr.write(r.stderr);
process.exit(r.status ?? 1);
