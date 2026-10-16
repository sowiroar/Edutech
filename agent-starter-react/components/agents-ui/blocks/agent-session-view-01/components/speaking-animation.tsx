import { useEffect, useRef } from 'react';
import { cn } from '@/lib/shadcn/utils';

interface SpeakingAnimationProps {
  /** true: reproduce en loop (el agente está hablando). false: en pausa (en espera). */
  isSpeaking: boolean;
  isChatOpen: boolean;
  className?: string;
}

/**
 * Visual obligatorio del agente — reemplaza por completo al avatar de Unreal, al
 * visualizador de audio y al video de agente que había antes (ver tile-view.tsx): un
 * único <video>, siempre montado, que solo cambia entre reproducir y pausar. Nunca se
 * desmonta entre estados: así no hay que recargar el archivo ni se nota un salto al
 * cambiar, solo play()/pause() sobre el mismo elemento.
 *
 * - Hablando: en loop (el clip dura 4s, menos que la mayoría de locuciones).
 * - En espera (idle/listening/thinking): en pausa, congelado en el frame donde se quedó.
 */
export function SpeakingAnimation({ isSpeaking, isChatOpen, className }: SpeakingAnimationProps) {
  const videoRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    if (isSpeaking) {
      // play() devuelve una promesa que puede rechazarse (p.ej. autoplay bloqueado
      // antes de cualquier interacción del usuario); no hay nada más que hacer si
      // falla, así que se ignora en vez de dejar un rechazo sin atrapar.
      void video.play().catch(() => {});
    } else {
      video.pause();
    }
  }, [isSpeaking]);

  return (
    <div
      className={cn(
        'pointer-events-auto overflow-hidden rounded-xl bg-black drop-shadow-xl/80',
        isChatOpen ? 'h-[120px] w-[213px]' : 'aspect-video w-[min(100vw-2rem,42rem)]',
        className
      )}
    >
      <video
        ref={videoRef}
        src="/animaciones-viva/viva-uam-voz.webm"
        loop
        muted
        playsInline
        className="size-full object-cover"
      />
    </div>
  );
}
