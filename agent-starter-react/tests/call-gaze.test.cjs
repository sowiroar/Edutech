const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const THREE = require('three');
const context = { exports: {}, require: () => THREE };
vm.runInNewContext(
  ts.transpileModule(fs.readFileSync('components/avatar/call-gaze.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText,
  context
);
const { callEyes, faceCallCamera, placeCallCamera, createCallGaze } = context.exports;
const direction = (eye) =>
  new THREE.Vector3(0, 1, 0).applyQuaternion(eye.getWorldQuaternion(new THREE.Quaternion()));

function check(root) {
  const eyes = callEyes(root);
  assert.equal(eyes.length, 2);
  faceCallCamera(root, eyes);
  assert.ok(Math.abs(direction(eyes[0]).x) < 1e-5);
  assert.ok(direction(eyes[0]).z > 0.99);
  const camera = new THREE.PerspectiveCamera(32, 16 / 9, 0.01, 20);
  camera.position.set(0, 1.4, 1.3);
  placeCallCamera(camera, eyes);
  camera.updateMatrixWorld(true);
  const center = eyes[0]
    .getWorldPosition(new THREE.Vector3())
    .add(eyes[1].getWorldPosition(new THREE.Vector3()))
    .multiplyScalar(0.5);
  assert.ok(Math.abs(camera.position.y - center.y) < 1e-9);
  const projected = center.clone().project(camera);
  assert.ok(Math.abs(projected.x) < 1e-5);
  assert.ok(projected.y > 0.4 && projected.y < 0.48, 'eyes in upper third, without clipping');
  const bases = eyes.map((e) => e.position.clone());
  const gaze = createCallGaze(eyes, camera);
  for (let i = 0; i < 100; i++) gaze.update();
  for (let i = 0; i < eyes.length; i++) {
    const at = eyes[i].getWorldPosition(new THREE.Vector3());
    const desired = camera.position.clone().sub(at).normalize();
    assert.ok(direction(eyes[i]).angleTo(desired) < 1e-5, 'optical axis must reach the lens');
    assert.ok(eyes[i].position.distanceTo(bases[i]) < 1e-9, 'no eye translation or drift');
  }
}
test('presentation yaw is frontal and eyes converge on lens without accumulating rotation', () => {
  const root = new THREE.Group();
  root.rotation.y = 0.2142;
  for (const [side, x] of [
    ['L', 0.032],
    ['R', -0.032],
  ]) {
    const eye = new THREE.Bone();
    eye.userData = { vivaSkin: 'face', vivaBone: `FACIAL_${side}_Eye` };
    eye.position.set(x, 1.6, 0.09);
    eye.rotation.x = Math.PI / 2;
    root.add(eye);
  }
  check(root);
});
test('missing eye controls leave framing untouched', () => {
  const root = new THREE.Group(),
    camera = new THREE.PerspectiveCamera();
  camera.position.set(0, 1.4, 1.3);
  const before = camera.position.clone();
  faceCallCamera(root, []);
  placeCallCamera(camera, []);
  createCallGaze([], camera).update();
  assert.equal(camera.position.distanceTo(before), 0);
});
for (const slug of ['lira', 'nexo', 'elian']) {
  test(`${slug}: original delivered rig faces the lens, no asset edits required`, (t) => {
    const dir = `public/avatars/${slug}`;
    const m = JSON.parse(fs.readFileSync(`${dir}/manifest.json`));
    const file = `${dir}/${slug}-${m.sha256}.glb`;
    if (!fs.existsSync(file)) {
      t.skip('Private delivered GLB not installed');
      return;
    }
    const data = fs.readFileSync(file);
    const gltf = JSON.parse(data.subarray(20, 20 + data.readUInt32LE(12)));
    const nodes = gltf.nodes.map((n) => {
      const o = new THREE.Object3D();
      o.userData = n.extras || {};
      if (n.translation) o.position.fromArray(n.translation);
      if (n.rotation) o.quaternion.fromArray(n.rotation);
      if (n.scale) o.scale.fromArray(n.scale);
      if (n.matrix)
        new THREE.Matrix4().fromArray(n.matrix).decompose(o.position, o.quaternion, o.scale);
      return o;
    });
    gltf.nodes.forEach((n, i) => (n.children || []).forEach((c) => nodes[i].add(nodes[c])));
    const root = new THREE.Group();
    gltf.scenes[gltf.scene || 0].nodes.forEach((i) => root.add(nodes[i]));
    root.rotation.y = m.frontYaw;
    check(root);
  });
}

test('gaze follows mild head animation and bounds extreme turns', () => {
  const root = new THREE.Group();
  const head = new THREE.Group();
  root.add(head);
  const eyes = [];
  for (const x of [-0.032, 0.032]) {
    const eye = new THREE.Bone();
    eye.position.set(x, 1.6, 0.09);
    eye.rotation.x = Math.PI / 2;
    head.add(eye);
    eyes.push(eye);
  }
  const camera = new THREE.PerspectiveCamera();
  camera.position.set(0, 1.6, 1.3);
  const gaze = createCallGaze(eyes, camera);
  for (let i = 0; i < 150; i++) {
    head.rotation.y = Math.sin(i / 15) * 0.12;
    head.rotation.z = Math.cos(i / 20) * 0.05;
    gaze.update();
    for (const eye of eyes) {
      const desired = camera.position
        .clone()
        .sub(eye.getWorldPosition(new THREE.Vector3()))
        .normalize();
      assert.ok(direction(eye).angleTo(desired) < 1e-5);
    }
  }
  head.rotation.set(0, 1, 0);
  gaze.update();
  for (const eye of eyes) {
    const rest = new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(1, 0, 0), Math.PI / 2);
    assert.ok(eye.quaternion.angleTo(rest) <= 0.35001, 'extreme turn must not roll eyes backwards');
  }
});
