/** Minecraft video kit — post: projectLUMA final pass (Uncharted 2 tonemapping + saturation), soft bloom and vignette. */
import React, { useMemo } from 'react';
import * as THREE from 'three';
import { Bloom, DepthOfField, EffectComposer, Vignette } from '@react-three/postprocessing';
import { Effect } from 'postprocessing';

const U2_FRAG = `
uniform float exposure;
uniform float saturation;
vec3 u2(vec3 x){
  const float A=0.2, B=0.40, C=0.10, D=0.60, E=0.022, F=0.30;
  return ((x*(A*x+C*B)+D*E)/(x*(A*x+B)+D*F))-E/F;
}
void mainImage(const in vec4 inputColor, const in vec2 uv, out vec4 outputColor){
  vec3 c = inputColor.rgb;
  c = mix(c, vec3(dot(c, vec3(0.3333))), -saturation*1.1+1.0);
  c = u2(c*8.0*exposure) / u2(vec3(9.8));
  outputColor = vec4(c, inputColor.a);
}`;
class LumaTonemap extends Effect {
  constructor(exposure = 1.0, saturation = 1.15) {
    super('LumaTonemap', U2_FRAG, { uniforms: new Map<string, THREE.Uniform>([['exposure', new THREE.Uniform(exposure)], ['saturation', new THREE.Uniform(saturation)]]) });
  }
}
/** `focus` = world distance from the camera to the subject; `bokeh` = blur strength (0 disables depth of field, like the animated trailers use ~2). */
export const Post: React.FC<{ focus?: number; bokeh?: number }> = ({ focus = 8, bokeh = 0 }) => {
  const tone = useMemo(() => new LumaTonemap(0.8, 1.08), []);
  return (
    <EffectComposer multisampling={0}>
      {bokeh > 0 ? <DepthOfField worldFocusDistance={focus} worldFocusRange={Math.max(2.2, focus * 0.5)} bokehScale={bokeh} /> : <></>}
      <Bloom intensity={0.2} luminanceThreshold={0.9} luminanceSmoothing={0.2} mipmapBlur />
      <primitive object={tone} />
      <Vignette eskil={false} offset={0.25} darkness={0.5} />
    </EffectComposer>
  );
};
