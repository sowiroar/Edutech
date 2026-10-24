const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function setup({ pendingResume = false, failPlay = false } = {}) {
  let audio,
    context,
    resolveResume,
    now = 0;
  const stats = { revoked: 0, closed: 0, played: 0, outputs: 0 };
  const analyser = {
    frequencyBinCount: 1024,
    connect() {
      stats.outputs++;
    },
    disconnect() {},
    getFloatTimeDomainData(a) {
      a.fill(0.1);
    },
    getFloatFrequencyData(a) {
      a.fill(-100);
      a[40] = -20;
    },
  };
  class FakeContext {
    constructor() {
      context = this;
      this.state = 'running';
      this.sampleRate = 48000;
    }
    createMediaElementSource() {
      return { connect() {}, disconnect() {} };
    }
    createAnalyser() {
      return analyser;
    }
    resume() {
      return pendingResume
        ? new Promise((r) => {
            resolveResume = r;
          })
        : Promise.resolve();
    }
    close() {
      stats.closed++;
      this.state = 'closed';
      return Promise.resolve();
    }
  }
  class FakeAudio {
    constructor() {
      audio = this;
      this.paused = true;
      this.ended = false;
    }
    play() {
      stats.played++;
      if (failPlay) return Promise.reject(Error('blocked'));
      this.paused = false;
      return Promise.resolve();
    }
    pause() {
      this.paused = true;
    }
    removeAttribute() {}
    load() {}
  }
  const globals = {
    AudioContext: FakeContext,
    Audio: FakeAudio,
    URL: {
      createObjectURL: () => 'blob:local',
      revokeObjectURL() {
        stats.revoked++;
      },
    },
    performance: { now: () => (now += 33.333) },
  };
  function load(name) {
    const env = { ...globals, exports: {}, require: (dep) => load(dep.slice(2)) };
    vm.runInNewContext(
      ts.transpileModule(fs.readFileSync(`components/avatar/${name}.ts`, 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
      }).outputText,
      env
    );
    return env.exports;
  }
  return {
    create: load('preview-audio').createPreviewAudio,
    stats,
    audio: () => audio,
    context: () => context,
    resume: () => resolveResume(),
  };
}
test('local playback drives the same acoustic pose and ends at rest, releasing output', async () => {
  const h = setup();
  let ended = 0;
  const p = h.create(
    {},
    () => ended++,
    () => assert.fail('unexpected error')
  );
  await p.play();
  assert.ok(p.read().open > 0);
  assert.equal(h.stats.outputs, 1);
  h.audio().onended();
  assert.equal(ended, 1);
  assert.equal(p.read().open, 0);
  p.dispose();
  assert.equal(h.stats.closed, 1);
  assert.equal(h.stats.revoked, 1);
});
test('stop while AudioContext resumes never starts late playback', async () => {
  const h = setup({ pendingResume: true });
  const p = h.create(
    {},
    () => assert.fail('unexpected end'),
    () => {}
  );
  const start = p.play();
  p.dispose();
  h.resume();
  await start;
  assert.equal(h.stats.played, 0);
  assert.equal(p.read().open, 0);
  assert.equal(h.stats.closed, 1);
});
test('playback errors release resources and cannot leave the mouth open', async () => {
  const h = setup({ failPlay: true });
  const p = h.create(
    {},
    () => {},
    () => {}
  );
  await assert.rejects(p.play(), /blocked/);
  assert.equal(p.read().open, 0);
  assert.equal(h.stats.closed, 1);
  assert.equal(h.stats.revoked, 1);
});
