import { type RemoteAudioTrack, createAudioAnalyser } from 'livekit-client';
import { isTrackAudible } from './speech-monitor';
import { type MouthPose, REST_MOUTH, createSpeechMotion, speechRms } from './speech-motion';

/** One passive analyser per remote track. Never attaches an output or delays audio. */
export function createLiveSpeech(
  track: RemoteAudioTrack,
  canPlayback: () => boolean,
  observe: (now: number, rms: number, pose: MouthPose, audible: boolean) => void
) {
  const analyser = createAudioAnalyser(track, {
    fftSize: 2048,
    smoothingTimeConstant: 0.05,
    minDecibels: -85,
    maxDecibels: -20,
  });
  const node = analyser.analyser;
  const pcm = new Float32Array(node.fftSize);
  const spectrum = new Float32Array(node.frequencyBinCount);
  const motion = createSpeechMotion();
  let previous = performance.now();
  let disposed = false;
  void (node.context as AudioContext).resume().catch(() => {});
  return {
    read(): MouthPose {
      if (disposed) return REST_MOUTH;
      const now = performance.now();
      const elapsed = (now - previous) / 1000;
      previous = now;
      // Model loading / a hidden tab must not preserve an old phonation pose.
      if (elapsed > 0.25) motion.reset();
      try {
        if (isTrackAudible(track, canPlayback(), node.context.state)) {
          node.getFloatTimeDomainData(pcm);
          node.getFloatFrequencyData(spectrum);
          const pose = motion.read(pcm, spectrum, node.context.sampleRate, elapsed);
          observe(now, speechRms(pcm, node.context.sampleRate), pose, true);
          return pose;
        }
      } catch {
        // An optional visual reader must not stop rendering or the voice output.
      }
      const pose = motion.reset();
      observe(now, 0, pose, false);
      return pose;
    },
    dispose() {
      if (disposed) return;
      disposed = true;
      motion.reset();
      void analyser.cleanup().catch(() => {});
    },
  };
}
