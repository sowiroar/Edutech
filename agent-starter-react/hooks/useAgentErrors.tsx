import { ReactNode, useEffect, useRef } from 'react';
import { toast as sonnerToast } from 'sonner';
import { useAgent, useSessionContext } from '@livekit/components-react';
import { WarningIcon } from '@phosphor-icons/react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';

interface ToastProps {
  title: ReactNode;
  description: ReactNode;
}

function toastAlert(toast: ToastProps) {
  const { title, description } = toast;

  return sonnerToast.custom(
    (id) => (
      <Alert onClick={() => sonnerToast.dismiss(id)} className="bg-accent w-full md:w-[364px]">
        <WarningIcon weight="bold" />
        <AlertTitle>{title}</AlertTitle>
        {description && <AlertDescription>{description}</AlertDescription>}
      </Alert>
    ),
    { duration: 10_000 }
  );
}

export function useAgentErrors() {
  const agent = useAgent();
  const { isConnected, end } = useSessionContext();
  const handled = useRef(false);

  useEffect(() => {
    if (!isConnected || agent.state !== 'failed') {
      handled.current = false;
      return;
    }
    if (!handled.current) {
      handled.current = true;
      toastAlert({
        title: 'No se pudo conectar con el asistente',
        description: (
          <p className="w-full">
            La conexión se interrumpió o el asistente no terminó de prepararse. Puedes iniciar otra
            llamada en unos segundos.
          </p>
        ),
      });

      void end().catch(() => undefined);
    }
  }, [agent, isConnected, end]);
}
