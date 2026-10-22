'use client';

import { useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { type RemoteAudioTrack, createAudioAnalyser } from 'livekit-client';
import { useRoomContext, useVoiceAssistant } from '@livekit/components-react';
import { type MouthPose, REST_MOUTH, createSpeechMotion } from '@/components/avatar/speech-motion';
import type { BrowserAvatar } from '@/lib/browser-avatar';

const BrowserAvatarStage = dynamic(() => import('@/components/avatar/browser-avatar-stage'), {
  ssr: false,
});

export function AvatarStage({
  asset,
  isChatOpen,
  onFailure,
  onReady,
}: {
  asset: BrowserAvatar;
  isChatOpen: boolean;
  onFailure: () => void;
  onReady: () => void;
}) {
  const { audioTrack } = useVoiceAssistant();
  const room = useRoomContext();
  const speech = useRef<() => MouthPose>(() => REST_MOUTH);
  const track = audioTrack?.publication.track;
  useEffect(() => {
    if (!track || (!asset.mouthMorph && !asset.rigProfile)) return;
    // Analyse already received audio; LiveKit remains the only audio output.
    let analyser: ReturnType<typeof createAudioAnalyser> | undefined;
    try {
      analyser = createAudioAnalyser(track as RemoteAudioTrack, {
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
      void (node.context as AudioContext).resume().catch(() => {});
      speech.current = () => {
        const now = performance.now();
        const dt = (now - previous) / 1000;
        previous = now;
        if (!room.canPlaybackAudio || track.isMuted || node.context.state !== 'running')
          return motion.reset();
        node.getFloatTimeDomainData(pcm);
        node.getFloatFrequencyData(spectrum);
        return motion.read(pcm, spectrum, node.context.sampleRate, dt);
      };
    } catch {
      /* Voice continues if the optional analyser cannot start. */
    }
    return () => {
      speech.current = () => REST_MOUTH;
      if (analyser) void analyser.cleanup();
    };
  }, [track, asset.mouthMorph, asset.rigProfile, room]);
  return (
    <BrowserAvatarStage
      asset={asset}
      compact={isChatOpen}
      speech={speech}
      onFailure={onFailure}
      onReady={onReady}
    />
  );
}
