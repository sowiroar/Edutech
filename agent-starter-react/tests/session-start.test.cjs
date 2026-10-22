const { test } = require('node:test');
const assert = require('node:assert/strict');
const { EventEmitter } = require('node:events');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');

const context = {
  exports: {},
  AbortController,
  setTimeout,
  clearTimeout,
  Error,
  require: (name) => {
    assert.equal(name, 'livekit-client');
    return { RoomEvent: { Disconnected: 'disconnected' } };
  },
};
vm.runInNewContext(
  ts.transpileModule(fs.readFileSync('lib/session-start.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText,
  context
);
const { startSessionAttempt } = context.exports;

test('disconnect settles a start that the SDK leaves pending and aborts its waiter', async () => {
  const room = new EventEmitter();
  let signal;
  const result = startSessionAttempt({
    room,
    start: (options) => {
      signal = options.signal;
      return new Promise(() => {});
    },
    timeoutMs: 1000,
  });
  room.emit('disconnected');
  await assert.rejects(result, /conexión/);
  assert.equal(signal.aborted, true);
  assert.equal(room.listenerCount('disconnected'), 0);
});

test('a bounded wait releases a stuck connection without an agent', async () => {
  const room = new EventEmitter();
  let signal;
  await assert.rejects(
    startSessionAttempt({
      room,
      start: (options) => {
        signal = options.signal;
        return new Promise(() => {});
      },
      timeoutMs: 10,
    }),
    /tiempo/
  );
  assert.equal(signal.aborted, true);
  assert.equal(room.listenerCount('disconnected'), 0);
});

test('a successful connection is kept open and removes its temporary listeners', async () => {
  const room = new EventEmitter();
  let signal;
  await startSessionAttempt({
    room,
    start: async (options) => {
      signal = options.signal;
    },
    timeoutMs: 100,
  });
  room.emit('disconnected');
  assert.equal(signal.aborted, false);
  assert.equal(room.listenerCount('disconnected'), 0);
});

test('permission or token failures retain the original error and abort startup', async () => {
  const room = new EventEmitter();
  let signal;
  const denied = new Error('Permission denied');
  await assert.rejects(
    startSessionAttempt({
      room,
      start: async (options) => {
        signal = options.signal;
        throw denied;
      },
      timeoutMs: 100,
    }),
    (e) => e === denied
  );
  assert.equal(signal.aborted, true);
  assert.equal(room.listenerCount('disconnected'), 0);
});
