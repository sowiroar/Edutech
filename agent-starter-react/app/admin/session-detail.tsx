'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { describeEvent } from '@/lib/telemetry/event-detail';

type TraceEvent = {
  event_id: string;
  type: string;
  occurred_at: string;
  received_at: string;
  agent_id: string | null;
  source: string;
  turn_id: string | null;
  trace_id?: string;
  span_id?: string;
  parent_span_id?: string;
  tool_call_id?: string;
  payload: Record<string, unknown>;
};
type Detail = {
  items: TraceEvent[];
  next_cursor: string | null;
  transcript_capture: boolean;
  session: {
    started_at: string;
    ended_at: string | null;
    end_reason: string | null;
    context: { presentation_mode: string; release: string; environment: string };
  } | null;
  counts: { type: string; n: number }[];
};
const labels: Record<string, string> = {
  retrieval_completed: 'Fuentes recuperadas',
  session_started: 'Sesión iniciada',
  session_ended: 'Sesión cerrada',
  agent_changed: 'Agente asignado',
  response_started: 'Respuesta iniciada',
  response_completed: 'Respuesta completada',
  response_interrupted: 'Respuesta interrumpida',
  tool_started: 'Herramienta iniciada',
  tool_completed: 'Herramienta finalizada',
  operation_started: 'Operación iniciada',
  operation_completed: 'Operación finalizada',
  usage_recorded: 'Consumo reportado',
  error: 'Error',
  producer_health: 'Estado del registro',
  media_connect_started: 'Conexión iniciada',
  media_connected: 'Medio conectado',
  audio_playback_started: 'Primera reproducción',
  media_stalled: 'Conexión interrumpida',
  media_recovered: 'Conexión recuperada',
  media_disconnected: 'Medio desconectado',
  conversation_message: 'Mensaje de conversación',
  video_first_frame: 'Primer fotograma',
  avatar_unavailable: 'Avatar no disponible',
  presentation_changed: 'Presentación cambiada',
  media_quality_sample: 'Calidad del medio',
  avatar_quality_sample: 'Avatar y respuesta al audio',
};
const status: Record<string, string> = {
  ok: 'Correcto',
  error: 'Falló',
  cancelled: 'Cancelado',
  started: 'En curso',
  unknown: 'Sin confirmar',
};
const time = (value: string) => new Date(value).toLocaleTimeString('es-CO', { hour12: false });
function summary(e: TraceEvent) {
  const p = e.payload;
  if (e.type === 'avatar_quality_sample') {
    const numeric = (key: string, unit: string) =>
      typeof p[key] === 'number'
        ? `${new Intl.NumberFormat('es-CO', { maximumFractionDigits: 1 }).format(p[key] as number)} ${unit}`
        : 'Sin observación';
    return `${p.character} · ${numeric('fps', 'FPS')} · Cierre tras silencio: ${numeric('silence_to_rest_max_ms', 'ms')}`;
  }
  if (e.type === 'agent_changed')
    return p.previous_agent_id ? `${p.previous_agent_id} → ${p.agent_id}` : String(p.agent_id);
  if (e.type.startsWith('tool_') || e.type.startsWith('operation_'))
    return [
      p.name,
      p.purpose,
      status[String(p.status)] || p.status,
      typeof p.elapsed_ms === 'number' ? `${Math.round(p.elapsed_ms)} ms` : null,
    ]
      .filter(Boolean)
      .join(' · ');
  if (e.type === 'usage_recorded')
    return `${p.model} · ${p.purpose} · ${p.coverage_reason === 'complete' ? 'Uso desglosado' : 'Cobertura parcial'}`;
  if (e.type === 'retrieval_completed')
    return `${p.source_count} fuentes · ${p.result_available ? 'Resultado disponible' : 'Sin resultado'}`;
  if (e.type === 'error') return `${p.component} · ${p.code}`;
  if (e.type === 'session_ended') return `Motivo: ${p.reason}`;
  if (e.type === 'producer_health')
    return `${p.persisted} confirmados · ${p.dropped} descartados · ${p.queue_depth} pendientes`;
  return typeof p.elapsed_ms === 'number'
    ? `${Math.round(p.elapsed_ms)} ms`
    : e.agent_id || e.source;
}

