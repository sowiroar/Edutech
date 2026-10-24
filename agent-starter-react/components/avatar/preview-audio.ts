import { createSpeechMonitor } from './speech-monitor';
import { REST_MOUTH, type SpeechMotionStyle, createSpeechMotion, speechRms } from './speech-motion';

/** One local output, no microphone, upload or persistence. Same motion as calls. */
export function createPreviewAudio(
  file: File,
  onEnded: () => void,
  onError: () => void,
  style: SpeechMotionStyle = 'smooth'
) {
  const context = new AudioContext();
  const url = URL.createObjectURL(file);
  const audio = new Audio(url);
  const source = context.createMediaElementSource(audio);
  const analyser = context.createAnalyser();
  analyser.fftSize = 2048;
  analyser.smoothingTimeConstant = 0.05;
  analyser.minDecibels = -85;
  analyser.maxDecibels = -20;
  source.connect(analyser);
  analyser.connect(context.destination);
  const pcm = new Float32Array(analyser.fftSize);
  const spectrum = new Float32Array(analyser.frequencyBinCount);
  const motion = createSpeechMotion(style);
  const monitor = createSpeechMonitor();
  let disposed = false;
  let previous = performance.now();
  const dispose = () => {
    if (disposed) return;
    disposed = true;
    audio.onended = audio.onerror = null;
    audio.pause();
    audio.removeAttribute('src');
    audio.load();
    source.disconnect();
    analyser.disconnect();
    void context.close().catch(() => {});
    URL.revokeObjectURL(url);
    motion.reset();
  };
  audio.onended = () => {
    dispose();
    onEnded();
  };
  audio.onerror = () => {
    dispose();
    onError();
  };
  return {
    async play() {
      try {
        await context.resume();
        if (disposed) return;
        await audio.play();
      } catch (error) {
        if (disposed) return;
        dispose();
        throw error;
      }
    },
    read() {
      if (disposed) return REST_MOUTH;
      const now = performance.now();
      const dt = (now - previous) / 1000;
      previous = now;
      const audible = !audio.paused && !audio.ended && context.state === 'running';
      if (!audible) return motion.reset();
      analyser.getFloatTimeDomainData(pcm);
      analyser.getFloatFrequencyData(spectrum);
      const pose = motion.read(pcm, spectrum, context.sampleRate, dt);
      monitor.observe(now, speechRms(pcm, context.sampleRate), pose, true);
      return pose;
    },
    snapshot: () => ({ style, ...monitor.snapshot() }),
    dispose,
  };
}

export type PreviewAudioMeasurement = ReturnType<ReturnType<typeof createPreviewAudio>['snapshot']>;
