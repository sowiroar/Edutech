import { NextResponse } from 'next/server';
import { body, collector, rateLimit, sameOrigin, verify } from '@/lib/telemetry/server';

const allowed = new Set([
  'media_connect_started',
  'media_connected',
  'audio_playback_started',
  'video_first_frame',
  'media_stalled',
  'media_recovered',
  'presentation_changed',
  'avatar_unavailable',
  'media_quality_sample',
  'media_disconnected',
]);
export async function POST(req: Request) {
  if (!sameOrigin(req)) return NextResponse.json({ error: 'Origen no permitido' }, { status: 403 });
  try {
    const input = await body(req);
    const claims = await verify(input.context_token, 'viva-telemetry');
    const context = claims.context as Record<string, unknown>;
    if (!rateLimit('media:' + context.app_session_id, 120))
      return NextResponse.json({ error: 'Límite de eventos' }, { status: 429 });
    if (!Array.isArray(input.events) || !input.events.length || input.events.length > 10)
      throw new Error('Invalid batch');
    const events = input.events.map((event: Record<string, unknown>) => {
      if (!allowed.has(String(event.type))) throw new Error('Invalid type');
      // Context and producer are always reconstructed from the signed claims.
      const keys = [
        'event_id',
        'occurred_at',
        'type',
        'payload',
        'media_session_id',
        'connection_attempt_id',
      ];
      if (Object.keys(event).some((k) => !keys.includes(k))) throw new Error('Unknown field');
      return { ...context, ...event, source: 'browser', schema_version: 1 };
    });
    const res = await collector('/ingest', {
      method: 'POST',
      body: JSON.stringify({ context_token: input.context_token, events, media_only: true }),
    });
    return NextResponse.json(await res.json(), { status: res.status });
  } catch {
    return NextResponse.json({ error: 'Evento no autorizado o inválido' }, { status: 400 });
  }
}
