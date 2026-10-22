/** Lightweight acoustic mouth shapes. These are not timed, recognized phonemes. */
export interface MouthPose {
  open: number;
  round: number;
  wide: number;
}

export const REST_MOUTH: Readonly<MouthPose> = Object.freeze({ open: 0, round: 0, wide: 0 });
const clamp = (n: number) => Math.max(0, Math.min(1, Number.isFinite(n) ? n : 0));
const ramp = (value: number, start: number, end: number) => clamp((value - start) / (end - start));

/** RMS uses linear PCM, not saturated 8-bit FFT values. No audio leaves this reader. */
export function createSpeechMotion() {
  const pose: MouthPose = { ...REST_MOUTH };
  let peak = 0.08;
  return {
    reset() {
      peak = 0.08;
      Object.assign(pose, REST_MOUTH);
      return pose;
    },
    read(pcm: Float32Array, spectrumDb: Float32Array, sampleRate: number, dt: number): MouthPose {
      dt = Math.max(0, Math.min(0.1, dt));
      let power = 0;
      for (const v of pcm) power += v * v;
      const rms = Math.sqrt(power / Math.max(1, pcm.length));
      // Below -46 dBFS is silence; soft syllables have a smooth gate above it.
      const gate = ramp(rms, 0.005, 0.016);
      peak = Math.max(0.045, rms, peak * Math.exp(-dt / 1.5));
      const level = gate * Math.sqrt(clamp(rms / Math.max(0.045, peak * 0.85)));
      let low = 0,
        middle = 0,
        high = 0,
        hiss = 0;
      const hzPerBin = sampleRate / (spectrumDb.length * 2);
      for (let i = 1; i < spectrumDb.length; i++) {
        const hz = i * hzPerBin;
        if (hz < 180 || hz > 8000) continue;
        const value = Number.isFinite(spectrumDb[i]) ? 10 ** (spectrumDb[i] / 10) : 0;
        if (hz < 700) low += value;
        else if (hz < 1600) middle += value;
        else if (hz < 3000) high += value;
        else hiss += value;
      }
      const total = Math.max(1e-12, low + middle + high + hiss);
      const frication = ramp(hiss / total, 0.3, 0.7);
      const round = ramp(low / total, 0.58, 0.9) * (1 - ramp(high / total, 0.1, 0.3));
      const wide = ramp(high / total, 0.12, 0.42) * (1 - round);
      const targets: MouthPose = {
        open:
          level *
          (0.65 + 0.25 * ramp(middle / total, 0.1, 0.6)) *
          (1 - 0.45 * round) *
          (1 - 0.8 * frication),
        round: level * round * (1 - frication),
        wide: level * wide * (1 - 0.65 * frication),
      };
      for (const key of ['open', 'round', 'wide'] as const) {
        const time = gate === 0 ? 0.025 : targets[key] > pose[key] ? 0.035 : 0.045;
        pose[key] += (targets[key] - pose[key]) * (1 - Math.exp(-dt / time));
        if (pose[key] < 0.001) pose[key] = 0;
      }
      return pose;
    },
  };
}
