const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
const { randomUUID } = require('node:crypto');
function harness(fetch) {
  const listeners = new Map();
  class Audio {}
  const sandbox = {
    exports: {},
    require: () => ({
      ConnectionState: {
        Connecting: 'connecting',
        Connected: 'connected',
        Disconnected: 'disconnected',
      },
      RoomEvent: { ConnectionStateChanged: 'state', Reconnected: 'recovered' },
    }),
    crypto: { randomUUID },
    performance: { now: () => 100 },
    Date,
    fetch,
    AbortSignal,
    setTimeout: () => 1,
    clearTimeout: () => {},
    HTMLAudioElement: Audio,
    document: {
      addEventListener: (name, cb) => listeners.set(name, cb),
      removeEventListener: (name) => listeners.delete(name),
    },
  };
  vm.runInNewContext(
    ts.transpileModule(fs.readFileSync('lib/telemetry/client.ts', 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    sandbox
  );
  const room = {
    state: 'connected',
    remoteParticipants: new Map(),
    on: (name, cb) => listeners.set(name, cb),
    off: () => {},
  };
  return { client: new sandbox.exports.MediaTelemetry(), room, listeners, Audio };
}
test('pre-token connection survives; only the agent audio records first playback once', async () => {
  const sent = [];
  const h = harness(async (_, opts) => {
    sent.push(JSON.parse(opts.body));
    return { ok: true };
  });
  h.client.attach(h.room);
  h.client.beginSession();
  const audio = new h.Audio();
  audio.muted = false;
  audio.volume = 1;
  h.listeners.get('playing')({ target: audio });
  assert.equal(h.client.pending.length, 1);
  h.room.remoteParticipants.set('agent', {
    isAgent: true,
    audioTrackPublications: new Map([['audio', { track: { attachedElements: [audio] } }]]),
  });
  h.listeners.get('playing')({ target: audio });
  h.listeners.get('playing')({ target: audio });
  h.client.setToken('session-a');
  await h.client.flush();
  assert.equal(sent[0].events.length, 2);
  assert.equal(sent[0].events[0].type, 'media_connect_started');
  assert.equal(sent[0].events[1].type, 'audio_playback_started');
  assert.equal(sent[0].events[0].connection_attempt_id, sent[0].events[1].connection_attempt_id);
});
test('late acknowledgment cannot delete a new session queue', async () => {
  let resolve;
  const h = harness(
    () =>
      new Promise((r) => {
        resolve = r;
      })
  );
  h.client.attach(h.room);
  h.client.beginSession();
  h.client.setToken('old');
  const flushing = h.client.flush();
  h.client.beginSession();
  h.client.setToken('new');
  const newId = h.client.pending[0].event_id;
  resolve({ ok: true });
  await flushing;
  assert.equal(h.client.pending.length, 1);
  assert.equal(h.client.pending[0].event_id, newId);
});

test('avatar samples require a call token and keep the call connection identifiers', async () => {
  const sent = [];
  const h = harness(async (_, opts) => {
    sent.push(JSON.parse(opts.body));
    return { ok: true };
  });
  h.client.attach(h.room);
  h.client.avatarSample({ character: 'LIRA' });
  assert.equal(h.client.pending.length, 0);
  h.client.beginSession();
  h.client.avatarSample({ character: 'LIRA' });
  assert.equal(h.client.pending.length, 1);
  h.client.setToken('call-token');
  h.client.avatarSample({ character: 'LIRA', model_sha256: 'a'.repeat(64), fps: 30 });
  await h.client.flush();
  assert.equal(sent[0].events[1].type, 'avatar_quality_sample');
  assert.equal(sent[0].events[1].connection_attempt_id, sent[0].events[0].connection_attempt_id);
  assert.equal(sent[0].events[1].media_session_id, sent[0].events[0].media_session_id);
  h.client.beginSession();
  h.client.avatarSample({ character: 'ELIAN' });
  assert.equal(h.client.pending.length, 1, 'old call token is cleared');
});

test('SDK prefetch neither starts the connection clock nor rebinds active events', async () => {
  const sent = [];
  const h = harness(async (_, opts) => {
    sent.push(JSON.parse(opts.body));
    return { ok: true };
  });
  h.client.attach(h.room);
  h.client.setToken('prepared-first');
  assert.equal(h.client.pending.length, 0);
  h.client.beginSession();
  h.listeners.get('state')('connected');
  h.client.setToken('prepared-next');
  h.client.avatarSample({ character: 'ELIAN' });
  await h.client.flush();
  assert.equal(sent[0].context_token, 'prepared-first');
  const firstAttempt = sent[0].events[0].connection_attempt_id;
  h.client.beginSession();
  await h.client.flush();
  assert.equal(sent[1].context_token, 'prepared-next');
  assert.notEqual(sent[1].events[0].connection_attempt_id, firstAttempt);
  assert.equal(sent[1].events[0].type, 'media_connect_started');
});

test('expired prefetched credentials can refresh before connection', async () => {
  const sent = [];
  const h = harness(async (_, opts) => {
    sent.push(JSON.parse(opts.body));
    return { ok: true };
  });
  h.client.attach(h.room);
  h.client.setToken('expired');
  h.client.beginSession();
  h.client.setToken('fresh');
  h.listeners.get('state')('connected');
  await h.client.flush();
  assert.equal(sent[0].context_token, 'fresh');
  assert.equal(sent[0].events[0].type, 'media_connect_started');
  h.listeners.get('state')('disconnected');
  const count = h.client.pending.length;
  h.client.avatarSample({ character: 'ELIAN' });
  assert.equal(h.client.pending.length, count);
});
