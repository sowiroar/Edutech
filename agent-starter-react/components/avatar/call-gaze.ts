import * as THREE from 'three';

/** Exported MetaHuman eye joints use local +Y as the optical forward axis. */
const EYE_FORWARD = new THREE.Vector3(0, 1, 0);
const UP = new THREE.Vector3(0, 1, 0);

export function callEyes(root: THREE.Object3D) {
  const eyes: THREE.Object3D[] = [];
  root.traverse((node) => {
    if (node.userData.vivaSkin === 'face' && /^FACIAL_[LR]_Eye$/.test(node.userData.vivaBone))
      eyes.push(node);
  });
  return eyes.length === 2 ? eyes : [];
}

/** Correct the imported presentation yaw once, including clothes/hair as one assembly. */
export function faceCallCamera(pivot: THREE.Object3D, eyes: THREE.Object3D[]) {
  if (eyes.length !== 2) return;
  pivot.updateWorldMatrix(true, true);
  const forward = new THREE.Vector3();
  const quaternion = new THREE.Quaternion();
  for (const eye of eyes)
    forward.add(EYE_FORWARD.clone().applyQuaternion(eye.getWorldQuaternion(quaternion)));
  if (Math.hypot(forward.x, forward.z) < 1e-6) return;
  pivot.rotateOnWorldAxis(UP, -Math.atan2(forward.x, forward.z));
  pivot.updateWorldMatrix(true, true);
}

/** Lens at eye height; the framing target stays lower to retain a comfortable bust shot. */
export function placeCallCamera(camera: THREE.PerspectiveCamera, eyes: THREE.Object3D[]) {
  if (eyes.length !== 2) return;
  const center = new THREE.Vector3();
  const position = new THREE.Vector3();
  for (const eye of eyes) center.add(eye.getWorldPosition(position));
  center.multiplyScalar(0.5);
  const distance = Math.max(0.5, camera.position.z - center.z);
  camera.position.x = center.x;
  camera.position.y = center.y;
  // Eyes at ~72% of image height. The camera itself is level with the gaze.
  const offset = distance * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2)) * 0.44;
  camera.lookAt(center.x, center.y - offset, center.z);
}

/** Two joint rotations only. No new textures, render passes or per-frame allocations. */
export function createCallGaze(eyes: THREE.Object3D[], camera: THREE.Camera) {
  const controls = eyes.map((eye) => ({ eye, base: eye.quaternion.clone() }));
  const position = new THREE.Vector3();
  const target = new THREE.Vector3();
  const forward = new THREE.Vector3();
  const desired = new THREE.Vector3();
  const parent = new THREE.Quaternion();
  const world = new THREE.Quaternion();
  const correction = new THREE.Quaternion();
  const identity = new THREE.Quaternion();
  return {
    update() {
      camera.getWorldPosition(target);
      for (const { eye, base } of controls) {
        if (!eye.parent) continue;
        // Restore the bind rotation before computing, avoiding accumulated drift.
        eye.quaternion.copy(base);
        eye.getWorldPosition(position);
        eye.parent.getWorldQuaternion(parent);
        world.copy(parent).multiply(base);
        forward.copy(EYE_FORWARD).applyQuaternion(world).normalize();
        desired.copy(target).sub(position).normalize();
        correction.setFromUnitVectors(forward, desired);
        const angle = correction.angleTo(identity);
        // Preserve plausible eye motion if an animation turns the head too far.
        if (angle > 0.35) correction.slerp(identity, 1 - 0.35 / angle);
        eye.quaternion.copy(parent.invert()).multiply(correction).multiply(world);
      }
    },
  };
}
