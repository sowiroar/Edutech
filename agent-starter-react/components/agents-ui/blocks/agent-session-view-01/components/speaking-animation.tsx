import { useEffect, useRef } from 'react';
import { cn } from '@/lib/shadcn/utils';

interface SpeakingAnimationProps {
  /** true: reproduce en loop (el agente está hablando). false: en pausa (en espera). */
  isSpeaking: boolean;
  isChatOpen: boolean;
  /** Personaje activo (atributo `avatar.character` del agente: NEXO/LIRA/ELIAN, ver
   * agent.py). Elige el color del clip; cualquier otro valor usa el por defecto. */
  character?: string;
  className?: string;
}

// NEXO = Nexus (especialización en IA) -> verde agua. ELIAN = Elian (administrativo
// UAM) -> naranja. LIRA (recepción) y cualquier otro caso usan el color por defecto —
// no se pidió uno propio.
//
// El sufijo -v2 (2026-10-16): el contenido de estos dos se re-encodó para que tuvieran
// el mismo encuadre 1000x562 que viva-uam-voz.mp4 (las fuentes originales venían casi
// cuadradas, ~960x754 — con object-cover eso se ve "ampliado" frente al video por
// defecto, que sí es panorámico). Cambiar el nombre del archivo al cambiar el contenido
// es necesario, no cosmético: ya pasó una vez (ver historial) que mantener el mismo
// nombre dejaba el navegador sirviendo el contenido viejo desde su caché de medios, sin
// que un Cache-Control normal (max-age=0 + ETag) lo evitara dentro de la misma pestaña.
const SOURCE_BY_CHARACTER: Record<string, string> = {
  NEXO: '/animaciones-viva/viva-uam-voz-nexus-v2.mp4',
  ELIAN: '/animaciones-viva/viva-uam-voz-elian-naranja-v2.mp4',
};
const DEFAULT_SOURCE = '/animaciones-viva/viva-uam-voz.mp4';

/**
 * Visual obligatorio del agente — reemplaza por completo al avatar de Unreal, al
 * visualizador de audio y al video de agente que había antes (ver tile-view.tsx): un
 * único <video>, siempre montado, que solo cambia entre reproducir y pausar. Nunca se
 * desmonta entre estados: así no hay que recargar el archivo ni se nota un salto al
 * cambiar, solo play()/pause() sobre el mismo elemento.
 *
 * - Hablando: en loop (los clips duran 4-12s, menos que la mayoría de locuciones).
 * - En espera (idle/listening/thinking): en pausa, congelado en el frame donde se quedó.
 *
 * Al cambiar de personaje (Lira transfiere a Nexus/Elian) sí hay que recargar el
 * elemento: es un archivo distinto, no algo que resuelva play()/pause(). Queda pausado
 * en el frame 0 del clip nuevo hasta que vuelva a hablar — más simple que guardar la
 * posición exacta de cada clip, y no es perceptible porque el cambio de personaje real
 * casi siempre coincide con el agente nuevo presentándose (isSpeaking pasa a true casi
 * enseguida).
 */
export function SpeakingAnimation({
  isSpeaking,
  isChatOpen,
  character,
  className,
}: SpeakingAnimationProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const src = (character && SOURCE_BY_CHARACTER[character]) || DEFAULT_SOURCE;

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    // load() relee el src actual del elemento (ya actualizado por React antes de este
    // efecto) y dispara la recarga; sin esto, algunos navegadores no refrescan el frame
    // mostrado hasta el próximo play().
    video.load();
    if (isSpeaking) {
      void video.play().catch(() => {});
    }
    // isSpeaking también en las dependencias: si cambia mientras el src es el mismo
    // (el caso normal, hablando <-> en espera del mismo personaje) no hace falta
    // recargar el archivo, solo play()/pause() — ver el efecto de abajo.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src]);

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
      <video ref={videoRef} src={src} loop muted playsInline className="size-full object-cover" />
    </div>
  );
}
