/** Presentation only: never rewrite persisted events or infer missing identities. */
export function describeEvent(
  event: Record<string, unknown> & { payload: Record<string, unknown> }
) {
  const voice = event.presentation_mode === 'voice';
  const message = event.type === 'conversation_message';
  const missingMeanings: Record<string, string> = {
    user_id:
      event.identity_source === 'visitor'
        ? 'Visitante sin autenticación institucional. anonymous_id distingue este navegador; no identifica a una persona.'
        : 'Identidad autenticada no reportada.',
    agent_id: message
      ? 'Este mensaje no identifica de forma fiable qué agente lo produjo. Consulta los cambios de agente; no se asigna por proximidad horaria.'
      : 'Agente no atribuido en este evento. No se reparte el consumo acumulado entre agentes sin evidencia.',
    avatar_id: voice
      ? 'No hay avatar visual en el modo voz.'
      : 'Avatar no identificado en este evento.',
    avatar_release: voice ? 'No aplica a esta sesión de voz.' : 'Versión del avatar no reportada.',
    turn_id: message
      ? 'El mensaje aún no está enlazado a un turno de respuesta. message_id identifica el mensaje, no el turno.'
      : 'Turno no correlacionado en este evento.',
    request_id: 'No se registró un identificador de solicitud del proveedor para este evento.',
    tool_call_id: message
      ? 'Este registro es un mensaje, no una ejecución de herramienta.'
      : 'Sin llamada de herramienta asociada a este evento.',
    span_id: message
      ? 'El mensaje se agrupa por trace_id de sesión; no tiene un tramo de operación instrumentado.'
      : 'No se registró un tramo de operación para este evento.',
    parent_span_id: 'No se registró un tramo padre. Una operación raíz tampoco necesita padre.',
    media_session_id:
      event.source === 'agent'
        ? 'El agente no recibe esta correlación del navegador. Se registra en los eventos de reproducción y conexión.'
        : 'Sesión de medios no reportada.',
    connection_attempt_id:
      event.source === 'agent'
        ? 'Este evento no está enlazado a un intento de conexión del navegador.'
        : 'Intento de conexión no reportado.',
  };
  const missing = Object.entries(event)
    .filter(([key, value]) => key !== 'payload' && (value === null || value === undefined))
    .map(([field]) => ({
      field,
      meaning: missingMeanings[field] || 'Dato no reportado para este evento.',
    }));
  const available = Object.fromEntries(
    Object.entries(event).filter(([, value]) => value !== null && value !== undefined)
  );
  // Keep payload nulls: unknown costs/latencies must never look like zero or disappear.
  available.payload = Object.fromEntries(
    Object.entries(event.payload).filter(([key]) => !message || key !== 'text')
  );
  return { available, missing };
}
