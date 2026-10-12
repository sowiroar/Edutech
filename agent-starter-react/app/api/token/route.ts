import { NextResponse } from 'next/server';
import { AccessToken, type AccessTokenOptions, type VideoGrant } from 'livekit-server-sdk';
import { RoomConfiguration, RoomAgentDispatch } from '@livekit/protocol';

type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
};

// NOTE: you are expected to define the following environment variables in `.env.local`:
const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

// don't cache the results
export const revalidate = 0;

export async function POST(req: Request) {
  // make an exception for development, vercel preview, or local docker deployment
  if (
    process.env.NODE_ENV !== 'development' &&
    process.env.IS_VERCEL_PREVIEW !== 'true' &&
    process.env.ALLOW_INSECURE_ROOM_CREATION !== 'true'
  ) {
    throw new Error(
      'THIS API ROUTE IS INSECURE. DO NOT USE THIS ROUTE IN PRODUCTION WITHOUT AN AUTHENTICATION LAYER.'
    );
  }

  try {
    if (LIVEKIT_URL === undefined) {
      throw new Error('LIVEKIT_URL is not defined');
    }
    if (API_KEY === undefined) {
      throw new Error('LIVEKIT_API_KEY is not defined');
    }
    if (API_SECRET === undefined) {
      throw new Error('LIVEKIT_API_SECRET is not defined');
    }

    // Parse room config from request body.
    const body = await req.json().catch(() => ({}));
    const roomConfig = body?.room_config
      ? RoomConfiguration.fromJson(body.room_config, { ignoreUnknownFields: true })
      : new RoomConfiguration();

    // Ensure our agent (nexus) is always dispatched to the room
    const targetAgent = process.env.AGENT_NAME || 'nexus';
    if (!roomConfig.agents || roomConfig.agents.length === 0) {
      roomConfig.agents = [new RoomAgentDispatch({ agentName: targetAgent })];
    }

    // Generate participant token
    const participantName = 'user';
    const participantIdentity = `voice_assistant_user_${Math.floor(Math.random() * 10_000)}`;
    const roomName = `voice_assistant_room_${Math.floor(Math.random() * 10_000)}`;

    const participantToken = await createParticipantToken(
      { identity: participantIdentity, name: participantName },
      roomName,
      roomConfig
    );

    // Avisa al puente del avatar que hay una sala nueva, para que se una de
    // inmediato en vez de esperar a su siguiente poll (ver RoomFollower.hint
    // en avatar-bridge/livekit_source.py). Si el puente no está disponible o
    // tarda, no debe frenar el inicio de la llamada: se limita el tiempo de
    // espera (300ms) y cualquier error se ignora en silencio. Se espera
    // (await) porque en Next.js una promesa sin await puede quedar cortada
    // apenas la función retorna la respuesta (Claude, 2026-09-29).
    await hintAvatarBridge();

    // Return connection details
    const data: ConnectionDetails = {
      serverUrl: LIVEKIT_URL,
      roomName,
      participantName,
      participantToken,
    };
    const headers = new Headers({
      'Cache-Control': 'no-store',
    });
    return NextResponse.json(data, { headers });
  } catch (error) {
    if (error instanceof Error) {
      console.error(error);
      return new NextResponse(error.message, { status: 500 });
    }
  }
}

async function hintAvatarBridge(): Promise<void> {
  const hintUrl = process.env.AVATAR_BRIDGE_HINT_URL || 'http://avatar-bridge:8766/hint';
  try {
    // GET, no POST: el servidor websockets de Python (avatar-bridge) solo
    // acepta GET en su gancho process_request (rechaza cualquier otro
    // método antes de que nuestro código lo vea).
    await fetch(hintUrl, { method: 'GET', signal: AbortSignal.timeout(300) });
  } catch {
    // El avatar es opcional: si el puente no responde a tiempo o no está
    // levantado, la llamada sigue igual (el puente cae de vuelta a su poll
    // de respaldo).
  }
}

function createParticipantToken(
  userInfo: AccessTokenOptions,
  roomName: string,
  roomConfig: RoomConfiguration | undefined
): Promise<string> {
  const at = new AccessToken(API_KEY, API_SECRET, {
    ...userInfo,
    ttl: '15m',
  });
  const grant: VideoGrant = {
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canPublishData: true,
    canSubscribe: true,
  };
  at.addGrant(grant);

  if (roomConfig) {
    at.roomConfig = roomConfig;
  }

  return at.toJwt();
}
