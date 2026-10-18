import { cookies } from 'next/headers';
import { NextResponse } from 'next/server';
import { adminCookie, cookieOptions, sameOrigin } from '@/lib/telemetry/server';

export async function POST(req: Request) {
  if (!sameOrigin(req)) return NextResponse.json({ error: 'Origen no permitido' }, { status: 403 });
  (await cookies()).set(adminCookie, '', { ...cookieOptions, maxAge: 0 });
  return NextResponse.json({ ok: true });
}
