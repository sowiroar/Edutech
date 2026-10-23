const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const path = require('node:path');

function reader(manifest, fileBytes = 1024, previewManifest = null) {
  const readPaths = [];
  const mockedFs = {
    readFile: async (name) => {
      const selected = name.endsWith('/manifest.preview.json') ? previewManifest : manifest;
      if (name.endsWith('/manifest.preview.json') && !selected)
        throw Object.assign(new Error('no preview'), { code: 'ENOENT' });
      if (!selected) throw new Error('missing');
      return JSON.stringify({
        web_profile: 2,
        export_profile: 3,
        visual_review: 'passed',
        motion_review: 'passed',
        mouth_mapping: 'amplitude-verified',
        animations: 1,
        ...selected,
      });
    },
    stat: async (name) => {
      readPaths.push(name);
      return { isFile: () => true, size: fileBytes };
    },
  };
  const context = {
    exports: {},
    process: { cwd: () => '/app' },
    require: (name) => {
      if (name === 'node:fs/promises') return mockedFs;
      if (name === 'node:path') return { default: path };
      if (name === './browser-avatar')
        return { AVATAR_MAX_BYTES: 20 * 1024 * 1024, WEB_CHARACTERS: ['LIRA', 'NEXO', 'ELIAN'] };
      throw new Error(name);
    },
  };
  vm.runInNewContext(
    ts.transpileModule(fs.readFileSync('lib/browser-avatar-server.ts', 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    context
  );
  return { get: context.exports.browserAvatar, readPaths };
}

test('missing export does not advertise an available avatar', async () => {
  assert.equal(await reader(null).get(), null);
});
test('manifest cannot request an external or traversing model path', async () => {
  const fixture = reader({ sha256: '../../secret', bytes: 1024, frontYaw: 0 });
  assert.equal(await fixture.get(), null);
  assert.equal(fixture.readPaths.length, 0);
});
test('truncated or oversized model cannot become ready', async () => {
  const manifest = { sha256: 'a'.repeat(64), bytes: 1024, frontYaw: 0 };
  assert.equal(await reader(manifest, 100).get(), null);
  assert.equal(
    await reader({ ...manifest, bytes: 30 * 1024 * 1024 }, 30 * 1024 * 1024).get(),
    null
  );
});
test('installed model uses browser assets without a renderer lease', async () => {
  const value = await reader({
    sha256: 'a'.repeat(64),
    bytes: 1024,
    frontYaw: 0,
    visual_review: 'passed',
    motion_review: 'passed',
    mouth_mapping: 'amplitude-verified',
    animations: 1,
  }).get();
  assert.equal(value.engine, 'webgl');
  assert.equal(value.modelUrl, `/avatars/nexo/nexo-${'a'.repeat(64)}.glb`);
  assert.equal(value.token, undefined);
});

test('unreviewed candidate is previewable but cannot be offered in a call', async () => {
  const candidate = reader({
    sha256: 'a'.repeat(64),
    bytes: 1024,
    frontYaw: 0,
    visual_review: 'pending',
    motion_review: 'pending',
    mouth_mapping: 'pending',
    animations: 0,
  });
  assert.equal(await candidate.get(), null);
  assert.equal((await candidate.get({ preview: true })).engine, 'webgl');
});

test('review cannot enable a static export or an unverified mouth', async () => {
  const approved = {
    sha256: 'a'.repeat(64),
    bytes: 1024,
    frontYaw: 0,
    visual_review: 'passed',
    motion_review: 'passed',
    mouth_mapping: 'amplitude-verified',
    animations: 1,
  };
  assert.equal(await reader({ ...approved, animations: 0 }).get(), null);
  assert.equal(await reader({ ...approved, mouth_mapping: 'pending' }).get(), null);
});

test('LIRA uses her own directory and cannot be served as NEXO', async () => {
  const candidate = reader({
    character: 'LIRA',
    source_scene: '/Game/VIVA/Avatars/Lira/Maps/L_Lira',
    sha256: 'a'.repeat(64),
    bytes: 1024,
    frontYaw: 0,
  });
  const lira = await candidate.get({ character: 'LIRA' });
  assert.equal(lira.character, 'LIRA');
  assert.equal(lira.modelUrl, `/avatars/lira/lira-${'a'.repeat(64)}.glb`);
  assert.equal(await candidate.get({ character: 'NEXO' }), null);
  assert.equal(await candidate.get({ character: '../secret' }), null);
  assert.equal(
    await reader({
      character: 'LIRA',
      source_scene: '/Game/UniversityVirtualAssistant/FamiliaVIVA/LIRA/NewMap_LIRA_Studio',
      sha256: 'a'.repeat(64),
      bytes: 1024,
      frontYaw: 0,
    }).get({ character: 'LIRA' }),
    null
  );
});

test('agent handoffs select only the model announced by the agent', () => {
  const context = { exports: {} };
  vm.runInNewContext(
    ts.transpileModule(fs.readFileSync('lib/browser-avatar.ts', 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    context
  );
  const select = context.exports.avatarForAgent;
  const lira = { character: 'LIRA' },
    nexo = { character: 'NEXO' };
  const assets = [lira, nexo];
  assert.equal(select(undefined, assets), null);
  assert.equal(select('LIRA', assets), lira);
  assert.equal(select('NEXO', assets), nexo);
  assert.equal(select('nexus', assets), nexo);
  assert.equal(select(' LIRA ', assets), lira);
  assert.equal(select('ELIAN', assets), null);
  assert.equal(select('unknown', assets), null);
  assert.equal(select('LIRA', [nexo]), null);
  const elian = { character: 'ELIAN' };
  assert.equal(select('ELIAN', [...assets, elian]), elian);
});

test('ELIAN requires her original scene and retains its validated studio color', async () => {
  const manifest = {
    character: 'ELIAN',
    source_scene: '/Game/VIVA/Avatars/Elian/Maps/L_Elian',
    sha256: 'a'.repeat(64),
    bytes: 1024,
    frontYaw: Math.PI / 2,
    background_color: '#0b2129',
  };
  const asset = await reader(manifest).get({ character: 'ELIAN' });
  assert.equal(asset.character, 'ELIAN');
  assert.equal(asset.backgroundColor, '#0b2129');
  assert.ok(asset.modelUrl.startsWith('/avatars/elian/elian-'));
  assert.equal(
    await reader({
      ...manifest,
      source_scene: '/Game/UniversityVirtualAssistant/FamiliaVIVA/ELIAN/NewMap_ELIAN_Studio',
    }).get({ character: 'ELIAN' }),
    null
  );
  assert.equal(
    (
      await reader({ ...manifest, background_color: 'url(https://invalid.test)' }).get({
        character: 'ELIAN',
      })
    ).backgroundColor,
    undefined
  );
});

test('a separate candidate never replaces the model advertised for calls', async () => {
  const approved = { sha256: 'a'.repeat(64), bytes: 1024, frontYaw: 0 };
  const candidate = { ...approved, sha256: 'b'.repeat(64), visual_review: 'pending' };
  const fixture = reader(approved, 1024, candidate);
  assert.equal((await fixture.get()).sha256, approved.sha256);
  assert.equal((await fixture.get({ preview: true })).sha256, candidate.sha256);
  assert.equal(
    (await fixture.get({ preview: true })).backgroundUrl,
    '/avatars/nexo/uam-background.preview.jpg'
  );
  assert.equal((await fixture.get()).backgroundUrl, '/avatars/nexo/uam-background.jpg');
});
