'use client';

import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import SessionDetail from './session-detail';
import './telemetry.css';

type Usage = {
  provider: string;
  model: string;
  purpose: string;
  unit: string;
  direction: string;
  modality: string;
  cached: boolean;
  quantity: number;
  known_cost_usd: number | null;
  entries: number;
  priced_entries: number;
};
type Metrics = {
  summary: { sessions: number; active: number; expired: number; visitors: number };
  usage: Usage[];
  event_counts: { type: string; n: number }[];
  latencies: {
    metric: string;
    n: number;
    eligible: number;
    coverage_basis: string;
    p50: number | null;
    p95: number | null;
    excluded_events?: number;
  }[];
  known_cost_usd: number | null;
  unmetered_operations: number;
  operations: {
    type: string;
    name: string;
    purpose: string | null;
    calls: number;
    ok: number;
    errors: number;
    cancelled: number;
    timed: number;
    p50: number | null;
    p95: number | null;
  }[];
  quality: {
    sessions_with_errors: number;
    handoffs: number;
    interrupted: number;
    finished_responses: number;
    incomplete_usage_reports: number;
    retrieval_without_result: number;
  };
  producers: {
    session_id: string;
    occurred_at: string;
    payload: { dropped: number; write_failed: number; queue_depth: number };
  }[];
};
type Session = {
  id: string;
  context: {
    presentation_mode: string;
    environment: string;
    anonymous_id: string;
    release: string;
  };
  started_at: string;
  ended_at: string | null;
  end_reason: string | null;
};
const number = new Intl.NumberFormat('es-CO', { maximumFractionDigits: 2 });
const money = (v: number | null) =>
  v === null
    ? 'Sin dato'
    : new Intl.NumberFormat('es-CO', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 6,
      }).format(v);
const date = (v: string) => new Date(v).toLocaleString('es-CO');
const initialDate = (hours: number) => {
  const d = new Date(Date.now() - hours * 3600000);
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
};
const latencyLabels: Record<string, string> = {
  server_speech_handle_duration_ms: 'Duración de respuesta en servidor',
  server_response_start_ms: 'Inicio de respuesta en servidor',
  browser_first_audio_ms: 'Conexión → primera reproducción',
};

