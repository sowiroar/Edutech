'use client';

import { useRef, useState } from 'react';
import { useTheme } from 'next-themes';
import { AnimatePresence, motion } from 'motion/react';
import { useSessionContext } from '@livekit/components-react';
import { AgentSessionView_01 } from '@/components/agents-ui/blocks/agent-session-view-01';
import { WelcomeView } from '@/components/app/welcome-view';
import { useAvatarStream } from '@/hooks/useAvatarStream';
import { startSessionAttempt } from '@/lib/session-start';

const MotionWelcomeView = motion.create(WelcomeView);
const MotionSessionView = motion.create(AgentSessionView_01);

const VIEW_MOTION_PROPS = {
  variants: {
    visible: {
      opacity: 1,
    },
    hidden: {
      opacity: 0,
    },
  },
  initial: 'hidden',
  animate: 'visible',
  exit: 'hidden',
  transition: {
    duration: 0.5,
    ease: 'linear' as const,
  },
};

export function ViewController() {
  const { isConnected, start, end, room } = useSessionContext();
  const { resolvedTheme } = useTheme();
  const avatar = useAvatarStream();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const starting = useRef(false);
  const begin = async () => {
    if (starting.current) return;
    starting.current = true;
    setPending(true);
    setError('');
    try {
      await startSessionAttempt({ room, start });
    } catch (error) {
      await end().catch(() => undefined);
      avatar.release();
      setError(error instanceof Error ? error.message : 'No se pudo conectar.');
    } finally {
      starting.current = false;
      setPending(false);
    }
  };

  return (
    <AnimatePresence mode="wait">
      {/* Welcome view */}
      {!isConnected && (
        <MotionWelcomeView
          key="welcome"
          {...VIEW_MOTION_PROPS}
          startButtonText="Iniciar llamada"
          onStartCall={begin}
          pending={pending}
          error={error}
        />
      )}
      {/* Session view */}
      {isConnected && (
        <MotionSessionView
          key="session-view"
          {...VIEW_MOTION_PROPS}
          supportsChatInput={true}
          supportsVideoInput={true}
          supportsScreenShare={true}
          isPreConnectBufferEnabled={true}
          themeMode={resolvedTheme === 'dark' ? 'dark' : 'light'}
          className="fixed inset-0"
        />
      )}
    </AnimatePresence>
  );
}
