/** Authoring checks without rendering: `node scripts/validate_episodes.mjs` (bundles this file with esbuild). */
import { buildTracks, buildSoundtrack, validateEpisode } from './episode';
import { actionsDemo } from './episodes/actionsDemo';
import { mobsDemo, mobsLine } from './episodes/mobsDemo';

declare const process: { exit(code: number): never };
let bad = 0;
for (const spec of [mobsDemo, mobsLine, actionsDemo]) {
  const tracks = buildTracks(spec);
  const warnings = validateEpisode(spec, tracks);
  const sounds = buildSoundtrack(spec, tracks);
  console.log(`\n[${spec.id}] ${spec.frames} frames (${spec.frames / 30}s), ${spec.shots.length} shots, ${sounds.length} sound events, ${warnings.length} warning(s)`);
  for (const [id, T] of Object.entries(tracks)) {
    const top = Math.max(...T.speed);
    const wet = T.x.map((_, f) => T.swim(f)).map((v, f) => (v > 0.5 ? f : -1)).filter((f) => f >= 0);
    const swimInfo = wet.length ? `, swims frames ${wet[0]}-${wet[wet.length - 1]} (x ${T.x[wet[0]].toFixed(1)}..${T.x[wet[wet.length - 1]].toFixed(1)})` : '';
    console.log(`  ${id}: top speed ${top.toFixed(1)} blocks/s, ${T.steps.length} footsteps, ${T.acts.length} acts, step marks ${T.marks.join(',')}${swimInfo}`);
  }
  warnings.forEach((w) => console.log('  ! ' + w));
  bad += warnings.length;
}
process.exit(bad ? 1 : 0);
