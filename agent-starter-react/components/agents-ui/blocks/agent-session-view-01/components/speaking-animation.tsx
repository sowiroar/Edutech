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
 *
 * viva-uam-voz.mp4 (de animaciones viva/viva_uam_voz.mp4, 2026-10-16) ya trae fondo
 * blanco de origen, sin el recorte de color que hizo falta con la versión anterior
 * (viva_uam_voz_transparente.webm, que pese al nombre no tenía canal alfa real). H264/MP4
 * en vez de VP9/WebM: incluso más compatible entre navegadores, y no hace falta alfa
 * aquí. El fondo blanco del contenedor de abajo se deja de todos modos, por si el video
 * no llena el recuadro entero (framing distinto a su aspect ratio).
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
        'pointer-events-auto overflow-hidden rounded-xl bg-white drop-shadow-xl/80',
        isChatOpen ? 'h-[120px] w-[213px]' : 'aspect-video w-[min(100vw-2rem,42rem)]',
        className
      )}
    >
      <video
        ref={videoRef}
        src="/animaciones-viva/viva-uam-voz.mp4"
        loop
        muted
        playsInline
        className="size-full object-cover"
      />
    </div>
  );
}
