import * as THREE from 'three';

// Juan's procedural fabric and projected facial traces, transcribed from
// Avatar/scripts/unreal/style_lira_uniform.py and apply_lira_face_traces.py.
// glTF cannot bake the fabric's two position UV sets or a deferred decal faithfully.
const uniform = `
vec3 vivaCloth(vec3 P) {
  float front=smoothstep(1.0,5.0,P.y);
  float torso=(1.0-smoothstep(17.0,20.0,abs(P.x)))*smoothstep(100.0,106.0,P.z)*(1.0-smoothstep(143.0,147.0,P.z))*front;
  float center=1.0-smoothstep(.045,.12,abs(P.x));
  float sideTarget=12.0+2.8*smoothstep(134.0,146.0,P.z);
  float edge=1.0-smoothstep(.045,.11,abs(abs(P.x)-sideTarget));
  float edge2=1.0-smoothstep(.03,.08,abs(abs(P.x)-sideTarget-1.0));
  float sideSeams=(edge+.30*edge2)*smoothstep(111.0,119.0,P.z);
  float panel=smoothstep(10.5,13.0,abs(P.x))*torso;
  vec2 q=vec2(P.x+7.0,P.z-134.0);
  float ring=(1.0-smoothstep(.05,.12,abs(length(q)-1.75)))*.6;
  float flow=0.0;
  for(int i=0;i<3;i++){float x=q.x+(float(i)-1.0)*.55;float target=.55*sin(q.y*1.5);flow=max(flow,1.0-smoothstep(.035,.085,abs(x-target)));}
  flow*=1.0-smoothstep(1.15,1.4,abs(q.y));
  flow*=1.0-smoothstep(1.15,1.4,abs(q.x));
  float lines=clamp((center*.12+sideSeams*.32+ring+flow)*torso,0.0,1.0);
  vec3 cloth=mix(vec3(.009,.008,.018),vec3(.004,.004,.009),panel);
  return mix(cloth,vec3(.571,.205,1.0),lines);
}`;

const face = `
float vivaSegment(vec2 p,vec2 a,vec2 b){vec2 v=b-a;return length(p-a-v*clamp(dot(p-a,v)/dot(v,v),0.0,1.0));}
float vivaTraces(vec3 P){
  vec2 p=vec2(abs(P.x/20.0),.5+(166.0-P.z)/28.0);
  float d=1.0;
  d=min(d,vivaSegment(p,vec2(.24,.16),vec2(.24,.26)));
  d=min(d,vivaSegment(p,vec2(.24,.26),vec2(.30,.31)));
  d=min(d,vivaSegment(p,vec2(.30,.31),vec2(.30,.37)));
  d=min(d,vivaSegment(p,vec2(.32,.42),vec2(.23,.48)));
  d=min(d,vivaSegment(p,vec2(.23,.48),vec2(.23,.57)));
  d=min(d,vivaSegment(p,vec2(.23,.57),vec2(.27,.61)));
  d=min(d,vivaSegment(p,vec2(.27,.64),vec2(.25,.69)));
  float nodes=min(abs(length(p-vec2(.24,.16))-.004),abs(length(p-vec2(.25,.69))-.004));
  d=min(d,nodes);
  return (1.0-smoothstep(.0012,max(.0025,fwidth(d)),d))*.65*smoothstep(0.0,2.0,P.y);
}`;

export function applyLiraMaterials(root: THREE.Object3D) {
  root.traverse((node) => {
    if (!(node instanceof THREE.Mesh)) return;
    const materials = Array.isArray(node.material) ? node.material : [node.material];
    for (const material of materials) {
      if (!(material instanceof THREE.MeshStandardMaterial)) continue;
      if (material.name.includes('SlightArch')) {
        material.alphaTest = 0;
        material.transparent = true;
        material.depthWrite = false;
        material.opacity = 1;
        material.forceSinglePass = true;
        // Preserve subpixel strands from the original atlas after web mipmapping.
        material.onBeforeCompile = (shader) => {
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <map_fragment>',
            '#include <map_fragment>\ndiffuseColor.a = min(1.0, diffuseColor.a * 3.5);'
          );
        };
        material.customProgramCacheKey = () => 'lira-original-brows-coverage-v1';
        material.needsUpdate = true;
      }
      const isUniform = material.userData.vivaMaterial === 'lira-juan-uniform-v1';
      const isFace = material.userData.vivaMaterial === 'lira-juan-face-v1';
      if (!isUniform && !isFace) continue;
      const positions = node.geometry.getAttribute('position');
      const reference = new Float32Array(positions.count * 3);
      for (let i = 0; i < positions.count; i++) {
        reference[i * 3] = positions.getX(i) * 100;
        reference[i * 3 + 1] = positions.getZ(i) * 100;
        reference[i * 3 + 2] = positions.getY(i) * 100;
      }
      node.geometry.setAttribute('vivaReferenceCm', new THREE.BufferAttribute(reference, 3));
      material.onBeforeCompile = (shader) => {
        shader.vertexShader =
          'attribute vec3 vivaReferenceCm; varying vec3 vVivaReferenceCm;\n' + shader.vertexShader;
        shader.vertexShader = shader.vertexShader.replace(
          '#include <begin_vertex>',
          '#include <begin_vertex>\nvVivaReferenceCm = vivaReferenceCm;'
        );
        shader.fragmentShader = 'varying vec3 vVivaReferenceCm;\n' + shader.fragmentShader;
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <common>',
          '#include <common>\n' + (isUniform ? uniform : face)
        );
        shader.fragmentShader = shader.fragmentShader.replace(
          '#include <color_fragment>',
          '#include <color_fragment>\n' +
            (isUniform
              ? 'diffuseColor.rgb = vivaCloth(vVivaReferenceCm);'
              : 'diffuseColor.rgb = mix(diffuseColor.rgb, vec3(.42,.18,.72), vivaTraces(vVivaReferenceCm));')
        );
      };
      material.customProgramCacheKey = () => String(material.userData.vivaMaterial);
      material.needsUpdate = true;
    }
  });
}
