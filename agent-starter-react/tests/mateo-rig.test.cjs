const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const THREE = require('three');
const context = { exports: {}, require: () => THREE };
vm.runInNewContext(
  ts.transpileModule(fs.readFileSync('components/avatar/mateo-rig.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText,
  context
);

test('mouth opens downwards using bind-pose axes and returns to rest', () => {
  const root = new THREE.Group();
  const bone = (name, x, y, z, parent = root) => {
    const node = new THREE.Bone();
    node.userData = { vivaSkin: 'face', vivaBone: name };
    node.position.set(x, y, z);
    parent.add(node);
    return node;
  };
  const jaw = bone('FACIAL_C_Jaw', 0, 1.6, 0);
  const lipRoot = bone('FACIAL_C_LowerLipRotation', 0, 1.6, 0);
  const lip = bone('FACIAL_C_LipLower', 0, -0.02, 0.08, lipRoot);
  bone('FACIAL_L_Eye', 0.04, 1.7, 0.08);
  bone('FACIAL_R_Eye', -0.04, 1.7, 0.08);
  // An arbitrarily rotated model must not change the inferred local opening direction.
  root.rotation.y = 1.1;
  const rig = context.exports.createMateoRig(root);
  assert.equal(rig.mouthAvailable, true);
  const closed = lip.getWorldPosition(new THREE.Vector3());
  rig.update({ open: 1, round: 0, wide: 0 }, 1);
  root.updateMatrixWorld(true);
  assert.ok(lip.getWorldPosition(new THREE.Vector3()).y < closed.y);
  assert.ok(jaw.quaternion.angleTo(new THREE.Quaternion()) > 0.1);
  rig.update({ open: 0, round: 0, wide: 0 }, 1);
  root.updateMatrixWorld(true);
  assert.ok(lip.getWorldPosition(new THREE.Vector3()).distanceTo(closed) < 1e-8);
});

test('missing face controls do not pretend to provide lip animation', () => {
  const rig = context.exports.createMateoRig(new THREE.Group());
  assert.equal(rig.mouthAvailable, false);
  assert.doesNotThrow(() => rig.update({ open: 1, round: 0, wide: 0 }, 0));
});

for (const character of ['nexo', 'lira', 'elian']) {
  test(
    `${character}: installed facial controls round/spread lips without moving the eyes and return exactly to rest`,
    { skip: !fs.existsSync(`public/avatars/${character}/manifest.json`) },
    (t) => {
      const dir = `public/avatars/${character}`;
      const manifest = JSON.parse(fs.readFileSync(`${dir}/manifest.json`));
      const filename = `${dir}/${character}-${manifest.sha256}.glb`;
      if (!fs.existsSync(filename)) {
        t.skip('Private avatar model is not installed; synthetic rig tests still run.');
        return;
      }
      const data = fs.readFileSync(filename);
      const gltf = JSON.parse(data.subarray(20, 20 + data.readUInt32LE(12)).toString());
      const nodes = gltf.nodes.map((n) => {
        const o = new THREE.Object3D();
        o.userData = n.extras || {};
        if (n.translation) o.position.fromArray(n.translation);
        if (n.rotation) o.quaternion.fromArray(n.rotation);
        if (n.scale) o.scale.fromArray(n.scale);
        if (n.matrix) {
          o.matrix.fromArray(n.matrix);
          o.matrix.decompose(o.position, o.quaternion, o.scale);
        }
        return o;
      });
      gltf.nodes.forEach((n, i) => (n.children || []).forEach((c) => nodes[i].add(nodes[c])));
      const root = new THREE.Group();
      for (const id of gltf.scenes[gltf.scene || 0].nodes) root.add(nodes[id]);
      root.rotation.y = manifest.frontYaw;
      root.updateMatrixWorld(true);
      const find = (name) =>
        nodes.find((n) => n.userData.vivaSkin === 'face' && n.userData.vivaBone === name);
      const pos = (n) => n.getWorldPosition(new THREE.Vector3());
      const l = find('FACIAL_L_LipCorner'),
        r = find('FACIAL_R_LipCorner'),
        eye = find('FACIAL_L_Eye');
      const base = pos(l),
        eyeBase = pos(eye),
        width = pos(l).distanceTo(pos(r));
      const rig = context.exports.createMateoRig(root);
      assert.ok(rig.lipShapesAvailable);
      rig.update({ open: 0, round: 1, wide: 0 }, 1);
      root.updateMatrixWorld(true);
      assert.ok(pos(l).distanceTo(pos(r)) < width * 0.9);
      assert.ok(pos(l).distanceTo(base) < width * 0.2);
      assert.ok(pos(eye).distanceTo(eyeBase) < 1e-8);
      rig.update({ open: 0, round: 0, wide: 1 }, 1);
      root.updateMatrixWorld(true);
      assert.ok(pos(l).distanceTo(pos(r)) > width * 1.1);
      rig.update({ open: 0, round: 0, wide: 0 }, 1);
      root.updateMatrixWorld(true);
      assert.ok(pos(l).distanceTo(base) < 1e-8);
    }
  );
}
