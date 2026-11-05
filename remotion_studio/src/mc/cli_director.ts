/** Compiles a script JSON and prints a JSON report (used by services/mc_director.py): `node scripts/mc_compile.mjs script.json`. */
import { compileScript, McScript } from './director';
import { buildTracks, buildSoundtrack, collisionReport, validateEpisode } from './episode';

declare const process: { argv: string[]; stdout: { write(s: string): void }; exit(code: number): never };
declare const require: (m: string) => { readFileSync(p: string, enc: string): string };

const script = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8')) as McScript;
const res = compileScript(script);
let validator: string[] = [];
let quality: string[] = []; // hitbox / camera notes: the director's business, not a script error
let sounds = 0;
let beats: { from: number; to: number; text: string }[] = [];
let shots = 0;
if (res.spec) {
  const tracks = buildTracks(res.spec);
  validator = validateEpisode(res.spec, tracks, { collisions: false });
  quality = collisionReport(res.spec, tracks);
  sounds = buildSoundtrack(res.spec, tracks).length;
  beats = res.spec.beats.map((b) => ({ from: b.from, to: b.to, text: b.text }));
  shots = res.spec.shots.length;
}
process.stdout.write(JSON.stringify({ ok: !!res.spec && !res.errors.length, errors: res.errors, warnings: [...res.warnings, ...validator], quality, frames: res.frames, seconds: res.seconds, shots, sounds, beats }));
process.exit(0);
