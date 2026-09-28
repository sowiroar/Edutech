'use client';

import { useMemo } from 'react';
import { TokenSource } from 'livekit-client';
import { type UseSessionReturn, useSession } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react/dist/ssr';
import { AgentSessionProvider } from '@/components/agents-ui/agent-session-provider';
import { StartAudioButton } from '@/components/agents-ui/start-audio-button';
import { ViewController } from '@/components/app/view-controller';
import { Toaster } from '@/components/ui/sonner';
import { useAgentErrors } from '@/hooks/useAgentErrors';
import { AvatarStreamProvider, useAvatarStream } from '@/hooks/useAvatarStream';
import { useDebugMode } from '@/hooks/useDebug';

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
  const tokenSource = useMemo(() => TokenSource.endpoint('/api/token'), []);

  const session = useSession(tokenSource, { agentName });

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
