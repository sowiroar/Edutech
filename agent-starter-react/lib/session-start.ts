import { type Room, RoomEvent } from 'livekit-client';

// The local worker can need 25–62 seconds to warm its document indexes.
// A ready worker still connects immediately; this only bounds the cold start.
export const AGENT_CONNECT_TIMEOUT_MS = 90_000;

export async function startSessionAttempt({
  room,
  start,
  timeoutMs = AGENT_CONNECT_TIMEOUT_MS + 5_000,
}: {
  room: Pick<Room, 'on' | 'off'>;
  start: (options: { signal: AbortSignal }) => Promise<void>;
  timeoutMs?: number;
}): Promise<void> {
  const controller = new AbortController();
  let rejectWait!: (reason: Error) => void;
  const interrupted = new Promise<never>((_, reject) => {
    rejectWait = reject;
  });
  const disconnected = () =>
    rejectWait(new Error('Se perdió la conexión con el asistente. Puedes iniciar otra llamada.'));
  room.on(RoomEvent.Disconnected, disconnected);
  const timeout = setTimeout(
    () => rejectWait(new Error('El asistente no se conectó a tiempo. Vuelve a intentarlo.')),
    timeoutMs
  );
  try {
    // useSession.start can keep waiting for an agent after end() disconnected
    // the room. Settle our UI and cancel the SDK waiter on that path as well.
    await Promise.race([start({ signal: controller.signal }), interrupted]);
  } catch (error) {
    controller.abort();
    throw error;
  } finally {
    clearTimeout(timeout);
    room.off(RoomEvent.Disconnected, disconnected);
  }
}
