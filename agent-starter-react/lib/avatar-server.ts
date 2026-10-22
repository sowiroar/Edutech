import { sign, verify } from '@/lib/telemetry/server';

type Lease = { room: string; lease: string };
const headers = () => ({ Authorization: `Bearer ${process.env.AVATAR_INTERNAL_KEY || ''}` });

export async function bridge(action: string, lease?: Lease) {
  const base = process.env.AVATAR_BRIDGE_STATUS_URL;
  if (!base || !process.env.AVATAR_INTERNAL_KEY) throw new Error('Avatar unavailable');
  return fetch(new URL(action, base), {
    cache: 'no-store',
    signal: AbortSignal.timeout(1500),
    headers: {
      ...headers(),
      ...(lease
        ? {
            'X-Avatar-Room': lease.room,
            'X-Avatar-Lease': lease.lease,
          }
        : {}),
    },
  });
}

export async function renderer(path: string) {
  const base = process.env.AVATAR_STREAM_SOURCE_URL;
  if (!base) throw new Error('Renderer unavailable');
  return fetch(new URL(path.replace(/^\//, ''), base), {
    headers: headers(),
    cache: 'no-store',
    signal: AbortSignal.timeout(1500),
  });
}

export async function availability() {
  try {
    const [statusResponse, renderResponse] = await Promise.all([
      bridge('/status'),
      renderer('/health'),
    ]);
    const status = await statusResponse.json(),
      render = await renderResponse.json();
    if (
      !statusResponse.ok ||
      !renderResponse.ok ||
      !status.managed ||
      !status.unreal_connected ||
      render.ready !== true
    )
      return 'offline';
    return status.busy ? 'busy' : 'available';
  } catch {
    return 'offline';
  }
}

export async function reserve(room: string, session: string) {
  if ((await availability()) !== 'available') throw new Error('Avatar unavailable');
  const result = await bridge('/lease/acquire', { room, lease: '' });
  if (!result.ok) throw new Error('Avatar occupied');
  const data = await result.json();
  const lease = { room, lease: data.token as string };
  try {
    return await sign({ ...lease, session }, 'viva-avatar', '15m');
  } catch (error) {
    await bridge('/lease/release', lease).catch(() => {});
    throw error;
  }
}

export async function claims(req: Request): Promise<Lease> {
  const token = req.headers.get('authorization')?.replace(/^Bearer /, '') || '';
  const data = await verify(token, 'viva-avatar');
  if (typeof data.room !== 'string' || typeof data.lease !== 'string')
    throw new Error('Invalid lease');
  return { room: data.room, lease: data.lease };
}

export async function owns(lease: Lease, ready = false) {
  const response = await bridge('/lease/verify', lease);
  const status = await response.json();
  return response.ok && status.valid === true && (!ready || status.ready === true);
}
