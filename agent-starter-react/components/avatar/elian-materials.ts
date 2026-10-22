import * as THREE from 'three';

// Original Elian Custom material and decal from /Game/VIVA/Avatars/Elian.
// They are evaluated before skinning, not approximated with another character's dye.
const uniform = `
vec3 elianCloth(vec3 P) {
  vec2 p=P.xz-vec2(0.0,4.4);
  float front=smoothstep(1.5,4.0,P.y);
  float torso=(1.0-smoothstep(17.0,20.0,abs(p.x)))*smoothstep(108.0,112.0,p.y)*(1.0-smoothstep(143.0,148.0,p.y))*front;
  float center=1.0-smoothstep(.04,max(.09,fwidth(p.x)),abs(p.x));
  float edgeD=abs(abs(p.x)-(11.5+2.0*smoothstep(132.0,147.0,p.y)));
  float edge=1.0-smoothstep(.045,max(.1,fwidth(edgeD)),edgeD);
  vec2 q=(p-vec2(-7.0,136.0))/2.2;
  vec2 h=vec2(abs(q.x)*.55,q.y*.55+.45);
  float d;
  if(h.y+h.x>1.0) d=length(h-vec2(.25,.75))-.353553;
  else {vec2 a=h-vec2(0.0,1.0);vec2 b=h-.5*max(h.x+h.y,0.0);d=sqrt(min(dot(a,a),dot(b,b)))*sign(h.x-h.y);}
  float heart=1.0-smoothstep(.018,.034,abs(d));
  float crossMark=1.0-smoothstep(-.015,.035,min(max(abs(q.x)-.42,abs(q.y)-.12),max(abs(q.x)-.12,abs(q.y)-.42)));
  float detail=clamp((center*.12+edge*.22+heart*.60+crossMark*.65)*torso,0.0,1.0);
  float panel=smoothstep(10.0,14.0,abs(p.x));
  vec3 dye=mix(mix(vec3(.007,.019,.028),vec3(.004,.011,.018),panel),vec3(0.0,.54,.445),detail);
  vec2 threads=P.xz*21.0;
  float fade=1.0-smoothstep(.7,2.5,max(fwidth(threads.x),fwidth(threads.y)));
  return dye*(1.0+.025*sin(threads.x)*sin(threads.y)*fade);
}`;
const face = `
float elianSegment(vec2 p,vec2 a,vec2 b){vec2 v=b-a;return length(p-a-v*clamp(dot(p-a,v)/dot(v,v),0.0,1.0));}
float elianTraces(vec3 P){
  vec2 p=vec2(abs(P.x/20.0),.5+(162.5-P.z)/28.0);
  float d=1.0;
  d=min(d,elianSegment(p,vec2(.24,.16),vec2(.24,.26)));
  d=min(d,elianSegment(p,vec2(.24,.26),vec2(.30,.31)));
  d=min(d,elianSegment(p,vec2(.30,.31),vec2(.30,.37)));
  d=min(d,elianSegment(p,vec2(.32,.42),vec2(.23,.48)));
  d=min(d,elianSegment(p,vec2(.23,.48),vec2(.23,.57)));
  d=min(d,elianSegment(p,vec2(.23,.57),vec2(.27,.61)));
  d=min(d,elianSegment(p,vec2(.27,.64),vec2(.25,.69)));
  d=min(d,min(abs(length(p-vec2(.24,.16))-.004),abs(length(p-vec2(.25,.69))-.004)));
  return (1.0-smoothstep(.0012,max(.0025,fwidth(d)),d))*.65*smoothstep(0.0,2.0,P.y);
}`;
const sleeves = `
float elianSleeves(vec3 P){
  vec3 Q=vec3(abs(P.x),P.y,P.z);
  float t=dot(Q-vec3(45.34694494010456,15.727310135319355,104.07102683496463),vec3(.5040975789228932,.6173149707333802,-.6039932597575269));
  float arm=smoothstep(15.0,18.0,Q.x)*smoothstep(65.0,75.0,Q.z);
  return (1.0-smoothstep(-.25,.05,t))*arm;
}`;

export function applyElianMaterials(root: THREE.Object3D) {
  root.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return;
    for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
      if (!(material instanceof THREE.MeshStandardMaterial)) continue;
      if (material.name === 'MI_Elian_HairCards') {
        material.metalness = 0;
        material.alphaToCoverage = true;
        material.onBeforeCompile = (shader) => {
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <roughnessmap_fragment>',
            '#include <roughnessmap_fragment>\nroughnessFactor=max(roughnessFactor,.72);'
          );
        };
        material.customProgramCacheKey = () => 'elian-original-silver-hair-v1';
        material.needsUpdate = true;
      }
      const isUniform = material.userData.vivaMaterial === 'elian-native-uniform-v1';
      const isFace = material.userData.vivaMaterial === 'elian-native-face-v1';
      const isSleeves = material.name === 'M_ELIAN_Sleeves';
      if (!isUniform && !isFace && !isSleeves) continue;
      if (isFace || isSleeves) {
        material.metalness = 0;
        material.roughness = 1;
      }
      const positions = node.geometry.getAttribute('position');
      const reference = new Float32Array(positions.count * 3);
      for (let i = 0; i < positions.count; i++) {
        reference[i * 3] = positions.getX(i) * 100;
        reference[i * 3 + 1] = positions.getZ(i) * 100;
        reference[i * 3 + 2] = positions.getY(i) * 100;
      }
      node.geometry.setAttribute('elianReferenceCm', new THREE.BufferAttribute(reference, 3));
      material.onBeforeCompile = (shader) => {
        shader.vertexShader =
          'attribute vec3 elianReferenceCm; varying vec3 vElianReferenceCm;\n' +
          shader.vertexShader;
        shader.vertexShader = shader.vertexShader.replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\nvElianReferenceCm=elianReferenceCm;'
        );
        shader.fragmentShader = 'varying vec3 vElianReferenceCm;\n' + shader.fragmentShader;
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <common>',
          '#include <common>\n' + (isUniform ? uniform : isSleeves ? sleeves : face)
        );
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <color_fragment>',
          '#include <color_fragment>\n' +
            (isUniform
              ? 'diffuseColor.rgb=elianCloth(vElianReferenceCm);'
              : isSleeves
                ? 'diffuseColor.rgb=mix(diffuseColor.rgb,vec3(.007,.019,.028),elianSleeves(vElianReferenceCm));'
                : 'diffuseColor.rgb=mix(diffuseColor.rgb,vec3(0.0,.54,.445),elianTraces(vElianReferenceCm));')
        );
        if (isFace) {
          // Suppress the covered shoulder skirt of the face mesh under the
          // original uniform. Keep the neck and the collar's central opening.
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <alphatest_fragment>',
            '#include <alphatest_fragment>\nif(vElianReferenceCm.z<152.5 && abs(vElianReferenceCm.x)>4.5) discard;'
          );
        }
        if (isFace || isSleeves)
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <roughnessmap_fragment>',
            '#include <roughnessmap_fragment>\nroughnessFactor=max(roughnessFactor,.75);'
          );
      };
      material.customProgramCacheKey = () =>
        isSleeves ? 'elian-original-sleeves-v1' : String(material.userData.vivaMaterial);
      material.needsUpdate = true;
    }
  });
}
