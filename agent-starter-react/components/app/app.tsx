'use client';

import { useEffect, useMemo } from 'react';
import { Room, TokenSource } from 'livekit-client';
import { type UseSessionReturn, useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { AvatarStreamProvider, useAvatarStream } from '@/hooks/useAvatarStream';
import { useDebugMode } from '@/hooks/useDebug';
import { MediaTelemetry } from '@/lib/telemetry/client';

const IN_DEVELOPMENT = process.env.NODE_ENV !== 'production';

function AppSetup() {
  useDebugMode({ enabled: IN_DEVELOPMENT });
  useAgentErrors();

  return null;
}

/**
 * Sesión del agente. Con Unreal conectado, el audio lo emite Unreal (con los labios
 * sincronizados) y el de LiveKit se silencia para no oír la voz duplicada — con o sin
 * video de Pixel Streaming en la web.
 */
function AgentSession({
  session,
  children,
}: {
  session: UseSessionReturn;
  children: React.ReactNode;
}) {
  const avatar = useAvatarStream();

  return (
    <AgentSessionProvider session={session} muted={avatar.unrealConnected && avatar.muteAgentAudio}>
      {children}
    </AgentSessionProvider>
  );
}

interface AppProps {
  agentName?: string;
}

export function App({ agentName = 'nexus' }: AppProps) {
  const mediaTelemetry = useMemo(() => new MediaTelemetry(), []);
  const tokenSource = useMemo(
    () =>
      TokenSource.custom(async () => {
        mediaTelemetry.beginSession();
        const response = await fetch('/api/token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({}),
        });
        if (!response.ok) throw new Error('No se pudo iniciar la sesión');
        const data = await response.json();
        mediaTelemetry.setToken(data.telemetry?.token || '');
        return data;
      }),
    [mediaTelemetry]
  );

  // Room propio (en vez de dejar que useSession cree el suyo por defecto)
  // solo para poder pedir voiceIsolation además de lo que ya viene activado
  // por defecto en livekit-client (noiseSuppression, echoCancellation,
  // autoGainControl — se repiten explícitos para no depender de que ese
  // default no cambie). voiceIsolation es una supresión de ruido más fuerte
  // que noiseSuppression, estándar de WebRTC, gratis y local (corre en el
  // navegador); hoy solo la soportan navegadores basados en Chromium, en
  // los demás simplemente no aplica, sin error (Claude, 2026-10-08).
  const room = useMemo(
    () =>
      new Room({
        audioCaptureDefaults: {
          noiseSuppression: true,
          echoCancellation: true,
          autoGainControl: true,
          voiceIsolation: true,
        },
      }),
    []
  );

  useEffect(() => mediaTelemetry.attach(room), [mediaTelemetry, room]);
  const session = useSession(tokenSource, { agentName, room });

  return (
    <AvatarStreamProvider>
      <AgentSession session={session}>
        <AppSetup />
        <main className="grid h-svh grid-cols-1 place-content-center">
          <ViewController />
        </main>
        <StartAudioButton label="Start Audio" />
        <Toaster
          icons={{
            warning: <WarningIcon weight="bold" />,
          }}
          position="top-center"
          className="toaster group"
          style={
            {
              '--normal-bg': 'var(--popover)',
              '--normal-text': 'var(--popover-foreground)',
              '--normal-border': 'var(--border)',
            } as React.CSSProperties
          }
        />
      </AgentSession>
    </AvatarStreamProvider>
  );
}
