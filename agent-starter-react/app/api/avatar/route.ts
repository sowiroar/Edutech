import { NextResponse } from 'next/server';

// Estado del avatar de Unreal (NEXO/Familia VIVA) para el navegador.
//
// - AVATAR_BRIDGE_STATUS_URL: estado del puente VVA1, alcanzable desde este servidor.
// - AVATAR_STREAM_SOURCE_URL: dónde está el MJPEG de avatar-render dentro de la red de
//   Docker (ver avatar-render/README.md: comparte red con avatar-bridge, así que es
//   "http://avatar-bridge:8080/stream", no "http://avatar-render:..."). El navegador
//   nunca ve esta URL directamente: la pide a través de /api/avatar/stream (este
//   servidor la reenvía), igual que ya se hace con el estado del puente más abajo.
//   Reemplaza al Pixel Streaming de Unreal, que nunca llegó a verse en el navegador.
// - AVATAR_MUTE_AGENT_AUDIO: con Unreal conectado, silencia el audio de LiveKit y deja sonar
//   el que reproduce Unreal (evita el eco/doble voz cuando ambos suenan por los mismos
//   parlantes). "false" mantiene siempre el audio de LiveKit.
const STATUS_TIMEOUT_MS = 1500;

// no almacenar en caché: Unreal puede conectarse o caerse en cualquier momento
export const dynamic = 'force-dynamic';

async function isUnrealConnected(statusUrl: string): Promise<boolean> {
  try {
    const response = await fetch(statusUrl, {
      cache: 'no-store',
      signal: AbortSignal.timeout(STATUS_TIMEOUT_MS),
    });
    if (!response.ok) {
      return false;
    }
    const status = await response.json();
    return status?.unreal_connected === true;
  } catch {
    return false;
  }
}

export async function GET() {
  const statusUrl = process.env.AVATAR_BRIDGE_STATUS_URL || 'http://avatar-bridge:8766/status';
  // Solo hay algo que mostrar si avatar-render está configurado (la var de entorno de
  // su URL fuente existe); de lo contrario /api/avatar/stream no tiene nada que reenviar.
  const hasStreamSource = Boolean(process.env.AVATAR_STREAM_SOURCE_URL?.trim());
  const unrealConnected = await isUnrealConnected(statusUrl);

  return NextResponse.json(
    {
      // Unreal está reproduciendo el audio del agente ahora mismo (con o sin video en la web).
      unrealConnected,
      // Ruta propia (no la URL interna de Docker): el navegador la pide normal y este
      // servidor reenvía el MJPEG de avatar-render por dentro.
      videoUrl: unrealConnected && hasStreamSource ? '/api/avatar/stream' : undefined,
      muteAgentAudio: process.env.AVATAR_MUTE_AGENT_AUDIO !== 'false',
    },
    { headers: { 'Cache-Control': 'no-store' } }
  );
}
