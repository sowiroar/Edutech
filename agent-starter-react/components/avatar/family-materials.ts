import * as THREE from 'three';
import { familySurface } from './family-surface-shaders';

// Original pre-skinned masks and surface brows from the retained NOA/NOVA
// materials. Virtual texture bakes cannot carry these position-based effects.
export function applyFamilyMaterials(root: THREE.Object3D, character: string) {
  if (!['NOA', 'NOVA', 'ATLAS'].includes(character)) return;
  root.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return;
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
      if (!(material instanceof THREE.MeshStandardMaterial)) continue;
      const isFace =
        material.userData.vivaMaterial === `${character.toLowerCase()}-original-skin-v1`;
      const isUniform = ['M_NOA_Uniform', 'M_Nova_Uniform', 'M_Atlas_Uniform'].includes(
        material.name
      );
      const isSleeves = material.name === 'M_NOA_Sleeves';
      if (material.name.toLowerCase().includes('hair')) {
        material.metalness = 0;
        material.roughness = Math.max(material.roughness, 0.68);
        material.alphaToCoverage = true;
        material.onBeforeCompile = (shader) => {
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <roughnessmap_fragment>',
            '#include <roughnessmap_fragment>\nroughnessFactor=max(roughnessFactor,.68);'
          );
        };
        material.customProgramCacheKey = () => `${character}-hair-matte-v1`;
        material.needsUpdate = true;
      }
      if (!isFace && !isUniform && !isSleeves) continue;
      if (isUniform) {
        material.map?.dispose();
        material.normalMap?.dispose();
        material.map = null;
        material.normalMap = null;
        material.metalness = 0;
        material.roughness = 0.85;
      }
      const positions = node.geometry.getAttribute('position');
      const reference = new Float32Array(positions.count * 3);
      for (let i = 0; i < positions.count; i++) {
        reference[i * 3] = positions.getX(i) * 100;
        reference[i * 3 + 1] = positions.getZ(i) * 100;
        reference[i * 3 + 2] = positions.getY(i) * 100;
      }
      node.geometry.setAttribute('familyReferenceCm', new THREE.BufferAttribute(reference, 3));
      material.onBeforeCompile = (shader) => {
        shader.vertexShader =
          'attribute vec3 familyReferenceCm; varying vec3 vFamilyP;\n' + shader.vertexShader;
        shader.vertexShader = shader.vertexShader.replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\nvFamilyP=familyReferenceCm;'
        );
        shader.fragmentShader = 'varying vec3 vFamilyP;\n' + shader.fragmentShader;
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <common>',
          '#include <common>\n' + familySurface
        );
        if (isFace && character !== 'ATLAS') {
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <alphatest_fragment>',
            '#include <alphatest_fragment>\nif(vFamilyP.z<151.5) discard;'
          );
          if (character === 'NOA') {
            shader.fragmentShader = shader.fragmentShader.replace(
              '#include <alphatest_fragment>',
              '#include <alphatest_fragment>\nif(vFamilyP.z<155.0 && abs(vFamilyP.x)>.55) discard;'
            );
          }
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <color_fragment>',
            `#include <color_fragment>
          float t=clamp((abs(vFamilyP.x)-1.5)/4.8,0.,1.);
          float z=${character === 'NOA' ? '170.35' : '169.8'}+.50*sin(t*3.14159)-.42*t;
          float width=mix(.30,.09,t);
          float edge=smoothstep(1.3,1.8,abs(vFamilyP.x))*(1.-smoothstep(5.8,6.4,abs(vFamilyP.x)));
          float ink=(1.-smoothstep(width*.4,width,abs(vFamilyP.z-z)))*edge*smoothstep(5.,8.,vFamilyP.y);
          float fibre=.72+.28*sin(abs(vFamilyP.x)*85.-vFamilyP.z*55.);
          diffuseColor.rgb=mix(diffuseColor.rgb,${character === 'NOA' ? 'vec3(.035,.019,.012)' : 'vec3(.043,.021,.011)'},ink*fibre*.9);
          diffuseColor.rgb=mix(diffuseColor.rgb,${character === 'NOA' ? 'vec3(.023,.658,.584)' : 'vec3(.62,.36,.085)'},familyTraces(vFamilyP));`
          );
        }
        if (isUniform || isSleeves || (isFace && character === 'ATLAS')) {
          const effect = isUniform
            ? `diffuseColor.rgb=${character.toLowerCase()}Cloth(vFamilyP);`
            : isSleeves
              ? 'diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.005,.014,.022),noaSleeves(vFamilyP).x);'
              : 'diffuseColor.rgb=atlasSkin(vFamilyP,diffuseColor.rgb); vec2 q=vec2(abs(vFamilyP.x),vFamilyP.z); float d=min(familySegment(q,vec2(7.3,181.),vec2(6.8,178.)),min(familySegment(q,vec2(6.8,178.),vec2(5.1,175.5)),familySegment(q,vec2(5.1,175.5),vec2(5.6,172.5)))); diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.08,.48,.25),(1.-smoothstep(.035,.105,d))*smoothstep(1.,4.,vFamilyP.y));';
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <color_fragment>',
            '#include <color_fragment>\n' + effect
          );
        }
      };
      material.customProgramCacheKey = () =>
        `${character.toLowerCase()}-${material.name}-surface-v2`;
      material.needsUpdate = true;
    }
  });
}
