import { ConnectionState, Room, RoomEvent } from 'livekit-client';

/** Best-effort media events. No audio buffers, transcripts or credentials persisted. */
export class MediaTelemetry {
  private token = '';
  private attempt = '';
  private media = '';
  private started = 0;
  private firstAudio = false;
  private pending: Record<string, unknown>[] = [];
  private timer: ReturnType<typeof setTimeout> | null = null;
  private sending = false;
  private failures = 0;
  private closed = false;
  private generation = 0;
  beginSession() {
    this.generation++;
    this.token = '';
    this.pending = [];
    this.failures = 0;
    this.startAttempt();
  }
  private startAttempt() {
    this.attempt = crypto.randomUUID();
    this.media = crypto.randomUUID();
    this.started = performance.now();
    this.firstAudio = false;
    this.emit('media_connect_started', { reason: 'connecting' });
  }
  setToken(token: string) {
    this.token = token;
    if (this.pending.length) this.schedule();
  }
  private emit(type: string, payload: Record<string, unknown> = {}) {
    if (!this.attempt || this.closed || this.pending.length >= 50) return;
    this.pending.push({
      event_id: crypto.randomUUID(),
      occurred_at: new Date().toISOString(),
      type,
      payload,
      media_session_id: this.media,
      connection_attempt_id: this.attempt,
    });
    this.schedule();
  }
  private schedule() {
    if (!this.timer && !this.closed)
      this.timer = setTimeout(() => {
        this.timer = null;
        void this.flush();
      }, 1000);
  }
  private async flush() {
    if (this.sending || !this.token || !this.pending.length || this.closed) return;
    this.sending = true;
    const batch = this.pending.slice(0, 10);
    const generation = this.generation;
    try {
      const response = await fetch('/api/telemetry/media', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context_token: this.token, events: batch }),
        signal: AbortSignal.timeout(4000),
        keepalive: true,
      });
      if (generation !== this.generation) return;
      if (response.ok) {
        this.pending.splice(0, batch.length);
        this.failures = 0;
      } else if (![409, 503].includes(response.status) || ++this.failures >= 6) {
        this.pending.splice(0, batch.length);
        this.failures = 0;
      }
    } catch {
      if (generation !== this.generation) return;
      if (++this.failures >= 6) {
        this.pending.splice(0, batch.length);
        this.failures = 0;
      }
    } finally {
      this.sending = false;
      if (this.pending.length) this.schedule();
    }
  }
  attach(room: Room) {
    this.closed = false;
    const state = (value: ConnectionState) => {
      if (value === ConnectionState.Connecting && !this.attempt) this.startAttempt();
      if (value === ConnectionState.Connected)
        this.emit('media_connected', {
          elapsed_ms: performance.now() - this.started,
          reason: 'connected',
        });
      if (value === ConnectionState.Reconnecting)
        this.emit('media_stalled', { reason: 'reconnecting' });
      if (value === ConnectionState.Disconnected)
        this.emit('media_disconnected', { reason: 'disconnected' });
    };
    const recovered = () => this.emit('media_recovered', { reason: 'connected' });
    const playing = (event: Event) => {
      const audio = event.target;
      if (
        audio instanceof HTMLAudioElement &&
        !audio.muted &&
        audio.volume > 0 &&
        !this.firstAudio &&
        room.state === ConnectionState.Connected &&
        Array.from(room.remoteParticipants.values()).some(
          (participant) =>
            participant.isAgent &&
            Array.from(participant.audioTrackPublications.values()).some((publication) =>
              publication.track?.attachedElements.includes(audio)
            )
        )
      ) {
        this.firstAudio = true;
        this.emit('audio_playback_started', {
          elapsed_ms: performance.now() - this.started,
          reason: 'playing',
        });
      }
    };
    room.on(RoomEvent.ConnectionStateChanged, state);
    room.on(RoomEvent.Reconnected, recovered);
    document.addEventListener('playing', playing, true);
    return () => {
      room.off(RoomEvent.ConnectionStateChanged, state);
      room.off(RoomEvent.Reconnected, recovered);
      document.removeEventListener('playing', playing, true);
      if (this.timer) clearTimeout(this.timer);
      this.timer = null;
      this.closed = true;
    };
  }
}
