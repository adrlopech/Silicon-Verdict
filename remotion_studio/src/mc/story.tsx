/** Composition for generated videos: `McStory` takes a script (see director.ts) and plays the episode the director compiles from it. */
import React, { useMemo } from 'react';
import { McScript, compileScript } from './director';
import { McEpisode } from './episode';

export const compileMcScript = (script: McScript) => {
  const res = compileScript(script);
  if (!res.spec) throw new Error('Invalid Minecraft script:\n - ' + res.errors.join('\n - '));
  return res;
};

export const McStory: React.FC<{ script: McScript }> = ({ script }) => {
  const res = useMemo(() => compileMcScript(script), [script]);
  return <McEpisode spec={res.spec!} />;
};
