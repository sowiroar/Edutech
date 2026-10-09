import { cn } from '@/lib/shadcn/utils';

interface AvatarStageProps {
  /** /api/avatar/stream: MJPEG (multipart/x-mixed-replace) de avatar-render. */
  url: string;
  isChatOpen: boolean;
  className?: string;
}

/**
 * Muestra al avatar (NEXO/Familia VIVA) vía MJPEG — reemplaza al Pixel Streaming de
 * Unreal, que nunca llegó a verse en el navegador (ver avatar-render/README.md). Un
 * <img> normal basta: multipart/x-mixed-replace es un formato que el navegador ya sabe
 * mostrar como si fueran frames de video, sin códecs ni JS de por medio. Unreal anima al
 * avatar con la voz del agente que esté hablando; con el chat abierto se reduce a una
 * miniatura.
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
      {/* eslint-disable-next-line @next/next/no-img-element -- MJPEG no es un <Image> de next/image: es un stream infinito, no un archivo que optimizar. */}
      <img src={url} alt="Avatar" className="size-full object-cover" />
    </div>
  );
}
