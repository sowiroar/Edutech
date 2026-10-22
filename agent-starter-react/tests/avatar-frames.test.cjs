const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function route(api) {
  const sandbox = { exports: {}, require: () => api, Response };
  vm.runInNewContext(ts.transpileModule(fs.readFileSync('app/api/avatar/frame/route.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, sandbox);
  return sandbox.exports.GET;
}
test('no proof cannot fetch the shared renderer', async () => {
  let calls = 0;
  const get = route({ claims: async () => { throw new Error(); }, renderer: () => calls++ });
  assert.notEqual((await get(new Request('http://local/api/avatar/frame'))).status, 200);
  assert.equal(calls, 0);
});
test('released owner cannot receive a frame that arrived after release', async () => {
  let checks = 0;
  const get = route({ claims: async () => ({}), owns: async () => ++checks === 1,
    renderer: async () => new Response('synthetic', { headers: { 'content-type': 'image/jpeg' } }) });
  const result = await get(new Request('http://local/api/avatar/frame'));
  assert.equal(result.status, 409);
  assert.equal(await result.text(), '');
});
test('owner with an active ready lease receives one bounded JPEG', async () => {
  const get = route({ claims: async () => ({}), owns: async () => true,
    renderer: async () => new Response('synthetic', { headers: { 'content-type': 'image/jpeg' } }) });
  const result = await get(new Request('http://local/api/avatar/frame'));
  assert.equal(result.status, 200);
  assert.equal(await result.text(), 'synthetic');
  assert.equal(result.headers.get('cache-control'), 'no-store');
});
