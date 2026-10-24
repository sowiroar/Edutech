import { Button } from '@/components/ui/button';
import { useAvatarStream } from '@/hooks/useAvatarStream';

function WelcomeImage() {
  // Antes: ícono genérico de barras de audio (SVG inline). Reemplazado por el logo de
  // VIVA UAM (animaciones-viva/logo-viva.png, con transparencia real) — es lo primero
  // que se ve, sobre el botón de "Start call" por defecto.
  // eslint-disable-next-line @next/next/no-img-element -- archivo estático simple, igual que /lk-logo.svg en app/layout.tsx.
  return <img src="/animaciones-viva/logo-viva.png" alt="VIVA UAM" className="mb-4 h-16 w-auto" />;
}

interface WelcomeViewProps {
  startButtonText: string;
  onStartCall: () => void;
  pending?: boolean;
  error?: string;
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  pending,
  error,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  const avatar = useAvatarStream();
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center">
        <WelcomeImage />

        <p className="text-foreground max-w-prose pt-1 leading-6 font-medium">
          Bienvenido a la Liga Sapience
        </p>

        <div role="group" aria-label="Presentación" className="mt-5 flex gap-2">
          <Button
            variant={avatar.mode === 'voice' ? 'default' : 'outline'}
            disabled={pending}
            aria-pressed={avatar.mode === 'voice'}
            onClick={() => avatar.setMode('voice')}
          >
            Voz
          </Button>
          <Button
            variant={avatar.mode === 'avatar' ? 'default' : 'outline'}
            disabled={pending}
            aria-pressed={avatar.mode === 'avatar'}
            onClick={() => avatar.setMode('avatar')}
          >
            Avatar
          </Button>
        </div>
        {avatar.mode === 'avatar' && (
          <p role="status" className="mt-3 max-w-sm text-sm">
            {avatar.availability === 'available'
              ? 'LIRA te recibe. El avatar cambia automáticamente con el agente.'
              : 'Estamos preparando los modelos. Puedes elegir Voz.'}
          </p>
        )}
        {avatar.mode === 'avatar' && avatar.availability === 'available' && (
          <div className="mt-2 flex gap-4 text-sm">
            {avatar.availableCharacters.map((character) => (
              <a
                key={character}
                href={`/avatar-preview?character=${character}`}
                className="underline"
              >
                Ver {character}
              </a>
            ))}
          </div>
        )}
        {error && (
          <p role="alert" className="mt-3 max-w-sm text-sm">
            {error}
          </p>
        )}
        <Button
          size="lg"
          onClick={onStartCall}
          disabled={pending || (avatar.mode === 'avatar' && avatar.availability !== 'available')}
          className="mt-6 w-64 rounded-full font-mono text-xs font-bold tracking-wider uppercase"
        >
          {pending ? 'Conectando…' : startButtonText}
        </Button>
      </section>

      <div className="fixed bottom-5 left-0 flex w-full items-center justify-center">
        <p className="text-muted-foreground max-w-prose pt-1 text-xs leading-5 font-normal text-pretty md:text-sm">
          Need help getting set up? Check out the{' '}
          <a
            target="_blank"
            rel="noopener noreferrer"
            href="https://docs.livekit.io/agents/start/voice-ai/"
            className="underline"
          >
            Voice AI quickstart
          </a>
          .
        </p>
      </div>
    </div>
  );
};
