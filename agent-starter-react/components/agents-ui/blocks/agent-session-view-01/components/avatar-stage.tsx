import { cn } from '@/lib/shadcn/utils';

interface AvatarStageProps {
  /** Página de Pixel Streaming del avatar de Unreal. */
  url: string;
  isChatOpen: boolean;
  className?: string;
}

/**
 * Muestra al avatar (NEXO) transmitido por Pixel Streaming. Unreal lo anima con la voz del
 * agente que esté hablando; con el chat abierto se reduce a una miniatura.
 */
export function AvatarStage({ url, isChatOpen, className }: AvatarStageProps) {
  return (
    <div
      className={cn(
        'pointer-events-auto overflow-hidden rounded-xl bg-black drop-shadow-xl/80',
        isChatOpen ? 'h-[120px] w-[213px]' : 'aspect-video w-[min(100vw-2rem,42rem)]',
        className
      )}
    >
      <iframe
        src={url}
        title="Avatar NEXO"
        allow="autoplay; fullscreen"
        className="size-full border-0"
      />
    </div>
  );
}
