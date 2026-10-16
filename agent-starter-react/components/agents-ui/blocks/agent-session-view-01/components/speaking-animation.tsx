import { cn } from '@/lib/shadcn/utils';

interface SpeakingAnimationProps {
  isChatOpen: boolean;
  className?: string;
}

/**
 * Animación obligatoria mientras el agente está hablando (estado "speaking" de
 * useVoiceAssistant), sin importar cuál agente sea ni si hay avatar de Unreal
 * conectado: reemplaza a cualquiera de los dos (ver tile-view.tsx, que la hace
 * mutuamente excluyente con "Avatar de Unreal", "Audio Agent" y "Avatar Agent").
 * Clip corto (4s, sin audio) en loop — dura lo que dure la locución real, que
 * casi nunca coincide con esos 4s.
 */
export function SpeakingAnimation({ isChatOpen, className }: SpeakingAnimationProps) {
  return (
    <div
      className={cn(
        'pointer-events-auto overflow-hidden rounded-xl bg-black drop-shadow-xl/80',
        isChatOpen ? 'h-[120px] w-[213px]' : 'aspect-video w-[min(100vw-2rem,42rem)]',
        className
      )}
    >
      <video
        src="/animaciones-viva/viva-uam-voz.webm"
        autoPlay
        loop
        muted
        playsInline
        className="size-full object-cover"
      />
    </div>
  );
}
