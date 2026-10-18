import { NextResponse } from 'next/server';
import { collector, isAdmin } from '@/lib/telemetry/server';

export const dynamic = 'force-dynamic';
export async function GET(req: Request, { params }: { params: Promise<{ path: string[] }> }) {
  if (!(await isAdmin())) return NextResponse.json({ error: 'Inicia sesión' }, { status: 401 });
  const path = (await params).path.join('/');
  if (!/^(metrics|sessions|health|sessions\/[0-9a-f-]{36}\/events)$/.test(path))
    return NextResponse.json({ error: 'Ruta no válida' }, { status: 404 });
  const search = new URL(req.url).search;
  try {
    const res = await collector('/' + path + search);
    return NextResponse.json(await res.json(), {
      status: res.status,
      headers: { 'Cache-Control': 'no-store' },
    });
  } catch {
    return NextResponse.json(
      { error: 'Telemetría no disponible; la voz puede continuar' },
      { status: 503 }
    );
  }
}
