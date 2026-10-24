import { cookies } from 'next/headers';
import { SignJWT, jwtVerify } from 'jose';
import { randomUUID, timingSafeEqual } from 'node:crypto';

export const adminCookie = 'viva_admin';
const visitorCookie = 'viva_visitor';
export const cookieOptions = {
  httpOnly: true,
  sameSite: 'strict' as const,
  secure: process.env.TELEMETRY_COOKIE_SECURE === 'true',
  path: '/',
};
const buckets = new Map<string, { n: number; until: number }>();
export function rateLimit(key: string, maximum: number, windowMs = 60_000) {
  const now = Date.now();
  for (const [k, v] of buckets) if (v.until <= now) buckets.delete(k);
  const bucket = buckets.get(key) || { n: 0, until: now + windowMs };
  bucket.n++;
  buckets.set(key, bucket);
  return bucket.n <= maximum;
}
export function sameOrigin(req: Request) {
  const origin = req.headers.get('origin');
  if (!origin || origin === 'null') return false;
  const allowedOrigins = [
    new URL(req.url).origin,
    process.env.TELEMETRY_PUBLIC_ORIGIN,
    ...(process.env.TELEMETRY_ADDITIONAL_ORIGINS || '').split(',').map((value) => value.trim()),
  ];
  return allowedOrigins.includes(origin);
}
function key() {
  const value = process.env.TELEMETRY_SIGNING_SECRET;
  if (!value || value.length < 32) throw new Error('Telemetry not configured');
  return new TextEncoder().encode(value);
}
export function enabled() {
  return !!process.env.TELEMETRY_SIGNING_SECRET && !!process.env.TELEMETRY_URL;
}
export async function sign(payload: Record<string, unknown>, audience: string, expiration: string) {
  return new SignJWT(payload)
    .setProtectedHeader({ alg: 'HS256' })
    .setIssuedAt()
    .setAudience(audience)
    .setExpirationTime(expiration)
    .sign(key());
}
export async function verify(token: string, audience: string) {
  return (await jwtVerify(token, key(), { algorithms: ['HS256'], audience })).payload;
}
export async function isAdmin() {
  try {
    return (
      (await verify((await cookies()).get(adminCookie)?.value || '', 'viva-admin')).role === 'admin'
    );
  } catch {
    return false;
  }
}
export function passwordMatches(value: unknown) {
  const expected = process.env.TELEMETRY_ADMIN_PASSWORD || '';
  if (typeof value !== 'string' || expected.length < 16) return false;
  const a = Buffer.from(value),
    b = Buffer.from(expected);
  return a.length === b.length && timingSafeEqual(a, b);
}
export async function createContext(
  roomName: string,
  participantIdentity: string,
  presentationMode: 'voice' | 'avatar' = 'voice'
) {
  const jar = await cookies();
  let anonymousId: string;
  try {
    const claims = await verify(jar.get(visitorCookie)?.value || '', 'viva-visitor');
    if (typeof claims.id !== 'string' || !/^[0-9a-f-]{36}$/.test(claims.id))
      throw new Error('Invalid visitor');
    anonymousId = claims.id;
  } catch {
    anonymousId = randomUUID();
  }
  jar.set(visitorCookie, await sign({ id: anonymousId }, 'viva-visitor', '30d'), {
    ...cookieOptions,
    maxAge: 30 * 86400,
  });
  const context = {
    app_session_id: randomUUID(),
    conversation_id: randomUUID(),
    anonymous_id: anonymousId,
    user_id: null,
    identity_source: 'visitor',
    environment: process.env.TELEMETRY_ENVIRONMENT || 'local',
    release: process.env.APP_RELEASE || 'unknown',
    avatar_release: process.env.AVATAR_RELEASE || null,
    presentation_mode: presentationMode,
    channel: 'voice',
    room_name: roomName,
    participant_identity: participantIdentity,
  };
  return { context, token: await sign({ context }, 'viva-telemetry', '8h') };
}
export async function collector(path: string, init?: RequestInit) {
  const url = process.env.TELEMETRY_URL;
  const secret = process.env.TELEMETRY_INTERNAL_KEY;
  if (!url || !secret) throw new Error('Telemetry unavailable');
  return fetch(url.replace(/\/$/, '') + path, {
    ...init,
    cache: 'no-store',
    signal: AbortSignal.timeout(3000),
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${secret}` },
  });
}
export async function body(req: Request, maximum = 16_384) {
  if (!req.body) throw new Error('Missing body');
  const reader = req.body.getReader();
  let length = 0;
  const chunks: Uint8Array[] = [];
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    length += value.length;
    if (length > maximum) {
      await reader.cancel();
      throw new Error('Body too large');
    }
    chunks.push(value);
  }
  return JSON.parse(Buffer.concat(chunks).toString('utf8'));
}
