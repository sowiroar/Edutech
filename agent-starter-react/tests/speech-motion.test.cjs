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
