import { claims, owns, renderer } from '@/lib/avatar-server';

export const dynamic = 'force-dynamic';

export async function GET(req: Request) {
  const headers = { 'Cache-Control': 'no-store', 'Content-Type': 'image/jpeg' };
  try {
    const lease = await claims(req);
    if (!(await owns(lease, true))) return new Response(null, { status: 409 });
    const upstream = await renderer('/frame');
    if (!upstream.ok || upstream.headers.get('content-type') !== 'image/jpeg') {
      return new Response(null, { status: 503 });
    }
    const data = await upstream.arrayBuffer();
    // Recheck after I/O: a released/expired session cannot receive a new owner's frame.
    if (!(await owns(lease, true))) return new Response(null, { status: 409 });
    if (data.byteLength > 4 * 1024 * 1024) return new Response(null, { status: 502 });
    return new Response(data, { headers });
  } catch {
    return new Response(null, { status: 503 });
  }
}
