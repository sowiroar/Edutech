import React, { useEffect, useMemo } from 'react';
import { Track } from 'livekit-client';
import { AnimatePresence, type MotionProps, motion } from 'motion/react';
import {
  type TrackReference,
  VideoTrack,
  useLocalParticipant,
  useTracks,
  useVoiceAssistant,
} from '@livekit/components-react';
import { useAvatarStream } from '@/hooks/useAvatarStream';
import { avatarForAgent } from '@/lib/browser-avatar';
import { cn } from '@/lib/shadcn/utils';
import { AvatarStage } from './avatar-stage';
import { SpeakingAnimation } from './speaking-animation';

const ANIMATION_TRANSITION: MotionProps['transition'] = {
  type: 'spring',
  stiffness: 675,
  damping: 75,
  mass: 1,
};

const tileViewClassNames = {
  // GRID
  // 2 Columns x 3 Rows
  grid: [
    'h-full w-full',
    'grid gap-x-2 place-content-center',
    'grid-cols-[1fr_1fr] grid-rows-[90px_1fr_90px]',
  ],
  // Agent
  // chatOpen: true,
  // hasSecondTile: true
  // layout: Column 1 / Row 1
  // align: x-end y-center
  agentChatOpenWithSecondTile: ['col-start-1 row-start-1', 'self-center justify-self-end'],
  // Agent
  // chatOpen: true,
  // hasSecondTile: false
  // layout: Column 1 / Row 1 / Column-Span 2
  // align: x-center y-center
  agentChatOpenWithoutSecondTile: ['col-start-1 row-start-1', 'col-span-2', 'place-content-center'],
  // Agent
  // chatOpen: false
  // layout: Column 1 / Row 1 / Column-Span 2 / Row-Span 3
  // align: x-center y-center
  agentChatClosed: ['col-start-1 row-start-1', 'col-span-2 row-span-3', 'place-content-center'],
  // Second tile
  // chatOpen: true,
  // hasSecondTile: true
  // layout: Column 2 / Row 1
  // align: x-start y-center
  secondTileChatOpen: ['col-start-2 row-start-1', 'self-center justify-self-start'],
  // Second tile
  // chatOpen: false,
  // hasSecondTile: false
  // layout: Column 2 / Row 2
  // align: x-end y-end
  secondTileChatClosed: ['col-start-2 row-start-3', 'place-content-end'],
};

export function useLocalTrackRef(source: Track.Source) {
  const { localParticipant } = useLocalParticipant();
  const publication = localParticipant.getTrackPublication(source);
  const trackRef = useMemo<TrackReference | undefined>(
    () => (publication ? { source, participant: localParticipant, publication } : undefined),
    [source, publication, localParticipant]
  );
  return trackRef;
}

interface TileLayoutProps {
  themeMode?: 'dark' | 'light';
  isChatOpen: boolean;
  audioVisualizerType?: 'bar' | 'wave' | 'grid' | 'radial' | 'aura';
  audioVisualizerColor?: `#${string}`;
  audioVisualizerColorShift?: number;
  audioVisualizerWaveLineWidth?: number;
  audioVisualizerGridRowCount?: number;
  audioVisualizerGridColumnCount?: number;
  audioVisualizerRadialBarCount?: number;
  audioVisualizerRadialRadius?: number;
  audioVisualizerBarCount?: number;
}

