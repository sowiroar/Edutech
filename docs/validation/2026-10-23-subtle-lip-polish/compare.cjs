// Run from repository root; input must be a generated mono PCM16 WAV, never a call recording.
const fs = require('node:fs');
const vm = require('node:vm');
const crypto = require('node:crypto');
const ts = require(process.cwd() + '/agent-starter-react/node_modules/typescript');
const env = { exports: {} };
vm.runInNewContext(ts.transpileModule(fs.readFileSync('agent-starter-react/components/avatar/speech-motion.ts', 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
}).outputText, env);
const wav = fs.readFileSync(process.argv[2]);
let sampleRate, samples;
for (let at = 12; at + 8 <= wav.length;) {
  const name = wav.toString('ascii', at, at + 4), length = wav.readUInt32LE(at + 4), start = at + 8;
  if (name === 'fmt ') {
    if (wav.readUInt16LE(start) !== 1 || wav.readUInt16LE(start + 2) !== 1 || wav.readUInt16LE(start + 14) !== 16) throw Error('Expected mono PCM16');
    sampleRate = wav.readUInt32LE(start + 4);
  }
  if (name === 'data') samples = Float32Array.from({ length: length / 2 }, (_, i) => wav.readInt16LE(start + i * 2) / 32768);
  at = start + length + (length % 2);
}
if (!sampleRate || !samples) throw Error('Missing PCM');
// Deterministic offline FFT with a Blackman window; not a browser/audio-output measurement.
function spectrum(pcm) {
  const n = pcm.length, re = new Float64Array(n), im = new Float64Array(n);
  for (let i = 0; i < n; i++) re[i] = pcm[i] * (0.42 - 0.5 * Math.cos(2 * Math.PI * i / n) + 0.08 * Math.cos(4 * Math.PI * i / n));
  for (let i = 1, j = 0; i < n; i++) {
    let bit = n >> 1;
    for (; j & bit; bit >>= 1) j ^= bit;
    j ^= bit;
    if (i < j) [re[i], re[j]] = [re[j], re[i]];
  }
  for (let size = 2; size <= n; size *= 2) for (let offset = 0; offset < n; offset += size) {
    for (let j = 0; j < size / 2; j++) {
      const angle = -2 * Math.PI * j / size, c = Math.cos(angle), s = Math.sin(angle);
      const a = offset + j, b = a + size / 2, tr = c * re[b] - s * im[b], ti = s * re[b] + c * im[b];
      re[b] = re[a] - tr; im[b] = im[a] - ti; re[a] += tr; im[a] += ti;
    }
  }
  return Float32Array.from({ length: n / 2 }, (_, i) => 10 * Math.log10(Math.max(1e-15, (re[i] ** 2 + im[i] ** 2) / n ** 2)));
}
const reports = [];
for (const fps of [15, 30, 60]) {
  const a = env.exports.createSpeechMotion('santiago'), b = env.exports.createSpeechMotion('smooth');
  let jawMaxError = 0, oldTravel = 0, newTravel = 0, error2 = 0, count = 0;
  let lastA = { round: 0, wide: 0 }, lastB = { round: 0, wide: 0 };
  for (let frame = 0; frame <= Math.ceil(samples.length / sampleRate * fps) + fps / 2; frame++) {
    const end = Math.round(frame * sampleRate / fps);
    const pcm = Float32Array.from({ length: 2048 }, (_, i) => samples[end - 2048 + i] ?? 0);
    const db = spectrum(pcm), x = a.read(pcm, db, sampleRate, 1 / fps), y = b.read(pcm, db, sampleRate, 1 / fps);
    jawMaxError = Math.max(jawMaxError, Math.abs(x.open - y.open));
    for (const key of ['round', 'wide']) {
      oldTravel += Math.abs(x[key] - lastA[key]); newTravel += Math.abs(y[key] - lastB[key]);
      error2 += (x[key] - y[key]) ** 2; count++;
    }
    lastA = { ...x }; lastB = { ...y };
  }
  reports.push({ fps, jawMaxError, shapeTravelReductionPercent: +(100 * (1 - newTravel / oldTravel)).toFixed(2),
    shapeRmsDifference: +Math.sqrt(error2 / count).toFixed(4), rest: lastB });
}
console.log(JSON.stringify({ scope: 'offline-synthetic-speech-not-perceptual-acceptance',
  audioSha256: crypto.createHash('sha256').update(wav).digest('hex'), sampleRate,
  durationSeconds: samples.length / sampleRate, reports }, null, 2));