export default function SessionDetail({ id, onClose }: { id: string; onClose: () => void }) {
  const [view, setView] = useState('conversation');
  const [data, setData] = useState<Detail | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const heading = useRef<HTMLHeadingElement>(null);
  const sequence = useRef(0);
  const load = useCallback(
    async (cursor?: string) => {
      const current = ++sequence.current;
      setBusy(true);
      setError('');
      try {
        const query = new URLSearchParams({ view, ...(cursor ? { cursor } : {}) });
        const response = await fetch(`/api/admin/sessions/${id}/events?${query}`, {
          cache: 'no-store',
        });
        if (!response.ok)
          throw new Error(
            response.status === 401
              ? 'Tu acceso expiró. Actualiza la página para volver a entrar.'
              : 'No se pudo cargar esta sesión. Reintenta la consulta.'
          );
        const result: Detail = await response.json();
        if (current !== sequence.current) return;
        setData((old) => ({
          ...result,
          items: cursor ? [...(old?.items || []), ...result.items] : result.items,
        }));
      } catch (e) {
        if (current === sequence.current)
          setError(e instanceof Error ? e.message : 'No se pudo cargar.');
      } finally {
        if (current === sequence.current) setBusy(false);
      }
    },
    [id, view]
  );
  useEffect(() => {
    setData(null);
    void load();
    return () => {
      // This is a request generation counter, not a DOM ref.
      // eslint-disable-next-line react-hooks/exhaustive-deps
      sequence.current++;
    };
  }, [load]);
  useEffect(() => {
    heading.current?.focus();
    heading.current?.scrollIntoView({ block: 'start' });
  }, [id]);
  const items = [...(data?.items || [])].sort(
    (a, b) => a.occurred_at.localeCompare(b.occurred_at) || a.event_id.localeCompare(b.event_id)
  );
  return (
    <section className="telemetry-detail" aria-labelledby="session-detail-title" aria-busy={busy}>
      <div className="telemetry-section-heading">
        <div>
          <h2 id="session-detail-title" ref={heading} tabIndex={-1}>
            Detalle de sesión <code>{id.slice(0, 8)}</code>
          </h2>
          <p>Conversación y actividad registrada en una misma línea de tiempo.</p>
        </div>
        <button onClick={onClose}>Cerrar detalle</button>
      </div>
      {data?.session && (
        <div className="telemetry-session-meta">
          <span>{new Date(data.session.started_at).toLocaleString('es-CO')}</span>
          <span>
            {data.session.context.environment} ·{' '}
            {data.session.context.presentation_mode === 'voice' ? 'Voz' : 'Avatar'}
          </span>
          <span>{data.session.ended_at ? 'Cerrada' : 'Activa'}</span>
          <span>
            Versión{' '}
            <code>
              {data.session.context.release === 'unknown'
                ? 'No registrada'
                : data.session.context.release}
            </code>
          </span>
        </div>
      )}
      <div className="telemetry-detail-nav" aria-label="Vista de la sesión">
        {[
          ['conversation', 'Conversación'],
          ['actions', 'Herramientas y acciones'],
          ['all', 'Todos los eventos'],
        ].map(([key, label]) => (
          <button key={key} aria-pressed={view === key} onClick={() => setView(key)}>
            {label}
          </button>
        ))}
        <button disabled={busy} onClick={() => load()}>
          Actualizar sesión
        </button>
      </div>
      {error && (
        <p className="telemetry-error" role="alert">
          {error} <button onClick={() => load()}>Reintentar</button>
        </p>
      )}
      {busy && <p role="status">Cargando eventos…</p>}
      {!busy && !error && data && !data.session && (
        <p className="telemetry-empty">Esta sesión no existe o ya no está disponible.</p>
      )}
      {view === 'conversation' && data?.session && (
        <p className="telemetry-caption">
          {data.transcript_capture
            ? 'Texto del historial del agente, con ocultación básica de identificadores. Sin audio guardado. No certifica lo que el usuario alcanzó a escuchar.'
            : 'Esta sesión no tenía activada la transcripción. Su texto no se guardó y no se puede reconstruir. Puedes consultar sus herramientas y eventos técnicos.'}
        </p>
      )}
      {data?.next_cursor && (
        <button disabled={busy} onClick={() => load(data.next_cursor!)}>
          Cargar eventos anteriores
        </button>
      )}
      {!busy && !error && data?.session && !items.length && (
        <p className="telemetry-empty">
          {view === 'conversation'
            ? 'No hay mensajes guardados en esta sesión.'
            : 'No hay eventos de este tipo en esta sesión.'}
        </p>
      )}
      <ol
        className="telemetry-timeline"
        aria-label={view === 'conversation' ? 'Transcripción' : 'Traza de eventos'}
      >
        {items.map((e) => (
          <li
            key={e.event_id}
            className={e.type === 'conversation_message' ? 'telemetry-message' : ''}
          >
            <time dateTime={e.occurred_at}>{time(e.occurred_at)}</time>
            <div>
              <div className="telemetry-event-heading">
                <strong>
                  {e.type === 'conversation_message'
                    ? e.payload.role === 'user'
                      ? 'Usuario'
                      : 'Asistente'
                    : e.type === 'agent_changed' && e.payload.previous_agent_id
                      ? 'Cambio de agente'
                      : labels[e.type] || e.type}
                </strong>
                {e.agent_id && <span>{e.agent_id}</span>}
                {(e.payload.status === 'error' || e.type === 'error') && (
                  <span className="telemetry-status-error">Error</span>
                )}
              </div>
              {e.type === 'conversation_message' ? (
                <>
                  <p className="telemetry-transcript">
                    {typeof e.payload.text === 'string'
                      ? e.payload.text
                      : 'Texto retirado por retención o no disponible.'}
                  </p>
                  {e.payload.interrupted === true && (
                    <small>Mensaje interrumpido; puede estar incompleto.</small>
                  )}
                  {e.payload.truncated === true && (
                    <small>Texto limitado a 4.000 caracteres.</small>
                  )}
                </>
              ) : (
                <p>{summary(e)}</p>
              )}
              {e.type === 'avatar_quality_sample' && (
                <p className="telemetry-caption">
                  Respuesta acústica de la animación, medida en el navegador durante la llamada. No
                  mide sincronía de fonemas ni retardo de los altavoces. El cierre es el máximo
                  observado en esta ventana; sin transición a silencio no hay valor. Memoria de
                  texturas estimada y heap JavaScript no equivalen a RAM o VRAM total. Modelo:{' '}
                  <code>{String(e.payload.model_sha256).slice(0, 12)}</code>.
                </p>
              )}
              <details>
                <summary>Detalle técnico</summary>
                <p className="telemetry-caption">
                  Campos disponibles del evento. Los datos ausentes se explican debajo; no equivalen
                  a cero ni a un fallo de la conversación.
                  {e.type === 'conversation_message' &&
                    ' El texto se muestra arriba y no se repite en el JSON.'}
                </p>
                {(e as TraceEvent & { release?: string }).release === 'unknown' && (
                  <p>
                    Versión no registrada al iniciar esta sesión. No se puede atribuir
                    retrospectivamente al código actual.
                  </p>
                )}
                <pre>{JSON.stringify(describeEvent(e).available, null, 2)}</pre>
                {!!describeEvent(e).missing.length && (
                  <details>
                    <summary>
                      Campos sin dato y su significado ({describeEvent(e).missing.length})
                    </summary>
                    <dl>
                      {describeEvent(e).missing.map(({ field, meaning }) => (
                        <div key={field}>
                          <dt>
                            <code>{field}</code>
                          </dt>
                          <dd>{meaning}</dd>
                        </div>
                      ))}
                    </dl>
                  </details>
                )}
              </details>
            </div>
          </li>
        ))}
      </ol>
      <p className="telemetry-caption">
        Orden por hora del productor; puede variar entre equipos. {items.length} eventos cargados
        {data?.next_cursor ? '; hay anteriores por consultar' : ''}.
      </p>
    </section>
  );
}
