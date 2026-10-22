import * as THREE from 'three';

// Port of Custom expressions in NativeFinal/Materials/M_NexoMateo_Uniform and
// M_NexoMateo_StylizedFace. Use pre-skin coordinates, as in Unreal, so lines follow
// the body instead of sliding across the surface during the idle animation.
const uniform = `
float nexoStroke(float d,float inner,float outer){return 1.0-smoothstep(inner,max(outer,fwidth(d)*.75),d);}
float nexoLines(vec3 P) {
  float front=smoothstep(1.0,4.0,P.y);
  float torso=smoothstep(110.0,114.0,P.z)*(1.0-smoothstep(159.0,164.0,P.z))*(1.0-smoothstep(17.0,22.0,abs(P.x)))*front;
  float path=11.5+3.0*smoothstep(140.0,158.0,P.z);
  float seam=nexoStroke(abs(abs(P.x)-path),.07,.17);
  float parallel=nexoStroke(abs(abs(P.x)-path-.85),.03,.11)*smoothstep(142.0,144.0,P.z);
  vec2 q=vec2(P.x+7.2,P.z-150.5);
  float hex=1.0-smoothstep(.06,.15,abs(max(abs(q.y),abs(q.x)*.866025+abs(q.y)*.5)-2.0));
  float inner=(1.0-smoothstep(.045,.12,min(abs(q.x),min(abs(q.y-.57735*q.x),abs(q.y+.57735*q.x)))))*(1.0-smoothstep(1.0,1.15,length(q)));
  float zip=nexoStroke(abs(P.x),.025,.075)*.22;
  return clamp((seam*.58+parallel*.28+zip+hex*.85+inner*.65)*torso,0.0,1.0);
}
vec3 nexoCloth(vec3 P) {
  float side=smoothstep(12.0,19.0,abs(P.x));
  vec3 fabric=mix(vec3(.012,.035,.078),vec3(.005,.014,.034),side);
  fabric=mix(fabric,vec3(.004,.009,.021),1.0-smoothstep(97.0,99.0,P.z));
  return mix(fabric,vec3(.025,.49,.63),nexoLines(P));
}`;

const face = `
float nexoSegment(vec2 p,vec2 a,vec2 b){vec2 v=b-a;return length(p-a-v*clamp(dot(p-a,v)/dot(v,v),0.0,1.0));}
float nexoLines(vec3 P) {
  vec2 q=vec2(abs(P.x),P.z);
  float d=min(nexoSegment(q,vec2(7.3,181.0),vec2(6.8,178.0)),min(nexoSegment(q,vec2(6.8,178.0),vec2(5.1,175.5)),nexoSegment(q,vec2(5.1,175.5),vec2(5.6,172.5))));
  return (1.0-smoothstep(.035,max(.105,fwidth(d)),d))*smoothstep(1.0,4.0,P.y);
}`;

export function applyNexoMaterials(root: THREE.Object3D) {
  root.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return;
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
      if (!(material instanceof THREE.MeshStandardMaterial)) continue;
      if (material.name === 'MI_Body_Baked_VT_Body') {
        material.metalness = 0;
        material.roughness = 1;
        material.roughnessMap = null;
        material.envMapIntensity = 0;
        material.onBeforeCompile = (shader) => {
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <lights_fragment_end>',
            '#include <lights_fragment_end>\nreflectedLight.directSpecular *= .12; reflectedLight.indirectSpecular *= .12;'
          );
        };
        material.customProgramCacheKey = () => 'nexo-body-matte-v1';
        material.needsUpdate = true;
      }
      if (material.name === 'MI_NexoMateo_ClassicHair') {
        // glTF's metallic/roughness bake cannot reproduce the original hair shader.
        material.metalness = 0;
        material.alphaToCoverage = true;
        material.alphaTest = 0.25;
        material.onBeforeCompile = (shader) => {
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <roughnessmap_fragment>',
            '#include <roughnessmap_fragment>\nroughnessFactor = max(roughnessFactor, .72);'
          );
        };
        material.customProgramCacheKey = () => 'nexo-classic-hair-matte-v1';
        material.needsUpdate = true;
      }
      const isUniform = material.name === 'M_NexoMateo_Uniform';
      const isFace =
        material.name === 'M_NexoMateo_StylizedFace' ||
        material.userData.vivaMaterial === 'nexo-native-face-v2';
      if (!isUniform && !isFace) continue;
      const positions = node.geometry.getAttribute('position');
      const reference = new Float32Array(positions.count * 3);
      for (let i = 0; i < positions.count; i++) {
        reference[i * 3] = positions.getX(i) * 100;
        reference[i * 3 + 1] = positions.getZ(i) * 100;
        reference[i * 3 + 2] = positions.getY(i) * 100;
      }
      node.geometry.setAttribute('nexoReferenceCm', new THREE.BufferAttribute(reference, 3));
      material.roughness = isUniform ? 0.85 : 0.8;
      material.metalness = 0;
      if (isFace) {
        material.roughness = 1;
        material.roughnessMap = null;
        material.envMapIntensity = 0;
        material.normalScale.set(0.35, 0.35);
        material.aoMapIntensity = 0;
      }
      material.onBeforeCompile = (shader) => {
        shader.vertexShader =
          'attribute vec3 nexoReferenceCm; varying vec3 vNexoReferenceCm;\n' + shader.vertexShader;
        shader.vertexShader = shader.vertexShader.replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\nvNexoReferenceCm = nexoReferenceCm;'
        );
        shader.fragmentShader = 'varying vec3 vNexoReferenceCm;\n' + shader.fragmentShader;
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <common>',
          '#include <common>\n' + (isUniform ? uniform : face)
        );
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <color_fragment>',
          '#include <color_fragment>\n' +
            (isUniform
              ? 'diffuseColor.rgb = nexoCloth(vNexoReferenceCm);'
              : 'diffuseColor.rgb = mix(diffuseColor.rgb, vec3(.025,.49,.63), nexoLines(vNexoReferenceCm));')
        );
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <emissivemap_fragment>',
          '#include <emissivemap_fragment>\ntotalEmissiveRadiance += vec3(.025,.49,.63) * nexoLines(vNexoReferenceCm) * .35;'
        );
        if (isFace) {
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <roughnessmap_fragment>',
            '#include <roughnessmap_fragment>\nroughnessFactor=1.0;'
          );
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <lights_fragment_end>',
            '#include <lights_fragment_end>\nreflectedLight.directSpecular *= .12; reflectedLight.indirectSpecular *= .12;'
          );
        }
      };
      material.customProgramCacheKey = () =>
        isUniform ? 'nexo-native-uniform-v1' : 'nexo-native-face-matte-v3';
      material.needsUpdate = true;
    }
  });
}
