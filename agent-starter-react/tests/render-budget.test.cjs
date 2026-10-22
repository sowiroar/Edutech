const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const THREE = require('three');
const context = { exports: {}, require: () => THREE };
vm.runInNewContext(
  ts.transpileModule(fs.readFileSync('components/avatar/render-budget.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText,
  context
);

test('high DPI and tall layouts stay inside the pixel budget', () => {
  for (const [w, h, ratio] of [
    [3840, 2160, 3],
    [960, 540, 2],
    [320, 2000, 4],
    [213, 120, 1],
    [0, 0, 2],
  ]) {
    const size = context.exports.renderSize(w, h, ratio);
    assert.ok(size.width >= 2 && size.width <= 1280);
    assert.ok(size.height >= 2 && size.height <= 720);
    assert.ok(size.width * size.height <= 1280 * 720);
  }
});

test('shared assets are counted once, including uncompressed texture mipmaps', () => {
  const root = new THREE.Group();
  const texture = new THREE.Texture({ width: 2048, height: 2048 });
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute(
    'position',
    new THREE.Float32BufferAttribute([0, 0, 0, 1, 0, 0, 0, 1, 0], 3)
  );
  geometry.setIndex([0, 1, 2]);
  const material = new THREE.MeshStandardMaterial({ map: texture, emissiveMap: texture });
  root.add(new THREE.Mesh(geometry, material), new THREE.Mesh(geometry, material));
  const estimate = context.exports.assetMemory(root);
  assert.equal(estimate.textureBytesEstimate, Math.ceil((2048 * 2048 * 4 * 4) / 3));
  assert.equal(estimate.geometryDataBytes, 36 + 6);
});
