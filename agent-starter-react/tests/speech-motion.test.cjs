const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs'),
  vm = require('node:vm'),
  ts = require('typescript');
const context = { exports: {} };
vm.runInNewContext(
  ts.transpileModule(fs.readFileSync('components/avatar/speech-motion.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText,
  context
);
const { createSpeechMotion } = context.exports;
function signal(rms, frequencies) {
  const pcm = Float32Array.from({ length: 2048 }, (_, i) => rms * Math.SQRT2 * Math.sin(i * 0.15));
  const db = new Float32Array(1024).fill(-120);
  for (const [hz, level] of frequencies) db[Math.round(hz / (48000 / 2048))] = level;
  return [pcm, db, 48000, 1 / 30];
}
test('digital silence and a quiet noise floor never open the mouth', () => {
  const motion = createSpeechMotion();
  for (const rms of [0, 0.001, 0.004])
    for (let i = 0; i < 60; i++) {
      const p = motion.read(
        ...signal(rms, [
          [400, -85],
          [2000, -85],
        ])
      );
      assert.equal(p.open, 0);
      assert.equal(p.round, 0);
      assert.equal(p.wide, 0);
    }
});
test('distinct spectral cues change lip shape at identical loudness', () => {
  const rounded = createSpeechMotion(),
    spread = createSpeechMotion(),
    open = createSpeechMotion();
  let r, s, o;
  for (let i = 0; i < 15; i++) {
    r = rounded.read(
      ...signal(0.06, [
        [400, -25],
        [900, -40],
        [2200, -55],
      ])
    );
    s = spread.read(
      ...signal(0.06, [
        [400, -35],
        [2100, -25],
      ])
    );
    o = open.read(
      ...signal(0.06, [
        [400, -32],
        [1000, -25],
        [2000, -36],
      ])
    );
  }
  assert.ok(r.round > 0.7 && r.wide < 0.1);
  assert.ok(s.wide > 0.7 && s.round < 0.1);
  assert.ok(o.open > r.open && o.open > 0.6);
});
test('silence closes within 133 ms and a muted/replaced track resets immediately', () => {
  const motion = createSpeechMotion();
  for (let i = 0; i < 12; i++) motion.read(...signal(0.1, [[900, -20]]));
  let p;
  for (let i = 0; i < 4; i++) p = motion.read(...signal(0, []));
  assert.ok(p.open < 0.005);
  assert.deepEqual(JSON.parse(JSON.stringify(motion.reset())), { open: 0, round: 0, wide: 0 });
});
test('high-frequency frication does not force a vowel-wide jaw', () => {
  const motion = createSpeechMotion();
  let p;
  for (let i = 0; i < 10; i++) p = motion.read(...signal(0.1, [[5000, -20]]));
  assert.ok(p.open < 0.2 && p.round < 0.01 && p.wide < 0.01);
});

test('soft syllables remain visible but open less than loud vowels', () => {
  const motion = createSpeechMotion();
  for (let i = 0; i < 15; i++) motion.read(...signal(0.1, [[1000, -20]]));
  const loud = motion.read(...signal(0.1, [[1000, -20]])).open;
  let quiet;
  for (let i = 0; i < 4; i++) quiet = motion.read(...signal(0.025, [[1000, -35]])).open;
  assert.ok(quiet > loud * 0.3 && quiet < loud * 0.75, `quiet=${quiet}, loud=${loud}`);
});

for (const fps of [15, 30, 60]) {
  test(`subtle smoothing preserves Santiago's jaw and attenuates shape flicker at ${fps} FPS`, () => {
    const original = createSpeechMotion('santiago'),
      smooth = createSpeechMotion('smooth');
    let originalTravel = 0,
      smoothTravel = 0;
    let lastA = { round: 0, wide: 0 },
      lastB = { round: 0, wide: 0 };
    for (let i = 0; i < fps * 3; i++) {
      const input = signal(0.08, i % 2 ? [[400, -20]] : [[2200, -20]]);
      input[3] = 1 / fps;
      const a = original.read(...input),
        b = smooth.read(...input);
      assert.equal(a.open, b.open, 'jaw response must remain exactly unchanged');
      if (i > fps)
        for (const key of ['round', 'wide']) {
          originalTravel += Math.abs(a[key] - lastA[key]);
          smoothTravel += Math.abs(b[key] - lastB[key]);
        }
      lastA = { ...a };
      lastB = { ...b };
    }
    assert.ok(smoothTravel < originalTravel * 0.85, `travel ${smoothTravel}/${originalTravel}`);
    for (let i = 0; i < fps; i++) {
      const input = signal(0.08, [[400, -20]]);
      input[3] = 1 / fps;
      const a = original.read(...input),
        b = smooth.read(...input);
      if (i === fps - 1) assert.ok(Math.abs(a.round - b.round) < 0.001, 'same held shape');
    }
    let pose;
    for (let i = 0; i < Math.floor(0.134 * fps); i++) {
      const input = signal(0, []);
      input[3] = 1 / fps;
      pose = smooth.read(...input);
    }
    assert.ok(Math.max(pose.open, pose.round, pose.wide) < 0.01, 'silence release must stay fast');
  });
}
