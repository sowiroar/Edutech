import type { MouthPose } from './speech-motion';

export type PlaybackStatus = 'active' | 'silent' | 'blocked' | 'unavailable';

/** Local acoustic-to-pose observations, NOT speaker/output or phoneme alignment. */
export function createSpeechMonitor() {
  let onset: number | null = null;
  let silence: number | null = null;
  let wasSpeech = false;
  let status: PlaybackStatus = 'unavailable';
  let frames = 0,
    speechFrames = 0,
    onsetCount = 0,
    closeCount = 0;
  let onsetMax: number | null = null,
    closeMax: number | null = null;
  return {
    observe(now: number, rms: number, pose: MouthPose, playback: boolean) {
      frames++;
      const moving = Math.max(pose.open, pose.round, pose.wide) >= 0.01;
      if (!playback) {
        status = 'blocked';
        onset = silence = null;
        wasSpeech = false;
        return;
      }
      const speaking = rms >= 0.005;
      status = speaking ? 'active' : 'silent';
      if (speaking) {
        speechFrames++;
        if (!wasSpeech) onset = now;
        silence = null;
        if (moving && onset !== null) {
          onsetMax = Math.max(onsetMax ?? 0, now - onset);
          onsetCount++;
          onset = null;
        }
      } else {
        if (wasSpeech) silence = now;
        onset = null;
        if (!moving && silence !== null) {
          closeMax = Math.max(closeMax ?? 0, now - silence);
          closeCount++;
          silence = null;
        }
      }
      wasSpeech = speaking;
    },
    snapshot() {
      const value = {
        playback_status: status,
        analysed_frames: frames,
        speech_frames: speechFrames,
        onset_observations: onsetCount,
        close_observations: closeCount,
        acoustic_onset_to_pose_max_ms: onsetMax,
        silence_to_rest_max_ms: closeMax,
      };
      frames = speechFrames = onsetCount = closeCount = 0;
      onsetMax = closeMax = null;
      return value;
    },
  };
}

/** The current app uses LiveKit's HTML media output; an analyser alone isn't playback. */
export function isTrackAudible(
  track: {
    isMuted: boolean;
    mediaStreamTrack: { readyState: string; enabled: boolean };
    attachedElements: Pick<
      HTMLMediaElement,
      'paused' | 'ended' | 'muted' | 'volume' | 'readyState'
    >[];
  },
  canPlayback: boolean,
  contextState: string
) {
  return (
    canPlayback &&
    contextState === 'running' &&
    !track.isMuted &&
    track.mediaStreamTrack.readyState === 'live' &&
    track.mediaStreamTrack.enabled &&
    track.attachedElements.some(
      (el) => !el.paused && !el.ended && !el.muted && el.volume > 0 && el.readyState >= 2
    )
  );
}
