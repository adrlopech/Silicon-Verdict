/** Compiles a script JSON and prints a JSON report (used by services/mc_director.py): `node scripts/mc_compile.mjs script.json`. */
import { compileScript, McScript } from './director';
import { cameraAt } from './camera';
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
let framing: { frames: number; hidden: number; worstRun: number; runs: [number, number, number][] } = { frames: 0, hidden: 0, worstRun: 0, runs: [] }; // frames where the hero is outside the safe part of the picture
if (res.spec) {
  const tracks = buildTracks(res.spec);
  validator = validateEpisode(res.spec, tracks, { collisions: false });
  quality = collisionReport(res.spec, tracks);
  sounds = buildSoundtrack(res.spec, tracks).length;
  beats = res.spec.beats.map((b) => ({ from: b.from, to: b.to, text: b.text }));
  shots = res.spec.shots.length;
  const hero = res.spec.actors.find((a) => a.kind === 'player')?.id;
  if (hero) {
    let run = 0;
    for (let f = 0; f < res.spec.frames; f++) {
      const c = cameraAt(res.spec.shots, tracks, f);
      const T = tracks[hero];
      const fx = c.look[0] - c.pos[0], fz = c.look[2] - c.pos[2], hx = T.x[f] - c.pos[0], hz = T.z[f] - c.pos[2];
      const diff = Math.abs(Math.atan2(fx * hz - fz * hx, fx * hx + fz * hz)); // horizontal angle between where the camera looks and the hero
      const half = Math.atan(Math.tan((c.fov * Math.PI) / 360) * 9 / 16); // half of the horizontal field of view of a 9:16 frame
      const out = diff > half * 0.8;
      framing.frames++;
      if (out) { framing.hidden++; run++; framing.worstRun = Math.max(framing.worstRun, run); if (run === 1) framing.runs.push([f, f, 0]); framing.runs[framing.runs.length - 1][1] = f; framing.runs[framing.runs.length - 1][2] = run; } else run = 0;
    }
    framing.runs = framing.runs.filter((r) => r[2] >= 15);
    if (framing.worstRun > 20) quality.push(`the hero is out of the safe frame for ${framing.worstRun} frames in a row`);
  }
}
process.stdout.write(JSON.stringify({ ok: !!res.spec && !res.errors.length, errors: res.errors, warnings: [...res.warnings, ...validator], quality, frames: res.frames, seconds: res.seconds, shots, sounds, beats, framing }));
process.exit(0);
