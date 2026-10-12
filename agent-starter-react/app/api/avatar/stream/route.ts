// Reenvía el MJPEG de avatar-render (ver avatar-render/README.md) al navegador. El
// navegador nunca habla directo con avatar-render: no tiene su propio hostname en la red
// de Docker (comparte el de avatar-bridge) ni puerto publicado al host, y además así el
// video pasa por el mismo origen que el resto del frontend, sin configurar CORS aparte.
//
// No se usa force-dynamic + NextResponse.json como /api/avatar: esto reenvía un stream
// que no termina nunca (multipart/x-mixed-replace), así que hay que devolver el body de
// la respuesta de avatar-render tal cual, sin bufferearlo.
export const dynamic = 'force-dynamic';

const UPSTREAM_TIMEOUT_MS = 5000;

export async function GET() {
  const sourceUrl = process.env.AVATAR_STREAM_SOURCE_URL?.trim();
  if (!sourceUrl) {
    return new Response(null, { status: 204 });
  }

  // El timeout es solo para la conexión inicial: una vez llegan las cabeceras se
  // desarma, porque el body de un MJPEG no termina nunca (no hay que cortarlo a los
  // UPSTREAM_TIMEOUT_MS de haber empezado a verse).
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), UPSTREAM_TIMEOUT_MS);
  let upstream: Response;
  try {
    upstream = await fetch(sourceUrl, { cache: 'no-store', signal: controller.signal });
  } catch {
    // avatar-render no está arriba o no responde: no hay stream que mostrar.
    return new Response(null, { status: 502 });
  } finally {
    clearTimeout(timeoutId);
  }

  if (!upstream.ok || !upstream.body) {
    return new Response(null, { status: 502 });
  }

  return new Response(upstream.body, {
    status: 200,
    headers: {
      // ffmpeg (muxer mpjpeg) manda el boundary multipart en este mismo header;
      // reenviarlo tal cual es lo que hace que un <img> lo entienda.
      'Content-Type': upstream.headers.get('content-type') ?? 'multipart/x-mixed-replace',
      'Cache-Control': 'no-store',
    },
  });
}