export default function Admin() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [from, setFrom] = useState(() => initialDate(24));
  const [to, setTo] = useState(() => initialDate(-1));
  const [environment, setEnvironment] = useState('local');
  const [mode, setMode] = useState('');
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [cursor, setCursor] = useState<string | null>(null);
  const [health, setHealth] = useState<{ ready: boolean; write_failed: number } | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [updated, setUpdated] = useState<string | null>(null);
  const query = useCallback(
    () =>
      new URLSearchParams({
        from: new Date(from).toISOString(),
        to: new Date(to).toISOString(),
        environment,
        mode,
      }).toString(),
    [from, to, environment, mode]
  );
  const requestSequence = useRef(0);
  const initialized = useRef(false);
  const [appliedQuery, setAppliedQuery] = useState('');
  const request = async (path: string) => {
    const sequence = requestSequence.current;
    const response = await fetch('/api/admin/' + path, { cache: 'no-store' });
    if (response.status === 401) {
      if (sequence === requestSequence.current) setAuthenticated(false);
      throw new Error('');
    }
    if (!response.ok)
      throw new Error(
        'No se pudieron consultar las métricas. Revisa el servicio de telemetría y vuelve a actualizar.'
      );
    return response.json();
  };
  const load = useCallback(async () => {
    const sequence = ++requestSequence.current;
    setBusy(true);
    setError('');
    try {
      const q = query();
      const [m, s, h] = await Promise.all([
        request('metrics?' + q),
        request('sessions?' + q),
        request('health'),
      ]);
      if (sequence !== requestSequence.current) return;
      setAuthenticated(true);
      setAppliedQuery(q);
      setMetrics(m);
      setSessions(s.items);
      setCursor(s.next_cursor);
      setHealth(h);
      setUpdated(new Date().toISOString());
      setSelected(null);
    } catch (e) {
      if (sequence === requestSequence.current)
        setError(e instanceof Error ? e.message : 'No se pudo actualizar');
    } finally {
      if (sequence === requestSequence.current) setBusy(false);
    }
  }, [query]);
  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      void load();
    }
  }, [load]);
  // Explicit refresh avoids silently replacing a session being inspected.
  async function login(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const r = await fetch('/api/admin/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });
      if (!r.ok) {
        const d = await r.json();
        throw new Error(d.error);
      }
      setPassword('');
      setAuthenticated(true);
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'No se pudo iniciar sesión');
    } finally {
      setBusy(false);
    }
  }
  async function logout() {
    requestSequence.current++;
    await fetch('/api/admin/logout', { method: 'POST' });
    setAuthenticated(false);
    setMetrics(null);
    setSessions([]);

    setSelected(null);
    setHealth(null);
    setBusy(false);
    setError('');
  }
  const priced = metrics?.usage.reduce((n, u) => n + u.priced_entries, 0) || 0;
  const total = metrics?.usage.reduce((n, u) => n + u.entries, 0) || 0;
  return (
    <main className="telemetry-page" lang="es">
      <header className="telemetry-header">
        <div>
          <h1>Telemetría VIVA</h1>
          <p>Uso, rendimiento y trazabilidad de las conversaciones.</p>
        </div>
        <nav aria-label="Navegación de telemetría">
          <Link href="/">Volver a voz</Link>
          {authenticated && <button onClick={logout}>Cerrar sesión</button>}
        </nav>
      </header>
      {error && (
        <p className="telemetry-error" role="alert">
          {error}
          {authenticated === null && (
            <button disabled={busy} onClick={load}>
              Reintentar consulta
            </button>
          )}
        </p>
      )}
      {authenticated === null && !error && <p role="status">Comprobando acceso…</p>}
      {authenticated === false && (
        <form className="telemetry-login" onSubmit={login}>
          <h2>Acceso del equipo</h2>
          <p>
            Panel privado de operación. Usa la contraseña administrativa configurada para este
            entorno.
          </p>
          <label htmlFor="admin-password">Contraseña</label>
          <input
            id="admin-password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          <button className="primary" disabled={busy}>
            {busy ? 'Verificando…' : 'Entrar al panel'}
          </button>
        </form>
      )}
      {authenticated && (
        <>
          <section aria-label="Filtros" className="telemetry-filters">
            <label>
              Desde
              <input type="datetime-local" value={from} onChange={(e) => setFrom(e.target.value)} />
            </label>
            <label>
              Hasta
              <input type="datetime-local" value={to} onChange={(e) => setTo(e.target.value)} />
            </label>
            <label>
              Entorno
              <select value={environment} onChange={(e) => setEnvironment(e.target.value)}>
                <option value="local">Desarrollo local</option>
                <option value="test">Pruebas sintéticas</option>
                <option value="uam-demo">UAM · demo</option>
                <option value="production">Producción</option>
              </select>
            </label>
            <label>
              Presentación
              <select value={mode} onChange={(e) => setMode(e.target.value)}>
                <option value="">Todas</option>
                <option value="voice">Voz</option>
                <option value="avatar">Avatar</option>
              </select>
            </label>
            <button onClick={load} disabled={busy}>
              {busy ? 'Actualizando…' : 'Actualizar'}
            </button>
          </section>
          <p className="telemetry-caption" role="status">
            {appliedQuery &&
              (() => {
                try {
                  return query() !== appliedQuery;
                } catch {
                  return true;
                }
              })() && <strong>Hay filtros sin aplicar. Pulsa Actualizar. </strong>}
            {appliedQuery && (
              <span>
                Consulta aplicada: {new URLSearchParams(appliedQuery).get('environment')} ·{' '}
                {new URLSearchParams(appliedQuery).get('mode') || 'todos los modos'}.{' '}
              </span>
            )}
            {updated ? 'Actualizado ' + date(updated) : 'Sin consulta completada'} · Sesiones
            iniciadas en el periodo seleccionado. Máximo 90 días.
          </p>
          {selected && (
            <SessionDetail
              key={selected}
              id={selected}
              onClose={() => {
                const id = selected;
                setSelected(null);
                requestAnimationFrame(() => document.getElementById('session-' + id)?.focus());
              }}
            />
          )}
          {metrics && (
            <>
              <nav className="telemetry-section-nav" aria-label="Secciones del panel">
                <a href="#overview">Resumen</a>
                <a href="#sessions">Sesiones</a>
                <a href="#operations">Herramientas</a>
                <a href="#cost">Consumo</a>
                <a href="#latency">Tiempos</a>
                <a href="#health">Salud</a>
              </nav>
              <section className="telemetry-overview" aria-labelledby="overview">
                <h2 id="overview">Actividad del periodo</h2>
                <dl>
                  <div>
                    <dt>Sesiones</dt>
                    <dd>{metrics.summary.sessions}</dd>
                  </div>
                  <div>
                    <dt>Visitantes anónimos</dt>
                    <dd>{metrics.summary.visitors}</dd>
                  </div>
                  <div>
                    <dt>Activas</dt>
                    <dd>{metrics.summary.active}</dd>
                  </div>
                  <div>
                    <dt>Cierre por inactividad</dt>
                    <dd>{metrics.summary.expired}</dd>
                  </div>
                  <div>
                    <dt>Errores reportados</dt>
                    <dd>{metrics.event_counts.find((e) => e.type === 'error')?.n || 0}</dd>
                  </div>
                </dl>
              </section>
              <section aria-labelledby="sessions">
                <h2 id="sessions">Sesiones</h2>
                <p>
                  Revisa la conversación, las herramientas ejecutadas y los errores. El texto solo
                  está disponible en sesiones con captura activada; no se guarda audio.
                </p>
                <div
                  className="telemetry-table"
                  tabIndex={0}
                  role="region"
                  aria-label="Tabla desplazable"
                >
                  <table>
                    <thead>
                      <tr>
                        <th>Inicio</th>
                        <th>Sesión</th>
                        <th>Modo</th>
                        <th>Estado</th>
                        <th>Acción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {sessions.map((s) => (
                        <tr key={s.id}>
                          <td>{date(s.started_at)}</td>
                          <td>
                            <code title={s.id}>{s.id.slice(0, 8)}</code>
                          </td>
                          <td>{s.context.presentation_mode === 'voice' ? 'Voz' : 'Avatar'}</td>
                          <td>
                            <span className={'telemetry-status ' + (!s.ended_at ? 'active' : '')}>
                              {s.ended_at
                                ? {
                                    shutdown: 'Cerrada',
                                    expired: 'Sin cierre confirmado',
                                    completed: 'Completada',
                                    participant_left: 'Usuario salió',
                                    error: 'Error',
                                    unknown: 'Sin confirmar',
                                  }[s.end_reason || 'unknown'] || s.end_reason
                                : 'Activa'}
                            </span>
                          </td>
                          <td>
                            <button
                              id={'session-' + s.id}
                              aria-expanded={selected === s.id}
                              disabled={busy}
                              onClick={() => setSelected(s.id)}
                              aria-label={'Ver eventos de sesión ' + s.id.slice(0, 8)}
                            >
                              Ver eventos
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!sessions.length && (
                    <p className="telemetry-empty">No hay sesiones para estos filtros.</p>
                  )}
                </div>
                {cursor && (
                  <button
                    disabled={busy}
                    onClick={async () => {
                      const sequence = requestSequence.current;
                      setBusy(true);
                      try {
                        const d = await request('sessions?' + appliedQuery + '&cursor=' + cursor);
                        if (sequence !== requestSequence.current) return;
                        setSessions((v) => [...v, ...d.items]);
                        setCursor(d.next_cursor);
                      } catch {
                        if (sequence === requestSequence.current)
                          setError('No se pudieron cargar más sesiones.');
                      } finally {
                        if (sequence === requestSequence.current) setBusy(false);
                      }
                    }}
                  >
                    Cargar más sesiones
                  </button>
                )}
              </section>
              <section aria-labelledby="operations">
                <h2 id="operations">Herramientas y operaciones</h2>
                <p>
                  Resultado y tiempo de cada ejecución. RAG y memoria se miden por separado de la
                  herramienta que los invoca.
                </p>
                <dl className="telemetry-quality">
                  <div>
                    <dt>Cambios de agente</dt>
                    <dd>{metrics.quality?.handoffs ?? 'Sin dato'}</dd>
                  </div>
                  <div>
                    <dt>Respuestas interrumpidas</dt>
                    <dd>
                      {metrics.quality?.interrupted ?? 'Sin dato'} /{' '}
                      {metrics.quality?.finished_responses ?? '—'}
                    </dd>
                  </div>
                  <div>
                    <dt>Sesiones con errores</dt>
                    <dd>
                      {metrics.quality?.sessions_with_errors ?? 'Sin dato'} /{' '}
                      {metrics.summary.sessions}
                    </dd>
                  </div>
                </dl>
                <div
                  className="telemetry-table"
                  tabIndex={0}
                  role="region"
                  aria-label="Resultados de herramientas"
                >
                  <table>
                    <thead>
                      <tr>
                        <th>Herramienta / operación</th>
                        <th>Ejecuciones</th>
                        <th>Correctas</th>
                        <th>Fallidas</th>
                        <th>Canceladas</th>
                        <th>p50 / p95</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.operations?.map((o) => (
                        <tr key={o.type + o.name + o.purpose}>
                          <td>
                            {o.name}
                            <small>{o.purpose || 'Herramienta'}</small>
                          </td>
                          <td>{o.calls}</td>
                          <td>{o.ok}</td>
                          <td>{o.errors}</td>
                          <td>{o.cancelled}</td>
                          <td>
                            {o.p50 === null ? 'Sin dato' : number.format(o.p50) + ' ms'} /{' '}
                            {o.p95 === null ? 'Sin dato' : number.format(o.p95) + ' ms'}
                            <small>
                              {o.timed} de {o.calls} con tiempo
                            </small>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!metrics.operations?.length && (
                    <p className="telemetry-empty">
                      No hay herramientas u operaciones finalizadas en este periodo.
                    </p>
                  )}
                </div>
              </section>
              <section aria-labelledby="cost">
                <div className="telemetry-section-heading">
                  <h2 id="cost">Consumo y costo estimado</h2>
                  <strong>{money(metrics.known_cost_usd)}</strong>
                </div>
                <p>
                  Tarifa estándar publicada, no factura. {priced} de {total} registros de uso tienen
                  tarifa. {metrics.unmetered_operations} operaciones de RAG o memoria no exponen
                  consumo; su costo es desconocido. Infraestructura, GPU e impuestos no incluidos.{' '}
                  {metrics.quality?.incomplete_usage_reports ?? 0} reportes de uso tienen cobertura
                  incompleta.
                </p>
                <div
                  className="telemetry-table"
                  tabIndex={0}
                  role="region"
                  aria-label="Tabla desplazable"
                >
                  <table>
                    <caption className="sr-only">
                      Uso reportado por modelo, propósito y modalidad
                    </caption>
                    <thead>
                      <tr>
                        <th>Modelo / proveedor</th>
                        <th>Propósito</th>
                        <th>Modalidad</th>
                        <th>Consumo</th>
                        <th>Costo conocido</th>
                        <th>Cobertura</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.usage.map((u, i) => (
                        <tr key={i}>
                          <td>
                            {u.model}
                            <small>{u.provider}</small>
                          </td>
                          <td>{u.purpose}</td>
                          <td>
                            {u.direction === 'input' ? 'Entrada' : 'Salida'} · {u.modality}
                            {u.cached ? ' · caché' : ''}
                          </td>
                          <td className="numeric">
                            {number.format(u.quantity)} {u.unit}
                          </td>
                          <td className="numeric">{money(u.known_cost_usd)}</td>
                          <td>
                            {u.priced_entries}/{u.entries}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {!metrics.usage.length && (
                    <p className="telemetry-empty">
                      Aún no hay consumo reportado en este periodo. Inicia una conversación y
                      actualiza al terminar.
                    </p>
                  )}
                </div>
              </section>
              <section aria-labelledby="latency">
                <h2 id="latency">Tiempos medidos</h2>
                <p>
                  Reloj de cada productor. La duración del servidor no demuestra reproducción ni
                  sincronía labial. Latencia de turno a reproducción: pendiente de marcadores
                  compartidos.
                </p>
                <div
                  className="telemetry-table"
                  tabIndex={0}
                  role="region"
                  aria-label="Tabla desplazable"
                >
                  <table>
                    <thead>
                      <tr>
                        <th>Medición</th>
                        <th>Muestras</th>
                        <th>Cobertura</th>
                        <th>p50</th>
                        <th>p95</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.latencies.map((l) => (
                        <tr key={l.metric}>
                          <td>{latencyLabels[l.metric] || l.metric}</td>
                          <td>{l.n}</td>
                          <td>
                            {l.eligible == null
                              ? 'Cobertura no disponible'
                              : `${l.n} / ${l.eligible}`}
                            <small>
                              {l.coverage_basis === 'connection_attempts'
                                ? 'Intentos de conexión registrados'
                                : 'Eventos de respuesta registrados'}
                            </small>
                            {!!l.excluded_events && (
                              <small>
                                {l.excluded_events} eventos sin emparejar o duplicados, excluidos.
                              </small>
                            )}
                          </td>
                          <td>{l.p50 === null ? 'Sin dato' : number.format(l.p50) + ' ms'}</td>
                          <td>{l.p95 === null ? 'Sin dato' : number.format(l.p95) + ' ms'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <footer className="telemetry-footer">
                <h2 id="health">Salud del registro</h2>
                <p>
                  {health?.ready ? 'Almacenamiento disponible' : 'Almacenamiento sin confirmar'} ·{' '}
                  {health?.write_failed ?? 'Sin dato'} fallos de escritura desde el inicio del
                  colector.
                </p>
                <p>
                  Último reporte por productor:{' '}
                  {metrics.producers?.reduce((n, row) => n + row.payload.dropped, 0) ?? 'Sin dato'}{' '}
                  eventos descartados,{' '}
                  {metrics.producers?.reduce((n, row) => n + row.payload.write_failed, 0) ??
                    'Sin dato'}{' '}
                  intentos de escritura fallidos. Cobertura: {metrics.producers?.length || 0} de{' '}
                  {metrics.summary.sessions} sesiones.
                </p>
                <p>
                  La cola del agente es acotada. Consulta los eventos <code>producer_health</code> y
                  sus logs para detectar descartes, incluso cuando PostgreSQL no responde. Un panel
                  vacío no significa consumo cero.
                </p>
              </footer>
            </>
          )}
        </>
      )}
    </main>
  );
}
