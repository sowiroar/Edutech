import * as THREE from 'three';
import type { MouthPose } from './speech-motion';

/** Local acoustic approximation. Axes and displacements use each imported bind pose. */
export function createMateoRig(root: THREE.Object3D) {
  const bones = new Map<string, THREE.Object3D>();
  root.traverse((node) => {
    if (node.userData.vivaSkin === 'face') bones.set(node.userData.vivaBone, node);
  });
  root.updateWorldMatrix(true, true);
  const jaw = bones.get('FACIAL_C_Jaw');
  const lowerLip = bones.get('FACIAL_C_LipLower');
  const leftEye = bones.get('FACIAL_L_Eye');
  const rightEye = bones.get('FACIAL_R_Eye');
  const rotations: {
    bone: THREE.Object3D;
    base: THREE.Quaternion;
    axis: THREE.Vector3;
    sign: number;
    gain: number;
  }[] = [];
  const lips: {
    bone: THREE.Object3D;
    base: THREE.Vector3;
    round: THREE.Vector3;
    wide: THREE.Vector3;
  }[] = [];
  if (jaw && lowerLip && leftEye && rightEye) {
    const axis = leftEye
      .getWorldPosition(new THREE.Vector3())
      .sub(rightEye.getWorldPosition(new THREE.Vector3()))
      .normalize();
    const lever = lowerLip
      .getWorldPosition(new THREE.Vector3())
      .sub(jaw.getWorldPosition(new THREE.Vector3()));
    const sign = axis.clone().cross(lever).y > 0 ? -1 : 1;
    for (const name of ['FACIAL_C_Jaw', 'FACIAL_C_LowerLipRotation']) {
      const bone = bones.get(name);
      if (bone)
        rotations.push({
          bone,
          base: bone.quaternion.clone(),
          sign,
          // The lip rotation is an additional deformation, not a second full jaw.
          gain: name === 'FACIAL_C_Jaw' ? 1 : 0.3,
          axis: axis
            .clone()
            .applyQuaternion(bone.getWorldQuaternion(new THREE.Quaternion()).invert()),
        });
    }
    const left = bones.get('FACIAL_L_LipCorner');
    const right = bones.get('FACIAL_R_LipCorner');
    if (left && right) {
      const center = left
        .getWorldPosition(new THREE.Vector3())
        .add(right.getWorldPosition(new THREE.Vector3()))
        .multiplyScalar(0.5);
      const width = left
        .getWorldPosition(new THREE.Vector3())
        .distanceTo(right.getWorldPosition(new THREE.Vector3()));
      const forward = axis
        .clone()
        .cross(new THREE.Vector3(0, 1, 0))
        .normalize();
      if (forward.dot(lever) < 0) forward.negate();
      for (const [name, bone] of bones) {
        // Move only the primary controls: their child joints inherit the deformation.
        if (
          !/^FACIAL_[CLR]_Lip(Upper|Lower|UpperOuter|LowerOuter|Corner)$/.test(name) ||
          !bone.parent
        )
          continue;
        const at = bone.getWorldPosition(new THREE.Vector3());
        const offset = at.clone().sub(center).dot(axis);
        const corner = name.endsWith('Corner');
        const round = axis
          .clone()
          .multiplyScalar(-offset * 0.2)
          .addScaledVector(forward, width * (corner ? 0.025 : 0.075));
        const wide = axis.clone().multiplyScalar(offset * 0.14);
        // worldToLocal differences include the actual parent's scale and rotation.
        const localDelta = (delta: THREE.Vector3) =>
          bone.parent!.worldToLocal(at.clone().add(delta)).sub(bone.position);
        lips.push({
          bone,
          base: bone.position.clone(),
          round: localDelta(round),
          wide: localDelta(wide),
        });
      }
    }
  }
  const lids: { bone: THREE.Object3D; base: THREE.Vector3; delta: THREE.Vector3 }[] = [];
  for (const side of ['L', 'R']) {
    const upper = bones.get(`FACIAL_${side}_EyelidUpperA`);
    const lower = bones.get(`FACIAL_${side}_EyelidLowerA`);
    if (!upper?.parent || !lower?.parent) continue;
    const up = upper.getWorldPosition(new THREE.Vector3());
    const low = lower.getWorldPosition(new THREE.Vector3());
    const meeting = up.clone().lerp(low, 0.8);
    for (const bone of [upper, lower])
      lids.push({
        bone,
        base: bone.position.clone(),
        delta: bone.parent!.worldToLocal(meeting.clone()).sub(bone.position),
      });
  }
  const rotation = new THREE.Quaternion();
  return {
    mouthAvailable: rotations.length === 2,
    lipShapesAvailable: lips.length >= 6,
    update(pose: MouthPose, seconds: number) {
      const clamp = (v: number) => Math.max(0, Math.min(1, Number.isFinite(v) ? v : 0));
      rotations.forEach(({ bone, base, axis, sign, gain }) => {
        rotation.setFromAxisAngle(axis, sign * clamp(pose.open) * 0.12 * gain);
        bone.quaternion.copy(base).multiply(rotation);
      });
      lips.forEach(({ bone, base, round, wide }) => {
        bone.position
          .copy(base)
          .addScaledVector(round, clamp(pose.round))
          .addScaledVector(wide, clamp(pose.wide));
      });
      const phase = seconds % 4.7;
      const blink = phase < 0.22 ? Math.sin((phase / 0.22) * Math.PI) : 0;
      lids.forEach(({ bone, base, delta }) =>
        bone.position.copy(base).addScaledVector(delta, blink)
      );
    },
  };
}