export function TileLayout({ isChatOpen }: TileLayoutProps) {
  const avatar = useAvatarStream();
  const { state: agentState, agentAttributes } = useVoiceAssistant();
  // El mismo anuncio del agente selecciona el modelo WebGL y la animación de voz.
  const character = agentAttributes?.['avatar.character'];
  const selectedAvatar = avatar.mode === 'avatar' ? avatarForAgent(character, avatar.assets) : null;
  const resetPlayback = avatar.resetPlayback;
  useEffect(() => resetPlayback(), [selectedAvatar?.sha256, resetPlayback]);
  const [screenShareTrack] = useTracks([Track.Source.ScreenShare]);
  const cameraTrack: TrackReference | undefined = useLocalTrackRef(Track.Source.Camera);

  const isCameraEnabled = cameraTrack && !cameraTrack.publication.isMuted;
  const isScreenShareEnabled = screenShareTrack && !screenShareTrack.publication.isMuted;
  const hasSecondTile = isCameraEnabled || isScreenShareEnabled;

  const isSpeaking = agentState === 'speaking';

  const animationDelay = isChatOpen ? 0 : 0.15;

  return (
    <div className="pointer-events-none absolute inset-x-0 top-8 bottom-32 z-50 md:top-12 md:bottom-40">
      <div className="relative mx-auto h-full max-w-2xl px-4 md:px-0">
        <div className={cn(tileViewClassNames.grid)}>
          {/* Agent */}
          <div
            className={cn([
              'grid',
              !isChatOpen && tileViewClassNames.agentChatClosed,
              isChatOpen && hasSecondTile && tileViewClassNames.agentChatOpenWithSecondTile,
              isChatOpen && !hasSecondTile && tileViewClassNames.agentChatOpenWithoutSecondTile,
            ])}
          >
            <AnimatePresence mode="popLayout">
              <motion.div
                key="speaking-animation"
                layoutId="speaking-animation"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{
                  ...ANIMATION_TRANSITION,
                  delay: animationDelay,
                }}
              >
                {selectedAvatar && !avatar.failed ? (
                  <AvatarStage
                    asset={selectedAvatar}
                    isChatOpen={isChatOpen}
                    onFailure={avatar.fail}
                    onReady={avatar.markReady}
                  />
                ) : (
                  <SpeakingAnimation
                    isSpeaking={isSpeaking}
                    isChatOpen={isChatOpen}
                    character={character}
                  />
                )}
                {avatar.mode === 'avatar' && selectedAvatar && !avatar.ready && (
                  <p role="status" className="text-center text-sm">
                    {avatar.failed
                      ? 'La imagen no está disponible. La conversación continúa por voz.'
                      : `Cargando ${selectedAvatar.character}…`}
                  </p>
                )}
                {avatar.mode === 'avatar' && !selectedAvatar && (
                  <p role="status" className="text-center text-sm">
                    {character
                      ? `${character}: la conversación continúa por voz; su modelo aún no está disponible.`
                      : 'Conectando con LIRA…'}
                  </p>
                )}
                {character && (
                  <p data-active-agent={character} className="mt-2 text-center text-sm font-medium">
                    {character}
                  </p>
                )}
              </motion.div>
            </AnimatePresence>
          </div>

          <div
            className={cn([
              'grid',
              isChatOpen && tileViewClassNames.secondTileChatOpen,
              !isChatOpen && tileViewClassNames.secondTileChatClosed,
            ])}
          >
            {/* Camera & Screen Share */}
            <AnimatePresence>
              {((cameraTrack && isCameraEnabled) || (screenShareTrack && isScreenShareEnabled)) && (
                <motion.div
                  key="camera"
                  layout="position"
                  layoutId="camera"
                  initial={{
                    opacity: 0,
                    scale: 0,
                  }}
                  animate={{
                    opacity: 1,
                    scale: 1,
                  }}
                  exit={{
                    opacity: 0,
                    scale: 0,
                  }}
                  transition={{
                    ...ANIMATION_TRANSITION,
                    delay: animationDelay,
                  }}
                  className="aspect-square size-[90px] drop-shadow-lg/20"
                >
                  <VideoTrack
                    trackRef={cameraTrack || screenShareTrack}
                    width={(cameraTrack || screenShareTrack)?.publication.dimensions?.width ?? 0}
                    height={(cameraTrack || screenShareTrack)?.publication.dimensions?.height ?? 0}
                    className="bg-muted aspect-square size-[90px] rounded-md object-cover"
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>
    </div>
  );
}
