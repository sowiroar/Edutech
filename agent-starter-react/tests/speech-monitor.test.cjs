const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const ts = require('typescript');
function load(file) {
  const context = { exports: {} };
  vm.runInNewContext(
    ts.transpileModule(fs.readFileSync(file, 'utf8'), {
      compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
    }).outputText,
    context
  );
  return context.exports;
}
const { createSpeechMonitor, isTrackAudible } = load('components/avatar/speech-monitor.ts');
const { createSpeechMotion, speechRms } = load('components/avatar/speech-motion.ts');
const rest = { open: 0, round: 0, wide: 0 };
test('pose metrics distinguish unobserved transitions from zero delay; reset windows', () => {
  const m = createSpeechMonitor();
  assert.equal(m.snapshot().silence_to_rest_max_ms, null);
  m.observe(100, 0.1, rest, true);
  m.observe(133, 0.1, { ...rest, open: 0.5 }, true);
  m.observe(200, 0, { ...rest, open: 0.1 }, true);
  m.observe(267, 0, rest, true);
  const s = m.snapshot();
  assert.equal(s.acoustic_onset_to_pose_max_ms, 33);
  assert.equal(s.silence_to_rest_max_ms, 67);
  assert.equal(s.analysed_frames, 4);
  assert.equal(s.onset_observations, 1);
  assert.equal(s.close_observations, 1);
  assert.equal(m.snapshot().silence_to_rest_max_ms, null);
  m.observe(300, 0, rest, false);
  assert.equal(m.snapshot().playback_status, 'blocked');
});
test('decoded audio alone never animates paused, muted, detached or ended playback', () => {
  const el = { paused: false, ended: false, muted: false, volume: 1, readyState: 4 };
  const track = {
    isMuted: false,
    mediaStreamTrack: { readyState: 'live', enabled: true },
    attachedElements: [el],
  };
  assert.equal(isTrackAudible(track, true, 'running'), true);
  for (const patch of [
    { paused: true },
    { muted: true },
    { ended: true },
    { volume: 0 },
    { readyState: 1 },
  ]) {
    assert.equal(
      isTrackAudible({ ...track, attachedElements: [{ ...el, ...patch }] }, true, 'running'),
      false
    );
  }
  assert.equal(isTrackAudible({ ...track, attachedElements: [] }, true, 'running'), false);
  assert.equal(isTrackAudible({ ...track, isMuted: true }, true, 'running'), false);
  assert.equal(isTrackAudible(track, false, 'running'), false);
  assert.equal(isTrackAudible(track, true, 'suspended'), false);
  assert.equal(
    isTrackAudible(
      { ...track, mediaStreamTrack: { readyState: 'ended', enabled: true } },
      true,
      'running'
    ),
    false
  );
});
test('recent PCM silence closes without waiting for the entire FFT window to empty', () => {
  const pcm = new Float32Array(1024).fill(0.1);
  pcm.fill(0, 544); // latest 10 ms at 48 kHz
  assert.equal(speechRms(pcm, 48000), 0);
  assert.equal(speechRms(new Float32Array(), 48000), 0);
});
for (const fps of [15, 30, 60])
  test(`attack and silence recover at ${fps} FPS`, () => {
    const motion = createSpeechMotion();
    const pcm = new Float32Array(1024).fill(0.08);
    const spectrum = new Float32Array(512).fill(-100);
    spectrum[20] = -20;
    let pose = motion.read(pcm, spectrum, 48000, 1 / fps);
    assert.ok(pose.open > 0.25, 'responds on the first rendered frame');
    for (let i = 0; i < fps; i++) pose = motion.read(pcm, spectrum, 48000, 1 / fps);
    pcm.fill(0);
    let closeMs = 0;
    while (pose.open >= 0.01 && closeMs < 200) {
      pose = motion.read(pcm, spectrum, 48000, 1 / fps);
      closeMs += 1000 / fps;
    }
    assert.ok(closeMs <= 134, `closed after ${closeMs}ms`);
  });
