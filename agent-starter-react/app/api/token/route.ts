import { NextResponse } from 'next/server';
import { AccessToken, type AccessTokenOptions, type VideoGrant } from 'livekit-server-sdk';
import { randomUUID } from 'node:crypto';
import { RoomAgentDispatch, RoomConfiguration } from '@livekit/protocol';
import type { BrowserAvatar } from '@/lib/browser-avatar';
import { browserAvatars } from '@/lib/browser-avatar-server';
import { body, createContext, enabled, sameOrigin } from '@/lib/telemetry/server';

type ConnectionDetails = {
  serverUrl: string;
  roomName: string;
  participantName: string;
  participantToken: string;
  telemetry?: { context: Record<string, unknown>; token: string };
  avatar?: BrowserAvatar;
  avatars?: BrowserAvatar[];
};

// NOTE: you are expected to define the following environment variables in `.env.local`:
const API_KEY = process.env.LIVEKIT_API_KEY;
const API_SECRET = process.env.LIVEKIT_API_SECRET;
const LIVEKIT_URL = process.env.LIVEKIT_URL;

// don't cache the results
export const revalidate = 0;

export async function POST(req: Request) {
  if (!sameOrigin(req)) return new Response(null, { status: 403 });
  let requested;
  try {
    requested = await body(req, 1024);
  } catch {
    return NextResponse.json({ error: 'Solicitud inválida' }, { status: 400 });
  }
  const mode = requested?.presentation_mode ?? 'voice';
  if (mode !== 'voice' && mode !== 'avatar') return new Response(null, { status: 400 });
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

    // Server owns dispatch and identity; never accept participant IDs or job metadata from POST.
    const targetAgent = process.env.AGENT_NAME || 'nexus';
    const participantName = 'user';
    const participantIdentity = `visitor_${randomUUID()}`;
    const roomName = `viva_${randomUUID()}`;
    const telemetry = enabled()
      ? await createContext(roomName, participantIdentity, mode)
      : undefined;
    const roomConfig = new RoomConfiguration({
      agents: [
        new RoomAgentDispatch({
          agentName: targetAgent,
          metadata: telemetry ? JSON.stringify({ telemetry_context: telemetry.token }) : '',
        }),
      ],
    });

    const participantToken = await createParticipantToken(
      { identity: participantIdentity, name: participantName },
      roomName,
      roomConfig
    );

    let avatars: BrowserAvatar[] | undefined;
    if (mode === 'avatar') {
      avatars = await browserAvatars();
      if (!avatars.length) {
        return NextResponse.json(
          { error: 'Los modelos aún no están disponibles. Puedes elegir Voz.' },
          { status: 409 }
        );
      }
    }

    // Return connection details
    const data: ConnectionDetails = {
      serverUrl: LIVEKIT_URL,
      roomName,
      participantName,
      participantToken,
      telemetry,
      avatar: avatars?.find((asset) => asset.character === 'LIRA'),
      avatars,
    };
    const headers = new Headers({
      'Cache-Control': 'no-store',
    });
    return NextResponse.json(data, { headers });
  } catch {
    return NextResponse.json({ error: 'No se pudo crear la sesión' }, { status: 500 });
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
