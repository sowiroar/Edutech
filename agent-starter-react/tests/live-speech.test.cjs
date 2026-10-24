const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function setup() {
  let now = 0,
    amplitude = 0.08,
    failRead = false,
    allowed = true;
  const stats = { contexts: 0, cleaned: 0 };
  const element = { paused: false, ended: false, muted: false, volume: 1, readyState: 4 };
  const track = {
    isMuted: false,
    mediaStreamTrack: { readyState: 'live', enabled: true },
    attachedElements: [element],
  };
  const observations = [];
  const node = {
    fftSize: 2048,
    frequencyBinCount: 1024,
    context: { state: 'running', sampleRate: 48000, resume: async () => {} },
    getFloatTimeDomainData(pcm) {
      if (failRead) throw Error('track replaced');
      pcm.fill(amplitude);
    },
    getFloatFrequencyData(a) {
      a.fill(-100);
      a[40] = -20;
    },
  };
  const sdk = {
    createAudioAnalyser(received) {
      assert.equal(received, track);
      stats.contexts++;
      return {
        analyser: node,
        cleanup: async () => {
          stats.cleaned++;
        },
      };
    },
  };
  const modules = {};
  function load(name) {
    if (modules[name]) return modules[name];
    const c = {
      exports: {},
      performance: { now: () => now },
      require: (dep) => (dep === 'livekit-client' ? sdk : load(dep.slice(2))),
    };
    vm.runInNewContext(
      ts.transpileModule(fs.readFileSync(`components/avatar/${name}.ts`, 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
      }).outputText,
      c
    );
    return (modules[name] = c.exports);
  }
  const reader = load('live-speech').createLiveSpeech(
    track,
    () => allowed,
    (...args) => observations.push(args)
  );
  return {
    reader,
    track,
    element,
    stats,
    observations,
    node,
    step(ms = 33.33) {
      now += ms;
      return reader.read();
    },
    silence() {
      amplitude = 0;
    },
    fail() {
      failRead = true;
    },
    block() {
      allowed = false;
    },
  };
}
test('one passive reader survives repeated model-sized pauses without creating outputs', async () => {
  const h = setup();
  assert.ok(h.step().open > 0);
  h.silence();
  const pose = h.step(2000);
  assert.equal(pose.open, 0);
  assert.equal(pose.round, 0);
  assert.equal(h.stats.contexts, 1);
  h.reader.dispose();
  h.reader.dispose();
  assert.equal(h.stats.cleaned, 1);
  assert.equal(h.step().open, 0);
});
test('muted, blocked or detached output clears an active mouth immediately', () => {
  for (const stop of [
    (h) => (h.element.muted = true),
    (h) => (h.track.attachedElements = []),
    (h) => h.block(),
    (h) => (h.node.context.state = 'suspended'),
    (h) => (h.track.mediaStreamTrack.readyState = 'ended'),
  ]) {
    const h = setup();
    assert.ok(h.step().open > 0);
    stop(h);
    assert.equal(h.step().open, 0);
    assert.equal(h.observations.at(-1)[3], false);
    h.reader.dispose();
  }
});
test('analyser errors fail at rest without escaping into the render loop', () => {
  const h = setup();
  assert.ok(h.step().open > 0);
  h.fail();
  assert.doesNotThrow(() => h.step());
  assert.equal(h.step().open, 0);
  h.reader.dispose();
});
test('ordinary speech keeps Santiago timing while silence returns to rest', () => {
  const h = setup();
  for (let i = 0; i < 30; i++) h.step();
  assert.ok(h.step().open > 0.3);
  h.silence();
  for (let i = 0; i < 5; i++) h.step();
  assert.ok(h.step().open < 0.01);
  h.reader.dispose();
});
