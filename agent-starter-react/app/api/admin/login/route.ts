import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import {
  adminCookie,
  body,
  cookieOptions,
  passwordMatches,
  rateLimit,
  sameOrigin,
  sign,
} from '@/lib/telemetry/server';

export async function POST(req: Request) {
  if (!sameOrigin(req)) return NextResponse.json({ error: 'Origen no permitido' }, { status: 403 });
  // Global limit is deliberate: no trust in a client-supplied forwarding header.
  if (!rateLimit('admin-login', 10))
    return NextResponse.json({ error: 'Espera un minuto antes de reintentar' }, { status: 429 });
  try {
    if (!passwordMatches((await body(req, 2048)).password))
      return NextResponse.json({ error: 'Credencial no válida' }, { status: 401 });
    (await cookies()).set(adminCookie, await sign({ role: 'admin' }, 'viva-admin', '8h'), {
      ...cookieOptions,
      maxAge: 8 * 3600,
    });
    return NextResponse.json({ ok: true }, { headers: { 'Cache-Control': 'no-store' } });
  } catch {
    return NextResponse.json({ error: 'No se pudo iniciar sesión' }, { status: 400 });
  }
}
