const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const sandbox = { exports: {} };
vm.runInNewContext(ts.transpileModule(fs.readFileSync('lib/telemetry/event-detail.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, sandbox);
const { describeEvent } = sandbox.exports;

test('voice transcript explains absent correlations without inventing identities or repeating text', () => {
  const event = {
    type: 'conversation_message', source: 'agent', presentation_mode: 'voice',
    identity_source: 'visitor', release: 'unknown', trace_id: 'actual-trace',
    user_id: null, agent_id: null, avatar_id: null, turn_id: null, media_session_id: null,
    payload: { role: 'assistant', text: '[CORREO]', interrupted: false, text_available: true },
  };
  const before = JSON.stringify(event);
  const { available, missing } = describeEvent(event);
  assert.equal(JSON.stringify(event), before);
  assert.equal(available.trace_id, 'actual-trace');
  assert.equal(available.release, 'unknown');
  assert.equal(available.payload.interrupted, false);
  assert.equal('text' in available.payload, false);
  assert.equal('agent_id' in available, false);
  assert.match(missing.find(x => x.field === 'agent_id').meaning, /no identifica/);
  assert.match(missing.find(x => x.field === 'avatar_id').meaning, /modo voz/);
  assert.match(missing.find(x => x.field === 'turn_id').meaning, /aún no/);
});

test('unknown measurements remain null; real zero, false and present spans survive', () => {
  const { available, missing } = describeEvent({ type: 'operation_completed',
    span_id: 'actual-span', parent_span_id: null,
    payload: { cost_usd: null, elapsed_ms: 0, result_available: false } });
  assert.equal(available.payload.cost_usd, null);
  assert.equal(available.payload.elapsed_ms, 0);
  assert.equal(available.payload.result_available, false);
  assert.equal(available.span_id, 'actual-span');
  assert.match(missing[0].meaning, /raíz/);
});

test('avatar missing data is identified as unavailable, not marked inapplicable', () => {
  const { missing } = describeEvent({ type: 'video_first_frame', presentation_mode: 'avatar',
    avatar_id: null, avatar_release: null, new_optional_field: null, payload: {} });
  assert.match(missing.find(x => x.field === 'avatar_id').meaning, /no identificado/);
  assert.match(missing.find(x => x.field === 'avatar_release').meaning, /no reportada/);
  assert.equal(missing.length, 3);
});
