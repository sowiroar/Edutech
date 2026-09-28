'use client';

import { type ReactNode, createContext, useContext, useEffect, useState } from 'react';

export interface AvatarStreamState {
  /** Unreal está conectado al puente y reproduciendo el audio del agente ahora mismo. */
  unrealConnected: boolean;
  /** Video de Pixel Streaming para mostrar (solo si está configurado y unrealConnected). */
  videoUrl?: string;
  /** Silenciar el audio de LiveKit mientras Unreal esté reproduciendo (evita doble voz). */
  muteAgentAudio: boolean;
}

const POLL_INTERVAL_MS = 3000;

const OFF: AvatarStreamState = { unrealConnected: false, muteAgentAudio: true };

const AvatarStreamContext = createContext<AvatarStreamState>(OFF);

async function fetchAvatarState(): Promise<AvatarStreamState> {
  try {
    const response = await fetch('/api/avatar', { cache: 'no-store' });
    if (!response.ok) {
      return OFF;
    }
    const data = await response.json();
    return {
      unrealConnected: data.unrealConnected === true,
      videoUrl: typeof data.videoUrl === 'string' ? data.videoUrl : undefined,
      muteAgentAudio: data.muteAgentAudio !== false,
    };
  } catch {
    return OFF;
  }
}

/**
 * Consulta cada pocos segundos si Unreal está conectado al puente del avatar. Sigue
 * consultando siempre: Unreal puede conectarse o desconectarse en cualquier momento.
 */
export function AvatarStreamProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AvatarStreamState>(OFF);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      const next = await fetchAvatarState();
      if (cancelled) {
        return;
      }
      setState((current) =>
        current.unrealConnected === next.unrealConnected &&
        current.videoUrl === next.videoUrl &&
        current.muteAgentAudio === next.muteAgentAudio
          ? current
          : next
      );
      timer = setTimeout(poll, POLL_INTERVAL_MS);
    };
    poll();

    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, []);

  return <AvatarStreamContext.Provider value={state}>{children}</AvatarStreamContext.Provider>;
}

export function useAvatarStream(): AvatarStreamState {
  return useContext(AvatarStreamContext);
}
