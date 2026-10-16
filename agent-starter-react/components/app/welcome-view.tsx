import { Button } from '@/components/ui/button';

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
}

export const WelcomeView = ({
  startButtonText,
  onStartCall,
  ref,
}: React.ComponentProps<'div'> & WelcomeViewProps) => {
  return (
    <div ref={ref}>
      <section className="bg-background flex flex-col items-center justify-center text-center">
        <WelcomeImage />

        <p className="text-foreground max-w-prose pt-1 leading-6 font-medium">
          Bienvenido a la Liga Sapience
        </p>

        <Button
          size="lg"
          onClick={onStartCall}
          className="mt-6 w-64 rounded-full font-mono text-xs font-bold tracking-wider uppercase"
        >
          {startButtonText}
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
