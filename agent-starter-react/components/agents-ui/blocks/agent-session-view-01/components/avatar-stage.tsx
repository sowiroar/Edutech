'use client';

import { useEffect, useRef } from 'react';
import dynamic from 'next/dynamic';
import { type RemoteAudioTrack } from 'livekit-client';
import { useRoomContext, useVoiceAssistant } from '@livekit/components-react';
import type { AvatarSample } from '@/components/avatar/browser-avatar-stage';
import { createLiveSpeech } from '@/components/avatar/live-speech';
import { createSpeechMonitor } from '@/components/avatar/speech-monitor';
import { type MouthPose, REST_MOUTH } from '@/components/avatar/speech-motion';
import type { BrowserAvatar } from '@/lib/browser-avatar';
import { useMediaTelemetry } from '@/lib/telemetry/context';

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
  const telemetry = useMediaTelemetry();
  const speech = useRef<() => MouthPose>(() => REST_MOUTH);
  const monitor = useRef(createSpeechMonitor());
  const reporting = useRef({
    since: performance.now(),
    sent: false,
    samples: [] as AvatarSample[],
  });
  const track = audioTrack?.publication.track;
  useEffect(() => {
    // The stage survives handoffs for visual continuity; measurements do not.
    reporting.current = { since: performance.now(), sent: false, samples: [] };
    monitor.current = createSpeechMonitor();
  }, [asset.sha256]);
  useEffect(() => {
    monitor.current = createSpeechMonitor();
    speech.current = () => REST_MOUTH;
    if (!track) return;
    let reader: ReturnType<typeof createLiveSpeech> | undefined;
    try {
      reader = createLiveSpeech(
        track as RemoteAudioTrack,
        () => room.canPlaybackAudio,
        (now, rms, pose, audible) => monitor.current.observe(now, rms, pose, audible)
      );
      speech.current = reader.read;
    } catch {
      /* Voice continues if the optional analyser cannot start. */
    }
    return () => {
      speech.current = () => REST_MOUTH;
      reader?.dispose();
    };
    // Model identity/rig does not own the audio stream. Keep the analyser alive
    // during LIRA -> NEXO -> ELIAN while resetting only per-model measurements.
  }, [track, room]);
  const sample = (value: AvatarSample) => {
    const report = reporting.current;
    report.samples.push(value);
    const now = performance.now();
    if (report.sent && now - report.since < 10_000) return;
    const samples = report.samples;
    telemetry?.avatarSample({
      character: asset.character,
      model_sha256: asset.sha256,
      measurement_scope: 'live-call-acoustic',
      window_ms: now - report.since,
      sample_count: samples.length,
      fps: samples.reduce((sum, s) => sum + s.fps, 0) / samples.length,
      fps_min: Math.min(...samples.map((s) => s.fps)),
      render_submission_ms:
        samples.reduce((sum, s) => sum + s.renderSubmissionMs, 0) / samples.length,
      first_frame_ms: value.firstFrameMs,
      model_bytes: value.modelBytes,
      texture_bytes_estimate: value.textureBytesEstimate,
      geometry_bytes: value.geometryDataBytes,
      page_js_heap_bytes: value.pageJsHeapBytes,
      triangles: value.triangles,
      draw_calls: value.drawCalls,
      width: value.width,
      height: value.height,
      resolution_scale: value.resolutionScale,
      mouth_available: value.mouthAnimationAvailable,
      lip_shapes_available: value.lipShapesAvailable,
      ...monitor.current.snapshot(),
    });
    report.sent = true;
    report.since = now;
    report.samples = [];
  };
  return (
    <BrowserAvatarStage
      asset={asset}
      compact={isChatOpen}
      speech={speech}
      onFailure={onFailure}
      onReady={onReady}
      onSample={sample}
    />
  );
}
