import { NextResponse } from 'next/server';

// Estado del avatar de Unreal (NEXO) para el navegador.
//
// - AVATAR_BRIDGE_STATUS_URL: estado del puente VVA1, alcanzable desde este servidor.
// - AVATAR_STREAM_URL: página de Pixel Streaming de Unreal, alcanzable desde el navegador
//   (por ejemplo http://localhost:8080). Vacía = sin video del avatar en la web.
// - AVATAR_MUTE_AGENT_AUDIO: con Unreal conectado, silencia el audio de LiveKit y deja sonar
//   el que reproduce Unreal (evita el eco/doble voz cuando ambos suenan por los mismos
//   parlantes, con o sin Pixel Streaming). "false" mantiene siempre el audio de LiveKit.
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
  const streamUrl = process.env.AVATAR_STREAM_URL?.trim();
  const unrealConnected = await isUnrealConnected(statusUrl);

  return NextResponse.json(
    {
      // Unreal está reproduciendo el audio del agente ahora mismo (con o sin video en la web).
      unrealConnected,
      // Video de Pixel Streaming para mostrar en la web (solo si está configurado y conectado).
      videoUrl: unrealConnected && streamUrl ? streamUrl : undefined,
      muteAgentAudio: process.env.AVATAR_MUTE_AGENT_AUDIO !== 'false',
    },
    { headers: { 'Cache-Control': 'no-store' } }
  );
}
